"""Per-call state shared by every agent in one room (AgentSession userdata)."""

from dataclasses import dataclass, field
from datetime import datetime

from multi_agent.agents.airline.carrier import Carrier, open_carrier


@dataclass
class CallState:
    # One airline per call, so a booking survives a trip back to the main menu.
    carrier: Carrier = field(default_factory=lambda: open_carrier(datetime.now()))
