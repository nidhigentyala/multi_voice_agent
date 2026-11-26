
from livekit.agents import Agent, RunContext, function_tool

COMMON_RULES = """
You are a voice assistant on a phone-style call.
- Keep every reply to 1 or 2 short sentences.
- Speak plainly. No lists, no markdown, no emojis.
- Ask one question at a time.
- Never ask for or give out real personal, account, card or medical details.
  This is a demo, so use made-up example information.
- If the user wants a different service or says they are done, call back_to_menu.
"""


class BaseSpecialist(Agent):
    prompt: str = ""
    greeting: str = ""

    def __init__(self, **kwargs):
        super().__init__(
            instructions=COMMON_RULES + "\n" + self.prompt,
            **kwargs
        )

    async def on_enter(self):
        if self.greeting:
            await self.session.generate_reply(
                instructions=self.greeting
            )

    @function_tool
    async def back_to_menu(self, context: RunContext):
        """Use when the user wants a different service, or is finished with this one."""
        from multi_agent.supervisor.agent import SupervisorAgent

        return SupervisorAgent(
            returning=True,
            chat_ctx=self.chat_ctx,
        )
