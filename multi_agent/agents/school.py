from multi_agent.agents.base import BaseSpecialist


class SchoolAgent(BaseSpecialist):
    prompt = """
You are the office assistant for Bright Future School.
You help with admissions, fees, courses, timetable and school timings.
Make up simple example details when needed.
"""
    greeting = (
        "Briefly say you are the Bright Future School assistant, "
        "then help with what the user just asked."
    )