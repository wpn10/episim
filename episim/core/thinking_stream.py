"""Thinking Stream — captures and classifies Opus 4.6 thinking blocks in real-time.

Two display modes:
- **Live**: During Reader Agent — fixed-height console, current phase only, newest
  text always visible (pinned to bottom via flexbox).
- **Replay**: During later pipeline stages — compact phase chips + rotating excerpt
  from the thinking analysis, keeping the user engaged throughout.
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
    """Accumulates thinking chunks, tracks phase transitions, renders two UI modes.

    Live mode: shows only the current phase + latest text (pinned to bottom).
    Replay mode: shows phase chips + a rotating excerpt for engagement during waits.
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

    def _all_sections(self) -> list[tuple[ThinkingPhase, str]]:
        """All sections including current work-in-progress."""
        return list(self._sections) + [(self._current_phase, self._current_text)]

    def _unique_phases(self) -> list[ThinkingPhase]:
        """Ordered list of unique phases encountered."""
        seen = set()
        result = []
        for phase, _ in self._all_sections():
            if phase not in seen:
                seen.add(phase)
                result.append(phase)
        return result

    # ── Live Mode ────────────────────────────────────────────────────────

    def format_live_html(self) -> str:
        """Render for LIVE streaming: current phase + latest text only.

        Fixed-height container with flex-end alignment so newest content
        is always visible at the bottom — no scrolling, no old phases
        taking up space.
        """
        current = self._current_text
        if len(current) > 800:
            current = current[-800:]
        escaped = html_mod.escape(current)

        return (
            '<div class="thinking-live-container">'
            '<div class="thinking-live-header">'
            '<span class="thinking-dot"></span>'
            'Extended Thinking &mdash; Reader Agent'
            '<span class="opus-tag">Opus 4.6</span>'
            '</div>'
            '<div class="thinking-live-console">'
            '<div class="thinking-content">'
            f'<span class="phase">{html_mod.escape(self._current_phase.value)}</span>\n'
            f'{escaped}'
            '<span class="cursor">|</span>'
            '</div>'
            '</div>'
            '</div>'
        )

    # ── Replay Mode ──────────────────────────────────────────────────────

    def format_replay_html(self, stage_label: str, excerpt_index: int = 0) -> str:
        """Render for REPLAY during later pipeline stages.

        Shows a compact row of completed-phase chips, then a rotating excerpt
        from the thinking analysis. Each pipeline stage gets a different excerpt
        by passing a different excerpt_index.
        """
        # Phase chips
        phases = self._unique_phases()
        chips_html = " ".join(
            f'<span class="phase-chip">{html_mod.escape(p.value)}</span>'
            for p in phases
        )

        # Pick excerpt by index (wraps around, skip tiny sections)
        content_sections = [
            (p, t) for p, t in self._all_sections() if len(t.strip()) > 50
        ]
        if content_sections:
            phase, text = content_sections[excerpt_index % len(content_sections)]
            excerpt = text.strip()[-400:]
            excerpt_html = (
                f'<span class="replay-phase">{html_mod.escape(phase.value)}</span>\n'
                f'{html_mod.escape(excerpt)}'
            )
        else:
            excerpt_html = '<span style="opacity:0.4">Analysis complete.</span>'

        return (
            '<div class="thinking-live-container">'
            '<div class="thinking-live-header thinking-replay-header">'
            '<span class="thinking-dot thinking-dot-slow"></span>'
            f'{html_mod.escape(stage_label)}'
            '<span class="opus-tag">Opus 4.6</span>'
            '</div>'
            '<div class="thinking-live-console thinking-replay-console">'
            '<div class="thinking-content">'
            f'<div class="phase-chips">{chips_html}</div>'
            f'<div class="replay-excerpt">{excerpt_html}</div>'
            '</div>'
            '</div>'
            '</div>'
        )

    # ── Parallel Execution Mode ──────────────────────────────────────────

    def format_parallel_html(
        self,
        running: list[tuple[str, str]],
        completed: list[tuple[str, str]],
        excerpt_index: int = 0,
    ) -> str:
        """Render for PARALLEL execution: agent status badges + thinking excerpt.

        Args:
            running: List of (agent_name, effort_level) for running agents.
            completed: List of (agent_name, effort_level) for completed agents.
            excerpt_index: Which thinking excerpt to show (wraps around).
        """
        badges = []
        for name, effort in completed:
            badges.append(
                f'<span class="agent-badge agent-done">'
                f'&#10003; {html_mod.escape(name)} '
                f'<span class="effort-label">{html_mod.escape(effort)}</span>'
                f'</span>'
            )
        for name, effort in running:
            badges.append(
                f'<span class="agent-badge agent-running">'
                f'&#9679; {html_mod.escape(name)} '
                f'<span class="effort-label">{html_mod.escape(effort)}</span>'
                f'</span>'
            )
        badges_html = " ".join(badges)

        # Thinking excerpt
        content_sections = [
            (p, t) for p, t in self._all_sections() if len(t.strip()) > 50
        ]
        if content_sections:
            phase, text = content_sections[excerpt_index % len(content_sections)]
            excerpt = text.strip()[-350:]
            excerpt_html = (
                f'<span class="replay-phase">'
                f'{html_mod.escape(phase.value)}</span>\n'
                f'{html_mod.escape(excerpt)}'
            )
        else:
            excerpt_html = ""

        n_running = len(running)
        header_text = (
            f"Parallel Execution &mdash; {n_running} agent{'s' if n_running != 1 else ''} running"
            if n_running > 0
            else "Parallel Execution &mdash; complete"
        )

        return (
            '<div class="thinking-live-container">'
            '<div class="thinking-live-header thinking-parallel-header">'
            '<span class="thinking-dot"></span>'
            f'{header_text}'
            '<span class="opus-tag">Opus 4.6</span>'
            '</div>'
            '<div class="thinking-live-console thinking-replay-console">'
            '<div class="thinking-content">'
            f'<div class="agent-badges">{badges_html}</div>'
            f'<div class="replay-excerpt">{excerpt_html}</div>'
            '</div>'
            '</div>'
            '</div>'
        )
