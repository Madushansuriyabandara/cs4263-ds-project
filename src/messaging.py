"""Message types and energy cost model."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List


class MessageType(Enum):
    ADV = "ADV"                  # leader advertisement
    JOIN = "JOIN"                # candidate requests to join
    HEARTBEAT = "HEARTBEAT"      # leader liveness signal
    ELECTION = "ELECTION"        # bully election message
    OK = "OK"                    # bully reply
    COORDINATOR = "COORDINATOR"  # winner announcement


@dataclass
class Message:
    sender_id: int
    recipient_ids: List[int]
    msg_type: MessageType
    step: int
    payload: dict = None

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}


# Energy cost per message sent (from assignment)
SEND_COST = 2
EXISTENCE_COST = 1
