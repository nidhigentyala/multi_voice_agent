"""A rolling 14-day schedule for the fictional SkyBridge Airways."""

from datetime import datetime, time, timedelta

from multi_agent.agents.airline.carrier.records import Carrier, Flight

# origin, destination, flight minutes, economy fare in rupees
ROUTES = [
    ("HYD", "BLR", 75, 3800),
    ("HYD", "DEL", 150, 6200),
    ("HYD", "BOM", 100, 4600),
    ("HYD", "MAA", 80, 3500),
    ("BLR", "DEL", 175, 6800),
    ("BLR", "BOM", 110, 4400),
    ("BOM", "DEL", 130, 5600),
]
SLOTS = [(7, 15, 1.00), (13, 40, 1.10), (19, 30, 0.95)]  # hour, minute, fare factor
DAYS = 14


def _round(value: float, step: int) -> int:
    return int(round(value / step)) * step


def open_carrier(now: datetime) -> Carrier:
    carrier = Carrier(now=now)
    start = now.date()
    carrier.last_day = start + timedelta(days=DAYS - 1)

    for offset in range(DAYS):
        day = start + timedelta(days=offset)
        for idx, (a, b, minutes, base) in enumerate(ROUTES):
            for slot, (hh, mm, factor) in enumerate(SLOTS):
                economy = _round(base * factor, 50)
                business = _round(economy * 2.6, 100)
                for leg, (orig, dest) in enumerate(((a, b), (b, a))):
                    number = 200 + idx * 10 + slot * 2 + leg
                    departs = datetime.combine(day, time(hh, mm)) + timedelta(minutes=idx * 5)
                    flight = Flight(
                        id=f"SB{number}-{day:%Y%m%d}",
                        number=f"SB {number}",
                        origin=orig,
                        destination=dest,
                        departs=departs,
                        arrives=departs + timedelta(minutes=minutes),
                        fares={"economy": economy, "business": business},
                        seats={"economy": 40, "business": 8},
                        gate=f"{'ABCD'[idx % 4]}{(slot * 3 + idx) % 9 + 1}",
                    )
                    carrier.flights[flight.id] = flight

    # Demo situations so the status and policy flows can be tested.
    delayed = carrier.flights.get(f"SB202-{start + timedelta(days=1):%Y%m%d}")
    if delayed:
        delayed.status, delayed.delay_minutes = "delayed", 40
    cancelled = carrier.flights.get(f"SB212-{start + timedelta(days=2):%Y%m%d}")
    if cancelled:
        cancelled.status = "cancelled"

    # Demo bookings for testing lookup, change and cancel.
    carrier.book(f"SB202-{start + timedelta(days=3):%Y%m%d}", "economy", ["Priya Sharma"], "Sharma", reference="KQ7M2X")
    carrier.book(
        f"SB210-{start + timedelta(days=4):%Y%m%d}", "business", ["Anil Reddy", "Meena Reddy"], "Reddy", reference="RT5N8P"
    )
    return carrier
