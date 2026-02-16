"""Thinking Stream — captures and classifies Opus 4.6 thinking blocks in real-time.

Provides structured phase detection and a typewriter-console HTML formatter
for displaying the Reader Agent's reasoning process in the Streamlit UI.
"""

from __future__ import annotations

import html as html_mod
import re
from enum import Enum


class ThinkingPhase(Enum):
    """Phases of epidemic model extraction reasoning."""
    READING = "Reading Paper"
    IDENTIFYING = "Identifying Compartments"
    EXTRACTING = "Extracting Parameters"
    FORMULATING = "Formulating ODE System"
    INITIAL_CONDITIONS = "Setting Initial Conditions"
    CROSS_REFERENCING = "Cross-referencing Results"
    SYNTHESIZING = "Synthesizing Model"


_PHASE_PATTERNS: dict[ThinkingPhase, str] = {
    ThinkingPhase.SYNTHESIZING: (
        r"summar|complet|final(?:ly|ize)|putting\s+(?:it\s+)?(?:all\s+)?together"
        r"|model\s+spec|ready\s+to\s+submit|now\s+(?:I\s+)?(?:can|will)\s+submit"
    ),
    ThinkingPhase.CROSS_REFERENCING: (
        r"[Ff]igure\s+\d|[Tt]able\s+\d|reported\s+(?:result|value)"
        r"|peak\s+(?:day|time|infection)|attack\s+rate|validate|verify|reproduct"
    ),
    ThinkingPhase.INITIAL_CONDITIONS: (
        r"initial\s+condition|population\s*[=:]|N\s*="
        r"|starting\s+value|t\s*=\s*0|baseline\s+scenario|at\s+time\s+zero"
    ),
    ThinkingPhase.FORMULATING: (
        r"differential\s+equation|ODE|d[A-Z]/?dt|derivative"
        r"|dynamics|flow\s+(?:from|between|into)|transition"
        r"|def\s+derivatives|return\s*\["
    ),
    ThinkingPhase.EXTRACTING: (
        r"parameter|transmission\s+rate|recovery\s+rate"
        r"|beta|gamma|sigma|alpha|delta|epsilon"
        r"|incubation|infectious\s+period|reproduction\s+number"
        r"|rate\s*=|value\s+of"
    ),
    ThinkingPhase.IDENTIFYING: (
        r"compartment|susceptible|infected|recovered|exposed"
        r"|SEIR|SIR[^a-z]|SIS[^a-z]|SIDARTHE|state\s+variable"
        r"|population\s+class|diagram"
    ),
}

# Compiled patterns (ordered most-specific first)
_COMPILED_PHASES: list[tuple[ThinkingPhase, re.Pattern]] = [
    (phase, re.compile(pattern, re.IGNORECASE))
    for phase, pattern in _PHASE_PATTERNS.items()
]


def classify_phase(text: str) -> ThinkingPhase:
    """Classify a window of thinking text into the most specific matching phase."""
    for phase, pattern in _COMPILED_PHASES:
        if pattern.search(text):
            return phase
    return ThinkingPhase.READING


class ThinkingAccumulator:
    """Accumulates thinking chunks, tracks phase transitions, and formats HTML.

    Used by the Reader Agent callback to build the real-time thinking console.
    """

    def __init__(self):
        self._sections: list[tuple[ThinkingPhase, str]] = []
        self._current_phase = ThinkingPhase.READING
        self._current_text = ""
        self._window = ""

    def add_chunk(self, chunk: str) -> None:
        """Add a thinking text chunk. Triggers phase reclassification every ~300 chars."""
        self._current_text += chunk
        self._window += chunk

        if len(self._window) > 300:
            new_phase = classify_phase(self._window[-500:])
            if new_phase != self._current_phase:
                # Save completed phase section
                self._sections.append((self._current_phase, self._current_text))
                self._current_phase = new_phase
                self._current_text = ""
            self._window = self._window[-500:]

    @property
    def full_text(self) -> str:
        """All accumulated thinking text (for storage in session state)."""
        parts = [text for _, text in self._sections]
        parts.append(self._current_text)
        return "".join(parts)

    def format_html(self) -> str:
        """Format the accumulated thinking as HTML for the typewriter console.

        Shows completed phases as collapsed headers with char counts,
        and the current phase with its latest ~1500 characters of text.
        """
        parts: list[str] = []

        # Completed phases — collapsed with char count
        for phase, text in self._sections:
            n = len(text)
            parts.append(
                f'<span class="phase">'
                f'{html_mod.escape(phase.value)} '
                f'<span style="opacity:0.4;font-size:0.65rem">'
                f'({n:,} chars)</span></span>\n'
            )

        # Current phase — full header + tail of thinking text
        parts.append(
            f'<span class="phase">'
            f'{html_mod.escape(self._current_phase.value)}</span>\n'
        )

        current = self._current_text
        if len(current) > 1500:
            current = "..." + current[-1500:]
        parts.append(html_mod.escape(current))

        content = "".join(parts)

        return (
            f'<div class="thinking-live-container">'
            f'<div class="thinking-live-header">'
            f'<span class="thinking-dot"></span>'
            f'Extended Thinking &mdash; Reader Agent'
            f'<span class="opus-tag">Opus 4.6</span>'
            f'</div>'
            f'<div class="thinking-live-console">'
            f'{content}'
            f'<span class="cursor">|</span>'
            f'</div>'
            f'</div>'
        )
