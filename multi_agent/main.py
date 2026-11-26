import os

from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import silero

from multi_agent.agents.airline import AirlineAgent
from multi_agent.agents.bank import BankAgent
from multi_agent.agents.clinic import ClinicAgent
from multi_agent.agents.interview import InterviewAgent
from multi_agent.agents.restaurant import RestaurantAgent
from multi_agent.agents.school import SchoolAgent

from multi_agent.config.settings import AGENT_NAME, build_llm, build_stt, build_tts
from multi_agent.config.voice_settings import VOICE_SETTINGS
from multi_agent.state import CallState
from multi_agent.supervisor.agent import SupervisorAgent


START_AGENT = os.getenv("START_AGENT", "supervisor").lower()


AGENT_MAP = {
    "supervisor": SupervisorAgent,
    "airline": AirlineAgent,
    "bank": BankAgent,
    "clinic": ClinicAgent,
    "interview": InterviewAgent,
    "restaurant": RestaurantAgent,
    "school": SchoolAgent,
}


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    session = AgentSession(
        userdata=CallState(),
        vad=ctx.proc.userdata["vad"],
        stt=build_stt(),
        llm=build_llm(),
        tts=build_tts(
            VOICE_SETTINGS["tts"]["voices"]["supervisor"]
        ),
        turn_handling=TurnHandlingOptions(
            endpointing=VOICE_SETTINGS["endpointing"],
            interruption=VOICE_SETTINGS["interruption"],
            preemptive_generation=VOICE_SETTINGS["preemptive_generation"],
        ),
    )

    agent_class = AGENT_MAP.get(START_AGENT)

    if agent_class is None:
        raise ValueError(
            f"Unknown agent: {START_AGENT}. "
            f"Available agents: {', '.join(AGENT_MAP.keys())}"
        )

    agent = agent_class()

    print(f"Starting agent: {START_AGENT}")

    await session.start(agent=agent, room=ctx.room)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name=AGENT_NAME,
        )
    )