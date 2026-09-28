"""
journal.py — MindLog v2.0 polished daily journal form.
"""

from __future__ import annotations

import datetime
from typing import Optional

import streamlit as st

from config import (
    MOOD_LABELS, STRESS_LABELS, ENERGY_LABELS,
    POSITIVE_ACTIVITIES, NEGATIVE_ACTIVITIES,
)
from database import get_entry_for_date, upsert_entry, JournalEntry


def _prefill(entry: Optional[JournalEntry]) -> dict:
    if entry is None:
        return dict(mood=5, stress=5, energy=6, sleep=7.5,
                    journal_notes="", gratitude_notes="",
                    pos_acts=[], neg_acts=[])
    acts = (entry.activities or "").split(",")
    return dict(
        mood=entry.mood_score,
        stress=entry.stress_score,
        energy=entry.energy_level or 6,
        sleep=entry.sleep_hours or 7.5,
        journal_notes=entry.journal_notes or "",
        gratitude_notes=entry.gratitude_notes or "",
        pos_acts=[a for a in acts if a in POSITIVE_ACTIVITIES],
        neg_acts=[a for a in acts if a in NEGATIVE_ACTIVITIES],
    )


def render_journal_form(username: str) -> None:

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown("## 📝 Daily Journal")
    st.markdown(
        "> *Log how you feel — your data stays private and helps AI track your wellness trends.*"
    )
    st.divider()

    # ── Date picker ────────────────────────────────────────────────────────────
    dc1, dc2 = st.columns([2, 5])
    with dc1:
        entry_date: datetime.date = st.date_input(
            "Entry Date",
            value=datetime.date.today(),
            max_value=datetime.date.today(),
            key="journal_date",
        )
    with dc2:
        st.markdown(f"#### {entry_date.strftime('%A, %B %d %Y')}")
        st.caption("You can back-fill entries for any past date.")

    existing = get_entry_for_date(username, entry_date)
    pf = _prefill(existing)

    if existing:
        st.info("✏️  An entry already exists for this date — you are editing it.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — WELLNESS SCORES
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🌡️ Wellness Scores")
    st.caption("Drag each slider to reflect how you feel right now.")

    sc1, sc2, sc3 = st.columns(3)

    with sc1:
        mood = st.slider("Mood", 1, 10, pf["mood"], key="mood_sl",
                         help="1 = Terrible · 10 = Amazing")
        m_name, m_emoji, m_color = MOOD_LABELS[mood]
        st.metric("Mood Score", f"{mood}/10", delta=f"{m_emoji} {m_name}")

    with sc2:
        stress = st.slider("Stress Level", 1, 10, pf["stress"], key="stress_sl",
                           help="1 = Completely Calm · 10 = Overwhelmed")
        s_name, s_emoji, s_color = STRESS_LABELS[stress]
        st.metric("Stress Score", f"{stress}/10", delta=f"{s_emoji} {s_name}",
                  delta_color="inverse")

    with sc3:
        energy = st.slider("Energy Level", 1, 10, pf["energy"], key="energy_sl",
                           help="1 = Exhausted · 10 = Fully Charged")
        st.metric("Energy Score", f"{energy}/10", delta=ENERGY_LABELS[energy])

    # Mood emoji bar
    st.markdown("---")
    cols = st.columns(10)
    for i, col in enumerate(cols, start=1):
        _, em, _ = MOOD_LABELS[i]
        col.markdown(f"**{em}**" if i == mood else em)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — SLEEP
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 💤 Sleep")
    sl1, sl2 = st.columns([2, 5])
    with sl1:
        sleep = st.number_input(
            "Hours slept last night",
            min_value=0.0, max_value=16.0,
            value=float(pf["sleep"]), step=0.5, key="sleep_inp",
        )
    with sl2:
        if sleep < 5:
            st.warning(f"Only **{sleep}h** — poor sleep significantly impacts mood and cognition.")
        elif sleep > 9:
            st.info(f"**{sleep}h** — oversleeping can sometimes signal low energy or low mood.")
        else:
            st.success(f"**{sleep}h** — you're in the healthy sleep range!")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — ACTIVITIES
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🏃 Today's Activities & Habits")
    st.caption("Select all that apply. This helps the AI understand your lifestyle patterns.")

    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**Positive habits:**")
        pos_acts = st.multiselect(
            "Positive", POSITIVE_ACTIVITIES,
            default=[a for a in pf["pos_acts"] if a in POSITIVE_ACTIVITIES],
            key="pos_acts", label_visibility="collapsed",
        )
    with a2:
        st.markdown("**Challenging habits:**")
        neg_acts = st.multiselect(
            "Negative", NEGATIVE_ACTIVITIES,
            default=[a for a in pf["neg_acts"] if a in NEGATIVE_ACTIVITIES],
            key="neg_acts", label_visibility="collapsed",
        )

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — JOURNAL
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📖 Free Journal")
    st.caption("Write freely — no structure needed. The more detail, the better the AI insights.")
    journal_notes = st.text_area(
        "What is on your mind today?",
        value=pf["journal_notes"], height=180,
        placeholder=(
            "How are you feeling? What happened today?\n"
            "Any worries, wins, or thoughts worth capturing?"
        ),
        key="jnotes",
    )

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — GRATITUDE
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🙏 Gratitude Check-in")
    st.caption(
        "Research shows noting 3 things you are grateful for each day "
        "meaningfully improves long-term wellbeing."
    )
    gratitude_notes = st.text_area(
        "What are you grateful for today?",
        value=pf["gratitude_notes"], height=110,
        placeholder="1. A good coffee this morning\n2. A kind message from a friend\n3. Sunshine outside",
        key="gnotes",
    )

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SAVE BUTTON
    # ══════════════════════════════════════════════════════════════════════════
    b1, b2 = st.columns([2, 5])
    with b1:
        save = st.button("💾  Save Entry", type="primary", use_container_width=True)
    with b2:
        st.caption(
            "After saving, visit **AI Insights** for personalised feedback "
            "or **Analytics Dashboard** to see your trends."
        )

    if save:
        entry = upsert_entry(
            username=username, entry_date=entry_date,
            mood_score=mood, stress_score=stress,
            energy_level=energy, sleep_hours=sleep,
            journal_notes=journal_notes, gratitude_notes=gratitude_notes,
            activities=",".join(pos_acts + neg_acts),
        )
        st.success(
            f"Entry saved for **{entry_date.strftime('%A, %B %d %Y')}**! "
            "Head to AI Insights for personalised feedback."
        )
        st.session_state["last_saved_entry_id"] = entry.id
        st.balloons()
