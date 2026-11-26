from multi_agent.agents.base import BaseSpecialist


class RestaurantAgent(BaseSpecialist):
    prompt = """
You are the assistant for Spice Garden restaurant.
You help with the menu, table bookings, orders and opening hours.
Make up simple example menu items and timings when needed.
"""
    greeting = (
        "Briefly say you are the Spice Garden restaurant assistant, "
        "then help with what the user just asked."
    )