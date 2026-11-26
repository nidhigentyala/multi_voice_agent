
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    cli,
)
from livekit.plugins import silero

from multi_agent.config.settings import (
    AGENT_NAME,
    build_llm,
    build_stt,
    build_tts,
)
from multi_agent.config.voice_settings import VOICE_SETTINGS
from multi_agent.supervisor.agent import SupervisorAgent


# Create the new LiveKit AgentServer
server = AgentServer()


# Load VAD before the agent job starts
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


# Register the prewarm function
server.setup_fnc = prewarm


# Register your main supervisor agent
@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext):

    # Connect to the LiveKit room
    await ctx.connect()

    # Create the voice session
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=build_stt(),
        llm=build_llm(),
        tts=build_tts(),
        turn_handling=TurnHandlingOptions(
            endpointing=VOICE_SETTINGS["endpointing"],
            interruption=VOICE_SETTINGS["interruption"],
            preemptive_generation=VOICE_SETTINGS["preemptive_generation"],
        ),
    )

    # Start the supervisor agent
    await session.start(
        agent=SupervisorAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
