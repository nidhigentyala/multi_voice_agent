"""In-memory airline: schedule, bookings and messages.

Framework-free on purpose (no LiveKit imports). To go live, replace this
package with your reservation system client and keep the agent unchanged.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import random

CITIES = {
    "HYD": "Hyderabad",
    "BLR": "Bengaluru",
    "DEL": "Delhi",
    "BOM": "Mumbai",
    "MAA": "Chennai",
}
ALIASES = {"bangalore": "BLR", "bombay": "BOM", "madras": "MAA", "new delhi": "DEL"}

# Policy numbers. The Markdown guide in airline_info/ must say the same things.
BOOKING_CUTOFF_HOURS = 2      # no new bookings inside 2 hours of departure
CHANGE_CUTOFF_HOURS = 4       # no changes inside 4 hours of departure
FULL_REFUND_HOURS = 24        # cancel 24h+ before departure: full refund
PARTIAL_REFUND_PERCENT = 50   # cancel inside 24h: 50% refund
MAX_PASSENGERS = 6

MESSAGE_TIMELINES = {
    "refund_request": "The refunds team will reply within 7 business days.",
    "lost_baggage": "The baggage team will call back within 24 hours.",
    "special_assistance": "The assistance team will confirm before departure.",
    "feedback": "The customer care team reads all feedback within 3 business days.",
}

REF_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0, O, 1, I


class CarrierError(Exception):
    """A rule of the airline was not met. The message is safe to say aloud."""


def resolve_airport(text: str) -> str | None:
    t = text.strip().lower().removesuffix(" airport").strip()
    if not t:
        return None
    for code, city in CITIES.items():
        if t in (code.lower(), city.lower()):
            return code
    return ALIASES.get(t)


def normalize_ref(reference: str) -> str:
    return "".join(ch for ch in reference.upper() if ch.isalnum())


@dataclass
class Flight:
    id: str  # internal, e.g. SB200-20261127. Never spoken.
    number: str  # spoken, e.g. "SB 200"
    origin: str
    destination: str
    departs: datetime
    arrives: datetime
    fares: dict[str, int]  # cabin -> rupees per passenger
    seats: dict[str, int]  # cabin -> seats left
    gate: str
    status: str = "on_time"  # on_time | delayed | cancelled
    delay_minutes: int = 0


@dataclass
class Booking:
    reference: str
    last_name: str
    passengers: list[str]
    flight_id: str
    cabin: str
    total: int
    status: str = "confirmed"  # confirmed | cancelled


@dataclass
class Message:
    kind: str
    reference: str
    last_name: str
    summary: str


@dataclass
class Carrier:
    now: datetime
    flights: dict[str, Flight] = field(default_factory=dict)
    bookings: dict[str, Booking] = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)
    escalations: list[str] = field(default_factory=list)
    last_day: date | None = None

    # ---- flights -------------------------------------------------------
    def flight(self, flight_id: str) -> Flight:
        f = self.flights.get(flight_id.strip())
        if f is None:
            raise CarrierError(
                "That flight id is not valid. Search for flights again and use an id from the results."
            )
        return f

    def find_by_number(self, number: str, day: date) -> Flight | None:
        key = "".join(ch for ch in number.upper() if ch.isalnum())
        if key.isdigit():
            key = "SB" + key
        for f in self.flights.values():
            if f.number.replace(" ", "") == key and f.departs.date() == day:
                return f
        return None

    def search(
        self, origin: str, destination: str, day: date, cabin: str = "any", passengers: int = 1
    ) -> list[Flight]:
        earliest = self.now + timedelta(hours=BOOKING_CUTOFF_HOURS)
        cabins = ("economy", "business") if cabin == "any" else (cabin,)
        found = []
        for f in self.flights.values():
            if (f.origin, f.destination) != (origin, destination):
                continue
            if f.departs.date() != day or f.departs < earliest or f.status == "cancelled":
                continue
            if any(f.seats[c] >= passengers for c in cabins):
                found.append(f)
        return sorted(found, key=lambda f: f.departs)

    def next_dates(self, origin: str, destination: str, after: date, passengers: int = 1, limit: int = 3):
        days = []
        d = after + timedelta(days=1)
        while self.last_day and d <= self.last_day and len(days) < limit:
            if self.search(origin, destination, d, "any", passengers):
                days.append(d)
            d += timedelta(days=1)
        return days

    def _check_bookable(self, flight: Flight) -> None:
        if flight.status == "cancelled":
            raise CarrierError("That flight is cancelled. Search for another flight.")
        if flight.departs < self.now + timedelta(hours=BOOKING_CUTOFF_HOURS):
            raise CarrierError("That flight is too close to departure to book. Search for a later flight.")

    # ---- bookings ------------------------------------------------------
    def _new_reference(self) -> str:
        while True:
            ref = "".join(random.choices(REF_ALPHABET, k=6))
            if ref not in self.bookings:
                return ref

    def book(
        self, flight_id: str, cabin: str, names: list[str], last_name: str, reference: str | None = None
    ) -> Booking:
        flight = self.flight(flight_id)
        self._check_bookable(flight)
        if cabin not in ("economy", "business"):
            raise CarrierError("The cabin must be economy or business.")
        n = len(names)
        if not 1 <= n <= MAX_PASSENGERS:
            raise CarrierError(f"A booking can have 1 to {MAX_PASSENGERS} passengers.")
        if flight.seats[cabin] < n:
            raise CarrierError(
                f"Only {flight.seats[cabin]} {cabin} seats are left on that flight. "
                "Offer another cabin or search again."
            )
        flight.seats[cabin] -= n
        booking = Booking(
            reference=reference or self._new_reference(),
            last_name=last_name.strip(),
            passengers=[x.strip() for x in names],
            flight_id=flight.id,
            cabin=cabin,
            total=flight.fares[cabin] * n,
        )
        self.bookings[booking.reference] = booking
        return booking

    def find_booking(self, reference: str, last_name: str) -> Booking:
        b = self.bookings.get(normalize_ref(reference))
        if b is None or b.last_name.strip().lower() != last_name.strip().lower():
            raise CarrierError(
                "No booking matches that reference and last name. Ask the caller to check both."
            )
        return b

    def reschedule(self, booking: Booking, new_flight_id: str) -> tuple[Flight, int]:
        if booking.status != "confirmed":
            raise CarrierError("That booking is cancelled, so it can't be changed.")
        old = self.flight(booking.flight_id)
        if old.departs - self.now < timedelta(hours=CHANGE_CUTOFF_HOURS):
            raise CarrierError(
                f"Changes close {CHANGE_CUTOFF_HOURS} hours before departure, so this booking can't be changed now."
            )
        new = self.flight(new_flight_id)
        if new.id == old.id:
            raise CarrierError("The booking is already on that flight.")
        if (new.origin, new.destination) != (old.origin, old.destination):
            raise CarrierError("A change must keep the same route. Search the same route again.")
        self._check_bookable(new)
        n = len(booking.passengers)
        if new.seats[booking.cabin] < n:
            raise CarrierError(f"Not enough {booking.cabin} seats on that flight. Search again.")
        diff = max(0, (new.fares[booking.cabin] - old.fares[booking.cabin]) * n)
        old.seats[booking.cabin] += n
        new.seats[booking.cabin] -= n
        booking.flight_id = new.id
        booking.total += diff
        return new, diff

    def refund_for(self, booking: Booking) -> tuple[int, int]:
        flight = self.flight(booking.flight_id)
        hours = (flight.departs - self.now).total_seconds() / 3600
        if hours <= 0:
            raise CarrierError("That flight has already departed, so it can't be cancelled or refunded.")
        pct = 100 if hours >= FULL_REFUND_HOURS else PARTIAL_REFUND_PERCENT
        return pct, booking.total * pct // 100

    def cancel(self, booking: Booking) -> tuple[int, int]:
        if booking.status != "confirmed":
            raise CarrierError("That booking is already cancelled.")
        pct, amount = self.refund_for(booking)
        self.flight(booking.flight_id).seats[booking.cabin] += len(booking.passengers)
        booking.status = "cancelled"
        return pct, amount

    # ---- messages and escalations --------------------------------------
    def add_message(self, kind: str, reference: str, last_name: str, summary: str):
        ref = normalize_ref(reference)
        for m in self.messages:
            if m.kind == kind and m.reference == ref and m.last_name.lower() == last_name.strip().lower():
                return m, True
        m = Message(kind, ref, last_name.strip(), summary.strip())
        self.messages.append(m)
        return m, False

    def record_escalation(self, situation: str) -> None:
        self.escalations.append(situation.strip())
