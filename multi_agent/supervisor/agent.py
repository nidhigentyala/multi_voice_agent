from livekit.agents import Agent, RunContext, function_tool

from multi_agent.agents.airline import AirlineAgent
from multi_agent.agents.bank import BankAgent
from multi_agent.agents.clinic import ClinicAgent
from multi_agent.agents.interview import InterviewAgent
from multi_agent.agents.restaurant import RestaurantAgent
from multi_agent.agents.school import SchoolAgent
from multi_agent.supervisor.prompts import (
    GREETING_RETURNING,
    GREETING_TEXT,
    SUPERVISOR_PROMPT,
)


class SupervisorAgent(Agent):
    def __init__(self, returning: bool = False, **kwargs):
        super().__init__(instructions=SUPERVISOR_PROMPT, **kwargs)
        self._returning = returning

    async def on_enter(self):
        if self._returning:
            await self.session.generate_reply(
                instructions=GREETING_RETURNING
            )
        else:
            await self.session.say(GREETING_TEXT)

    @function_tool
    async def transfer_to_restaurant(self, context: RunContext):
        """Use when the user wants the menu, a table booking, food orders or restaurant timings."""
        return RestaurantAgent(chat_ctx=self.chat_ctx), "Connecting to the restaurant assistant."

    @function_tool
    async def transfer_to_clinic(self, context: RunContext):
        """Use when the user wants a doctor appointment, clinic hours or clinic information."""
        return ClinicAgent(chat_ctx=self.chat_ctx), "Connecting to the clinic assistant."

    @function_tool
    async def transfer_to_school(self, context: RunContext):
        """Use when the user asks about school admissions, fees, courses, timetable or school timings."""
        return SchoolAgent(chat_ctx=self.chat_ctx), "Connecting to the school assistant."

    @function_tool
    async def transfer_to_bank(self, context: RunContext):
        """Use when the user asks about bank accounts, cards, loans or branch information."""
        return BankAgent(chat_ctx=self.chat_ctx), "Connecting to the bank assistant."

    @function_tool
    async def transfer_to_interview(self, context: RunContext):
        """Use when the user wants a practice interview or a resume-based interview."""
        return InterviewAgent(chat_ctx=self.chat_ctx), "Connecting to the interview assistant."

    @function_tool
    async def transfer_to_airline(self, context: RunContext):
        """Use when the user wants to book, change or cancel a flight, check flight status, or asks about airline baggage or check-in."""
        return AirlineAgent(
            chat_ctx=self.chat_ctx,
            greet=True,
        ), "Connecting to the airline assistant."
