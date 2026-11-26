import os
from pathlib import Path

from dotenv import load_dotenv
from livekit.plugins import openai, sarvam

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


def build_tts(speaker: str | None = None):
    cfg = dict(VOICE_SETTINGS["tts"])
    if speaker:
        cfg["speaker"] = speaker  # per-agent voice override
    return sarvam.TTS(**cfg)