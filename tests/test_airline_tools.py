"""Tests the airline agent's tools directly, with no model and no audio.

Run with:  uv run pytest -q
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from livekit.agents import ToolError

from multi_agent.agents.airline import AirlineAgent
from multi_agent.agents.airline.carrier import open_carrier

NOW = datetime(2026, 11, 26, 9, 0)  # pinned so day names and times stay stable
TOMORROW = (NOW + timedelta(days=1)).date().isoformat()
IN_THREE = (NOW + timedelta(days=3)).date().isoformat()
IN_FOUR = (NOW + timedelta(days=4)).date().isoformat()


def make():
    carrier = open_carrier(NOW)
    return AirlineAgent(carrier=carrier, greet=False), carrier


def run(coro):
    return asyncio.run(coro)


def test_search_returns_options_with_ids_and_prices():
    agent, _ = make()
    out = run(agent.search_flights("Hyderabad", "Bangalore", TOMORROW))  # alias works
    assert "Hyderabad to Bengaluru" in out
    assert "SB200-20261127" in out and "rupees" in out


def test_search_shows_the_delay():
    agent, _ = make()
    out = run(agent.search_flights("HYD", "BLR", TOMORROW))
    assert "delayed 40 minutes" in out


def test_unknown_city_is_refused_with_the_served_cities():
    agent, _ = make()
    with pytest.raises(ToolError) as e:
        run(agent.search_flights("Paris", "Delhi", TOMORROW))
    assert "Hyderabad" in str(e.value)


def test_past_date_is_refused():
    agent, _ = make()
    with pytest.raises(ToolError):
        run(agent.search_flights("HYD", "BLR", "2026-11-01"))


def test_empty_day_suggests_next_dates():
    agent, carrier = make()
    for f in carrier.flights.values():
        if f.departs.date().isoformat() == TOMORROW and (f.origin, f.destination) == ("HYD", "BLR"):
            f.status = "cancelled"
    out = run(agent.search_flights("HYD", "BLR", TOMORROW))
    assert "No open flights" in out and "next dates" in out


def test_booking_takes_seats_and_returns_a_spelled_reference():
    agent, carrier = make()
    before = carrier.flight("SB200-20261127").seats["economy"]
    out = run(agent.book_flight("SB200-20261127", "economy", ["Sai Kumar", "Ravi Kumar"], "Kumar"))
    assert "Booking reference:" in out
    assert carrier.flight("SB200-20261127").seats["economy"] == before - 2
    assert len(carrier.bookings) == 3  # two demo bookings plus this one


def test_booking_refuses_when_seats_run_out():
    agent, carrier = make()
    carrier.flight("SB200-20261127").seats["business"] = 1
    with pytest.raises(ToolError) as e:
        run(agent.book_flight("SB200-20261127", "business", ["A One", "B Two"], "One"))
    assert "Only 1 business" in str(e.value)


def test_lookup_needs_matching_reference_and_last_name():
    agent, _ = make()
    out = run(agent.manage_booking("lookup", "K Q 7 M 2 X", "sharma"))  # spaces and case are fine
    assert "SB 202" in out and "confirmed" in out
    with pytest.raises(ToolError):
        run(agent.manage_booking("lookup", "KQ7M2X", "Wrong"))


def test_change_flight_moves_the_booking():
    agent, carrier = make()
    out = run(agent.manage_booking("change_flight", "KQ7M2X", "Sharma", new_flight_id="SB204-20261129"))
    assert "SB 204" in out
    assert carrier.bookings["KQ7M2X"].flight_id == "SB204-20261129"


def test_change_to_another_route_is_refused():
    agent, _ = make()
    with pytest.raises(ToolError):
        run(agent.manage_booking("change_flight", "KQ7M2X", "Sharma", new_flight_id="SB210-20261129"))


def test_cancel_needs_a_confirmed_yes_and_refunds_fully_far_out():
    agent, carrier = make()
    preview = run(agent.manage_booking("cancel", "KQ7M2X", "Sharma"))
    assert "100 percent" in preview
    assert carrier.bookings["KQ7M2X"].status == "confirmed"  # nothing happened yet
    done = run(agent.manage_booking("cancel", "KQ7M2X", "Sharma", confirmed=True))
    assert done.startswith("Cancelled")
    assert carrier.bookings["KQ7M2X"].status == "cancelled"


def test_cancel_inside_24_hours_refunds_half():
    agent, carrier = make()
    carrier.now = carrier.flight("SB202-20261129").departs - timedelta(hours=10)
    preview = run(agent.manage_booking("cancel", "KQ7M2X", "Sharma"))
    assert "50 percent" in preview


def test_changes_close_four_hours_before_departure():
    agent, carrier = make()
    carrier.now = carrier.flight("SB202-20261129").departs - timedelta(hours=3)
    with pytest.raises(ToolError):
        run(agent.manage_booking("change_flight", "KQ7M2X", "Sharma", new_flight_id="SB204-20261129"))


def test_flight_status_on_time_delayed_and_cancelled():
    agent, _ = make()
    assert "on time" in run(agent.check_flight_status("SB 200", TOMORROW))
    assert "delayed 40 minutes" in run(agent.check_flight_status("202", TOMORROW))
    third = (NOW + timedelta(days=2)).date().isoformat()
    assert "cancelled" in run(agent.check_flight_status("sb212", third))


def test_duplicate_refund_request_is_not_sent_twice():
    agent, carrier = make()
    first = run(agent.take_message("refund_request", "Sharma", "Refund please", booking_reference="KQ7M2X"))
    second = run(agent.take_message("refund_request", "Sharma", "Do it today", booking_reference="KQ7M2X"))
    assert first.startswith("Sent")
    assert "already sent" in second
    assert len(carrier.messages) == 1


def test_message_needs_a_valid_booking():
    agent, _ = make()
    with pytest.raises(ToolError):
        run(agent.take_message("lost_baggage", "Sharma", "Bag missing", booking_reference="ZZZZZZ"))


def test_feedback_needs_no_booking():
    agent, carrier = make()
    out = run(agent.take_message("feedback", "Rao", "Great crew"))
    assert out.startswith("Sent") and len(carrier.messages) == 1


def test_emergency_is_recorded_and_points_to_112():
    agent, carrier = make()
    out = run(agent.record_emergency_escalation("passenger collapsed at gate"))
    assert "112" in out and carrier.escalations == ["passenger collapsed at gate"]


def test_guide_has_the_policy_numbers_the_tools_use():
    agent, _ = make()
    guide = run(agent.read_airline_information())
    for phrase in ["4 hours before departure", "24 hours or more", "50 percent", "7 business days"]:
        assert phrase in guide
