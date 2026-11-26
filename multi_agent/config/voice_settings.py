VOICE_SETTINGS = {
    "stt": {
        "model": "saaras:v4",
        "language": "en-IN",   # was "unknown"; unknown guessed other languages from noise
        "mode": "transcribe",
    },
    "tts": {
        "provider": "cartesia",
        "model": "sonic-3",
        "language": "en",
        "speed": 1.0,
         "voices": {
            "supervisor": "39d518b7-fd0b-4676-9b8b-29d64ff31e12",
            "airline": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        },
    },
    "endpointing": {
        "mode": "dynamic",
        "min_delay": 0.3,
        "max_delay": 2.5,
    },
    "interruption": {
        "mode": "vad",
        "min_duration": 0.5,
        "min_words": 2,
        "false_interruption_timeout": 2.0,
        "resume_false_interruption": True,
    },
    "preemptive_generation": {
        "enabled": True,
        "preemptive_tts": True,
        "max_speech_duration": 10.0,
        "max_retries": 3,
    },
    # Not applied yet. See Step 5.
    "noise_cancellation": {
        "enabled": False,
        "provider": "ai_coustics",
        "profile": "voice_isolation",
        "models": {
            "voice_isolation": "QUAIL_VF_S",
            "noise_suppression": "QUAIL_L",
        },
    },
}