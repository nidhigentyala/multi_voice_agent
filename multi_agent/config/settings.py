import os
from pathlib import Path

from dotenv import load_dotenv
from livekit.plugins import openai, sarvam
from livekit.plugins import cartesia

from multi_agent.config.voice_settings import VOICE_SETTINGS

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)

# Must match the agent_name your client uses when it dispatches the agent.
AGENT_NAME = "multi-agent"

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-mini")


def build_stt():
    return sarvam.STT(**VOICE_SETTINGS["stt"])


def build_llm():
    # Do not set temperature: gpt-5 models can reject it.
    return openai.LLM(model=LLM_MODEL)


def build_tts(voice_id: str):
    tts_settings = VOICE_SETTINGS["tts"]

    return cartesia.TTS(
        model=tts_settings["model"],
        voice=voice_id,
        language=tts_settings["language"],
        speed=tts_settings["speed"],
    )