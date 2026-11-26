from datetime import date, datetime, timedelta
from typing import Literal

from livekit.agents import ToolError, function_tool
from multi_agent.config.settings import build_tts
from multi_agent.config.voice_settings import VOICE_SETTINGS

from multi_agent.agents.airline.carrier import (
    CITIES,
    MAX_PASSENGERS,
    MESSAGE_TIMELINES,
    Carrier,
    CarrierError,
    resolve_airport,
    speech,
)
from multi_agent.agents.airline.knowledge import load_guide
from multi_agent.agents.airline.prompts import build_instructions, prompt
from multi_agent.agents.base import BaseSpecialist


def _fail(error: CarrierError) -> ToolError:
    return ToolError(str(error))


class AirlineAgent(BaseSpecialist):
    """SkyBridge Airways reservations assistant. All the work happens in the tools below."""

    greeting = prompt("greeting")

    def __init__(self, carrier: Carrier | None = None, greet: bool = True, **kwargs):
        self._carrier = carrier
        self._greet = greet
        now = carrier.now if carrier else datetime.now()
        self.prompt = build_instructions(now)

        airline_voice_id = VOICE_SETTINGS["tts"]["voices"]["airline"]

        super().__init__(
            tts=build_tts(airline_voice_id),
            **kwargs
        )
    @property
    def carrier(self) -> Carrier:
        # One carrier per call lives in session.userdata, so a booking survives
        # a trip back to the main menu. Tests pass a carrier directly.
        if self._carrier is not None:
            return self._carrier
        return self.session.userdata.carrier

    async def on_enter(self):
        if self._greet:
            await super().on_enter()

    # ---- small helpers -------------------------------------------------
    def _airport(self, text: str, label: str) -> str:
        code = resolve_airport(text)
        if code is None:
            cities = ", ".join(CITIES.values())
            raise ToolError(f"SkyBridge does not fly from or to '{text}' ({label}). It serves {cities}.")
        return code

    def _day(self, text: str) -> date:
        try:
            day = date.fromisoformat(text.strip())
        except ValueError:
            raise ToolError("Give the date as YYYY-MM-DD, worked out from today's date.") from None
        today = self.carrier.now.date()
        if day < today:
            raise ToolError("That date is in the past. Ask the caller for a date from today onwards.")
        last = self.carrier.last_day
        if last and day > last:
            raise ToolError(f"Flights can be booked up to {speech.say_day(last)}. Ask for an earlier date.")
        return day

    def _line(self, flight, cabin: str, passengers: int) -> str:
        cabins = ("economy", "business") if cabin == "any" else (cabin,)
        fares = [
            f"{c} {speech.say_money(flight.fares[c])} per passenger"
            for c in cabins
            if flight.seats[c] >= passengers
        ]
        note = f", delayed {flight.delay_minutes} minutes" if flight.status == "delayed" else ""
        return (
            f"flight {flight.number}, departs {speech.say_time(flight.departs)}, "
            f"arrives {speech.say_time(flight.arrives)}{note}, {' and '.join(fares)} "
            f"(id for tools: {flight.id})"
        )

    # ---- tools ---------------------------------------------------------
    @function_tool
    async def read_airline_information(self) -> str:
        """Read the published SkyBridge guide: check-in, baggage, changes and refunds, assistance, contact and payment.

        Use it for any policy question. It takes no arguments and returns the whole guide.
        """
        return load_guide()

    @function_tool
    async def search_flights(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        cabin: Literal["economy", "business", "any"] = "any",
        passengers: int = 1,
    ) -> str:
        """Search open SkyBridge flights for one route on one date.

        Args:
            origin: Departure city, for example Hyderabad.
            destination: Arrival city, for example Bengaluru.
            travel_date: The travel date as YYYY-MM-DD.
            cabin: economy, business, or any if the caller has no preference.
            passengers: How many people are travelling.
        """
        a = self._airport(origin, "origin")
        b = self._airport(destination, "destination")
        if a == b:
            raise ToolError("The origin and destination are the same city. Ask again.")
        if not 1 <= passengers <= MAX_PASSENGERS:
            raise ToolError(f"A booking can have 1 to {MAX_PASSENGERS} passengers.")
        day = self._day(travel_date)
        flights = self.carrier.search(a, b, day, cabin, passengers)
        route = f"{CITIES[a]} to {CITIES[b]} on {speech.say_day(day)}"
        if not flights:
            later = self.carrier.next_dates(a, b, day, passengers)
            hint = (
                " The next dates with flights are " + ", ".join(speech.say_day(d) for d in later) + "."
                if later
                else ""
            )
            return f"No open flights from {route}.{hint} Offer a different date."
        lines = "\n".join(f"- {self._line(f, cabin, passengers)}" for f in flights[:3])
        return (
            f"Open flights from {route}:\n{lines}\n"
            "Offer at most two. Do not say the ids aloud."
        )

    @function_tool
    async def book_flight(
        self,
        flight_id: str,
        cabin: Literal["economy", "business"],
        passenger_names: list[str],
        last_name: str,
    ) -> str:
        """Book seats on a flight the caller chose from search results.

        Args:
            flight_id: The id from the search results. Never spoken to the caller.
            cabin: economy or business.
            passenger_names: Full name of every passenger, as on their ID.
            last_name: The last name of the first passenger. It is used with the reference to find the booking later.
        """
        try:
            booking = self.carrier.book(flight_id, cabin, passenger_names, last_name)
            flight = self.carrier.flight(booking.flight_id)
        except CarrierError as e:
            raise _fail(e) from e
        return (
            f"Booked {len(booking.passengers)} {cabin} passenger(s) on flight {flight.number}, "
            f"{speech.say_day(flight.departs.date())} at {speech.say_time(flight.departs)}, "
            f"{CITIES[flight.origin]} to {CITIES[flight.destination]}. "
            f"Total {speech.say_money(booking.total)}. "
            f"Booking reference: {speech.spell_ref(booking.reference)}. "
            "A secure payment link is sent by SMS, and the booking is held for 24 hours. "
            "Say the reference spelled out."
        )

    @function_tool
    async def manage_booking(
        self,
        action: Literal["lookup", "change_flight", "cancel"],
        booking_reference: str,
        last_name: str,
        new_flight_id: str = "",
        confirmed: bool = False,
    ) -> str:
        """Look up, change or cancel an existing booking.

        Always lookup first. To change, search flights on the same route and pass the chosen flight id as
        new_flight_id. To cancel, call once with confirmed false to get the refund, ask the caller for a clear yes,
        then call again with confirmed true.

        Args:
            action: lookup, change_flight or cancel.
            booking_reference: The six character booking reference.
            last_name: The last name on the booking.
            new_flight_id: For change_flight, the id of the new flight from search results.
            confirmed: For cancel, true only after the caller said yes to the refund.
        """
        try:
            booking = self.carrier.find_booking(booking_reference, last_name)
            flight = self.carrier.flight(booking.flight_id)
            if action == "lookup":
                state = "confirmed" if booking.status == "confirmed" else "cancelled"
                return (
                    f"Booking is {state}: {len(booking.passengers)} {booking.cabin} passenger(s) on flight "
                    f"{flight.number}, {CITIES[flight.origin]} to {CITIES[flight.destination]}, "
                    f"{speech.say_day(flight.departs.date())} at {speech.say_time(flight.departs)}"
                    f"{' (delayed ' + str(flight.delay_minutes) + ' minutes)' if flight.status == 'delayed' else ''}"
                    f"{' (flight cancelled by SkyBridge)' if flight.status == 'cancelled' else ''}. "
                    f"Total {speech.say_money(booking.total)}."
                )
            if action == "change_flight":
                if not new_flight_id:
                    raise ToolError("Search for flights on the same route first, then pass the chosen flight id.")
                new, diff = self.carrier.reschedule(booking, new_flight_id)
                extra = (
                    f"The fare difference is {speech.say_money(diff)}, sent by SMS payment link."
                    if diff
                    else "There is no extra charge."
                )
                return (
                    f"Moved to flight {new.number}, {speech.say_day(new.departs.date())} at "
                    f"{speech.say_time(new.departs)}. {extra}"
                )
            # cancel
            pct, amount = self.carrier.refund_for(booking)
            if booking.status != "confirmed":
                raise CarrierError("That booking is already cancelled.")
            if not confirmed:
                return (
                    f"Cancelling now refunds {pct} percent, which is {speech.say_money(amount)}. "
                    "Ask the caller to say yes, then call again with confirmed true."
                )
            pct, amount = self.carrier.cancel(booking)
            return (
                f"Cancelled. The refund is {pct} percent, {speech.say_money(amount)}, "
                "back to the original payment method within 7 business days."
            )
        except CarrierError as e:
            raise _fail(e) from e

    @function_tool
    async def check_flight_status(self, flight_number: str, travel_date: str) -> str:
        """Check the status, times and gate of one SkyBridge flight on one date.

        Args:
            flight_number: For example SB 202 or just 202.
            travel_date: The date as YYYY-MM-DD.
        """
        day = self._day(travel_date)
        f = self.carrier.find_by_number(flight_number, day)
        if f is None:
            raise ToolError("No SkyBridge flight with that number on that date. Ask the caller to check both.")
        route = f"{CITIES[f.origin]} to {CITIES[f.destination]}"
        if f.status == "cancelled":
            return f"Flight {f.number}, {route}, is cancelled. The caller can choose a free change or a full refund."
        if f.status == "delayed":
            new_dep = f.departs + timedelta(minutes=f.delay_minutes)
            return (
                f"Flight {f.number}, {route}, is delayed {f.delay_minutes} minutes. "
                f"New departure {speech.say_time(new_dep)}, gate {f.gate}."
            )
        return (
            f"Flight {f.number}, {route}, is on time. Departs {speech.say_time(f.departs)}, "
            f"arrives {speech.say_time(f.arrives)}, gate {f.gate}."
        )

    @function_tool
    async def take_message(
        self,
        kind: Literal["refund_request", "lost_baggage", "special_assistance", "feedback"],
        last_name: str,
        summary: str,
        booking_reference: str = "",
    ) -> str:
        """Send a request to the right SkyBridge team. A message is a request, not an approval.

        Args:
            kind: refund_request, lost_baggage, special_assistance or feedback.
            last_name: The caller's last name.
            summary: The caller's own words about what they need, in one or two sentences.
            booking_reference: Required for refund_request, lost_baggage and special_assistance.
        """
        try:
            if kind != "feedback" or booking_reference:
                self.carrier.find_booking(booking_reference, last_name)
            _, duplicate = self.carrier.add_message(kind, booking_reference, last_name, summary)
        except CarrierError as e:
            raise _fail(e) from e
        label = kind.replace("_", " ")
        if duplicate:
            return (
                f"That {label} was already sent. No second message was created. "
                f"{MESSAGE_TIMELINES[kind]} The front desk cannot speed it up."
            )
        return f"Sent the {label}. {MESSAGE_TIMELINES[kind]} The front desk cannot approve it."

    @function_tool
    async def record_emergency_escalation(self, reported_situation: str) -> str:
        """Record a described medical emergency or safety or security threat. Use this before anything else.

        Args:
            reported_situation: What the caller described, in their own words.
        """
        self.carrier.record_escalation(reported_situation)
        return (
            "Emergency escalation recorded. Tell the caller to call 112 now and alert the nearest airport "
            "or airline staff. Do no booking or other work."
        )
