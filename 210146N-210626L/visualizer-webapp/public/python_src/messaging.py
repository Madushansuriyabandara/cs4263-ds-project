"""Message types & cost model."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class MessageType(Enum):
    ADV = "ADV"
    JOIN = "JOIN"
    HEARTBEAT = "HEARTBEAT"
    DATA = "DATA"
    AGG = "AGG"
    ELECTION = "ELECTION"
    OK = "OK"
    COORDINATOR = "COORDINATOR"
    VOTE = "VOTE"
    TOKEN = "TOKEN"


@dataclass
class Message:
    sender_id: int
    recipient_ids: List[int]
    msg_type: MessageType
    step: int
    payload: Dict[str, Any] = field(default_factory=dict)