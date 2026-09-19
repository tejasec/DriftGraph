"""driftgraph/voice/memory.py

Conversational memory manager for multi-turn voice and chat sessions.
Remembers dialogue history and formats contextual prompts for the RAG engine.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = Field(default_factory=time.time)


class ConversationSession(BaseModel):
    session_id: str
    turns: List[ConversationTurn] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    last_active: float = Field(default_factory=time.time)


class ConversationMemoryManager:
    """Manages conversational context across sessions."""

    def __init__(self, max_history_turns: int = 6):
        self.max_history_turns = max_history_turns
        self._sessions: Dict[str, ConversationSession] = {}

    def get_session(self, session_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id)
        return self._sessions[session_id]

    def add_user_message(self, session_id: str, content: str) -> None:
        session = self.get_session(session_id)
        session.turns.append(ConversationTurn(role="user", content=content))
        session.last_active = time.time()
        # Keep only recent turns
        if len(session.turns) > self.max_history_turns * 2:
            session.turns = session.turns[-(self.max_history_turns * 2):]

    def add_assistant_message(self, session_id: str, content: str) -> None:
        session = self.get_session(session_id)
        session.turns.append(ConversationTurn(role="assistant", content=content))
        session.last_active = time.time()
        if len(session.turns) > self.max_history_turns * 2:
            session.turns = session.turns[-(self.max_history_turns * 2):]

    def format_history_prompt(self, session_id: str) -> str:
        """Format prior turns into a context block to inject into LLM queries."""
        session = self._sessions.get(session_id)
        if not session or not session.turns:
            return ""

        lines = ["Prior Conversation Context:"]
        for turn in session.turns[-self.max_history_turns:]:
            prefix = "User" if turn.role == "user" else "Assistant"
            lines.append(f"{prefix}: {turn.content}")
        return "\n".join(lines) + "\n\n"

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
