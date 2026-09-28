"""
app.py — MindLog v2.0 · AI-Powered Mental Wellness Journal
Run with: streamlit run app.py
"""

from __future__ import annotations

import datetime
import streamlit as st

# ── MUST be the very first Streamlit call ─────────────────────────────────────
st.set_page_config(
    page_title="MindLog v2.0 — Mental Wellness Journal",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import (
    APP_TITLE, APP_TAGLINE, APP_ICON, APP_VERSION,
    PAGES, GEMINI_API_KEY, MOOD_LABELS,
)
from database import init_db, get_all_entries, get_entries, get_latest_therapist_note
from journal import render_journal_form
from analytics import (
    render_analytics_dashboard, entries_to_df,
    compute_summary, detect_patterns,
)
from ai_engine import analyse_entry, get_trend_insights, generate_therapist_report, chat_with_ai

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_db()

# ── Session defaults ──────────────────────────────────────────────────────────
_defaults = {
    "username":     "My Journal",
    "gemini_api_key": GEMINI_API_KEY,
    "chat_history": [],
    "active_page":  list(PAGES.keys())[0],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── Brand ─────────────────────────────────────────────────────────────────
    st.markdown(f"# {APP_ICON} **{APP_TITLE}**")
    st.caption(APP_TAGLINE)
    st.caption(f"v{APP_VERSION} · Gemini 2.5 Flash")
    st.divider()

    # ── Profile ───────────────────────────────────────────────────────────────
    st.markdown("### 👤 Profile")
    new_name = st.text_input(
        "Your name or alias",
        value=st.session_state["username"],
        key="username_field",
        help="No account required — data is stored locally.",
    )
    if new_name != st.session_state["username"]:
        st.session_state["username"] = new_name
        st.session_state["chat_history"] = []
        st.rerun()

    st.divider()

    # ── API Key ───────────────────────────────────────────────────────────────
    st.markdown("### 🔑 Gemini API Key")
    new_key = st.text_input(
        "Paste your key",
        value=st.session_state["gemini_api_key"],
        type="password",
        key="api_key_field",
        help="Free key at aistudio.google.com",
    )
    if new_key != st.session_state["gemini_api_key"]:
        st.session_state["gemini_api_key"] = new_key

    if st.session_state["gemini_api_key"]:
        st.success("AI features enabled")
    else:
        st.warning("Add key to unlock AI features")

    st.divider()

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("### 🗂️ Navigation")
    for _pg_name, _pg_icon in PAGES.items():
        _is_active = st.session_state["active_page"] == _pg_name
        if st.button(
            f"{_pg_icon}  {_pg_name}",
            key=f"nav_{_pg_name}",
            use_container_width=True,
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["active_page"] = _pg_name
            st.rerun()

    st.divider()

    # ── This week snapshot ────────────────────────────────────────────────────
    username     = st.session_state["username"]
    week_entries = get_entries(username, days=7)
    st.markdown("### 📈 This Week")
    if week_entries:
        df7   = entries_to_df(week_entries)
        wc1, wc2 = st.columns(2)
        wc1.metric("Avg Mood",   f"{df7['mood'].mean():.1f}")
        wc2.metric("Avg Stress", f"{df7['stress'].mean():.1f}")
        st.caption(f"{len(week_entries)} entries this week")
        emojis = "".join(MOOD_LABELS[int(round(e.mood_score))][1] for e in week_entries[:7])
        st.markdown(f"**Mood trail:** {emojis}")
    else:
        st.caption("No entries this week yet.")

    st.divider()

    # ── High-severity alert ───────────────────────────────────────────────────
    _all_entries = get_all_entries(username)
    if _all_entries:
        _df   = entries_to_df(_all_entries)
        _pats = detect_patterns(_df)
        _high = [p for p in _pats if p.severity == "high"]
        if _high:
            st.error(f"🚩 {len(_high)} high-severity pattern(s) detected!")
            for p in _high:
                st.caption(f"{p.icon} {p.pattern_type}")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═════════════════════════════════════════════════════════════════════════════
active      = st.session_state["active_page"]
username    = st.session_state["username"]
_active_icon = PAGES.get(active, "🧠")
all_entries  = get_all_entries(username)

h1, h2 = st.columns([5, 2])
with h1:
    st.markdown(f"# {_active_icon} {active}")
with h2:
    st.markdown(f"**User:** {username}")
    if all_entries:
        st.caption(f"{len(all_entries)} total entries")

st.divider()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DAILY JOURNAL
# ═════════════════════════════════════════════════════════════════════════════
if active == "Daily Journal":
    render_journal_form(username)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ANALYTICS DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
elif active == "Analytics Dashboard":
    render_analytics_dashboard(get_all_entries(username))


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — AI INSIGHTS
# ═════════════════════════════════════════════════════════════════════════════
elif active == "AI Insights":

    if not st.session_state["gemini_api_key"]:
        st.warning(
            "Add your **Gemini API key** in the sidebar to unlock AI features.  \n"
            "Get a free key at [aistudio.google.com](https://aistudio.google.com)"
        )
    else:
        entries = get_all_entries(username)
        tab1, tab2, tab3 = st.tabs(
            ["📊 Trend Insights", "📝 Analyse Latest Entry", "💬 Chat with MindBot"]
        )

        # ── Trend Insights ────────────────────────────────────────────────────
        with tab1:
            st.markdown("#### AI-Powered Trend Analysis")
            st.markdown(
                "Get a personalised analysis of your wellness trends, patterns, "
                "and tailored coping strategies — powered by Gemini 2.5 Flash."
            )
            if not entries:
                st.info("No entries yet. Log your first entry to see trend insights.")
            else:
                df_all  = entries_to_df(entries)
                summary = compute_summary(df_all)
                pats    = detect_patterns(df_all)

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Total Entries", summary.get("total_entries", 0))
                sc2.metric("Avg Mood",      f"{summary.get('avg_mood','—')}/10")
                sc3.metric("Avg Stress",    f"{summary.get('avg_stress','—')}/10")
                sc4.metric("Flagged Days",  summary.get("flagged_days", 0))

                if pats:
                    st.divider()
                    st.markdown("**Detected patterns (informing AI analysis):**")
                    for p in pats:
                        badge = {"high": "🔴", "medium": "🟠", "low": "🟡"}[p.severity]
                        st.caption(f"{badge} {p.icon} {p.pattern_type} — {p.description}")

                st.divider()
                if st.button("Generate AI Trend Insights", type="primary", key="gen_trend"):
                    with st.spinner("Analysing your wellness trends with Gemini 2.5 Flash..."):
                        result = get_trend_insights(entries)
                    st.session_state["trend_insight_cache"] = result

                if "trend_insight_cache" in st.session_state:
                    st.divider()
                    with st.container(border=True):
                        st.markdown(st.session_state["trend_insight_cache"])

        # ── Analyse Latest Entry ──────────────────────────────────────────────
        with tab2:
            st.markdown("#### Analyse Your Latest Entry")
            st.markdown("Receive personalised AI feedback on your most recent journal entry.")

            if not entries:
                st.info("No entries found. Write your first journal entry to get AI analysis.")
            else:
                latest = entries[0]
                m_name, m_emoji, _ = MOOD_LABELS[latest.mood_score]

                with st.container(border=True):
                    pc1, pc2, pc3, pc4 = st.columns(4)
                    pc1.markdown(f"**Date**  \n{latest.entry_date.strftime('%b %d, %Y') if latest.entry_date else 'N/A'}")
                    pc2.markdown(f"**Mood**  \n{m_emoji} {latest.mood_score}/10")
                    pc3.markdown(f"**Stress**  \n{latest.stress_score}/10")
                    pc4.markdown(f"**Sleep**  \n{latest.sleep_hours or 'N/A'}h")
                    if latest.journal_notes:
                        st.caption(latest.journal_notes[:280] + ("..." if len(latest.journal_notes or "") > 280 else ""))

                if latest.ai_insight:
                    st.divider()
                    st.markdown("**Previous AI analysis:**")
                    with st.container(border=True):
                        st.info(latest.ai_insight)
                        if latest.ai_suggestion:
                            st.markdown(f"*Suggestion: {latest.ai_suggestion}*")
                        if latest.ai_flagged:
                            st.error(f"Flagged: {latest.ai_flag_reason}")

                st.divider()
                if st.button("Analyse with Gemini 2.5 Flash", type="primary", key="analyse_btn"):
                    with st.spinner("Sending to Gemini 2.5 Flash..."):
                        result = analyse_entry(latest)

                    with st.container(border=True):
                        st.markdown("### Personal Insight")
                        st.write(result["insight"])

                    if result["flagged"]:
                        st.error(
                            f"**Concern Flagged for Therapist Review**  \n{result['flag_reason']}"
                        )
                    else:
                        st.success("No concerning patterns flagged in this entry.")

                    if result["suggestion"]:
                        with st.container(border=True):
                            st.markdown("### Suggested Action")
                            st.info(result["suggestion"])

        # ── MindBot Chat ──────────────────────────────────────────────────────
        with tab3:
            st.markdown("#### Chat with MindBot")
            st.markdown(
                "Ask about your trends, get coping advice, or just talk through "
                "how you are feeling. MindBot knows your journal history."
            )
            st.caption(
                "MindBot is not a licensed therapist. "
                "Consult a mental health professional for clinical support."
            )
            st.divider()

            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"], avatar="🧠" if msg["role"] == "assistant" else "👤"):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Ask MindBot anything..."):
                st.session_state["chat_history"].append({"role": "user", "content": prompt})
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt)
                with st.chat_message("assistant", avatar="🧠"):
                    with st.spinner("MindBot is thinking..."):
                        reply = chat_with_ai(prompt, entries)
                    st.markdown(reply)
                st.session_state["chat_history"].append({"role": "assistant", "content": reply})

            if st.session_state["chat_history"]:
                if st.button("Clear Chat", key="clr_chat"):
                    st.session_state["chat_history"] = []
                    st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — THERAPIST REPORT
# ═════════════════════════════════════════════════════════════════════════════
elif active == "Therapist Report":

    st.markdown(
        "Generate a **professional clinical wellness report** for your therapist.  \n"
        "Includes clinical summary, pattern analysis, risk assessment, and recommendations."
    )
    st.caption("Your data is only sent to Gemini when you click Generate — never stored externally.")

    if not st.session_state["gemini_api_key"]:
        st.warning("Add your Gemini API key in the sidebar to generate reports.")
    else:
        all_e = get_all_entries(username)
        if not all_e:
            st.info("No entries yet. Start journaling to generate a report.")
        else:
            rc1, rc2 = st.columns([2, 5])
            with rc1:
                period_opts = {"Last 7 days": 7, "Last 14 days": 14,
                               "Last 30 days": 30, "All time": 9999}
                selected = st.selectbox("Report period", list(period_opts.keys()), index=2)
            report_entries = get_entries(username, days=period_opts[selected]) \
                if period_opts[selected] < 9999 else all_e
            with rc2:
                st.info(f"Report will cover **{len(report_entries)} entries** ({selected.lower()}).")

            st.divider()
            if st.button("Generate Therapist Report", type="primary"):
                with st.spinner("Generating clinical report with Gemini 2.5 Flash..."):
                    report_text, concerning, recommendations = generate_therapist_report(
                        report_entries, username
                    )
                st.session_state["therapist_report_cache"] = {
                    "text": report_text, "concerning": concerning,
                    "recommendations": recommendations,
                    "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                }

            cached = st.session_state.get("therapist_report_cache")
            if not cached:
                saved = get_latest_therapist_note(username)
                if saved:
                    cached = {
                        "text": saved.report_text,
                        "concerning": saved.concerning_patterns or "",
                        "recommendations": saved.recommendations or "",
                        "generated_at": str(saved.generated_at)[:16],
                    }

            if cached:
                st.divider()
                dl_col, ts_col = st.columns([1, 4])
                with dl_col:
                    st.download_button(
                        "Download (.txt)", data=cached["text"],
                        file_name=f"mindlog_report_{username}_{datetime.date.today()}.txt",
                        mime="text/plain",
                    )
                with ts_col:
                    st.caption(f"Generated: {cached['generated_at']}")

                with st.container(border=True):
                    st.markdown(cached["text"])

                if cached.get("concerning"):
                    with st.expander("Concerning Patterns Detail"):
                        st.markdown(cached["concerning"])
                if cached.get("recommendations"):
                    with st.expander("Therapeutic Recommendations Detail"):
                        st.markdown(cached["recommendations"])


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5 — MY HISTORY
# ═════════════════════════════════════════════════════════════════════════════
elif active == "My History":

    all_e = get_all_entries(username)
    if not all_e:
        st.info("No entries yet. Head to **Daily Journal** to log your first entry.")
    else:
        st.markdown("### Filters")
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            min_mood = st.slider("Min Mood", 1, 10, 1, key="h_mood")
        with fc2:
            max_stress = st.slider("Max Stress", 1, 10, 10, key="h_stress")
        with fc3:
            flagged_only = st.checkbox("Flagged only", key="h_flag")
        with fc4:
            search = st.text_input("Search notes", placeholder="keyword...", key="h_search")

        filtered = [
            e for e in all_e
            if e.mood_score >= min_mood
            and e.stress_score <= max_stress
            and (not flagged_only or e.ai_flagged)
            and (not search or search.lower() in (e.journal_notes or "").lower())
        ]

        st.divider()
        st.markdown(f"Showing **{len(filtered)}** of **{len(all_e)}** entries")
        st.divider()

        for entry in filtered:
            flag_icon         = "🚩" if entry.ai_flagged else "✅"
            date_str          = entry.entry_date.strftime("%A, %B %d %Y") if entry.entry_date else "Unknown"
            m_name, m_emoji, _ = MOOD_LABELS.get(entry.mood_score, ("?", "?", "#999"))
            header = (
                f"{flag_icon} **{date_str}** — "
                f"{m_emoji} Mood {entry.mood_score}/10  ·  "
                f"Stress {entry.stress_score}/10"
            )
            with st.expander(header, expanded=False):
                hc1, hc2, hc3, hc4 = st.columns(4)
                hc1.metric("Mood",   f"{entry.mood_score}/10")
                hc2.metric("Stress", f"{entry.stress_score}/10")
                hc3.metric("Energy", f"{entry.energy_level}/10" if entry.energy_level else "N/A")
                hc4.metric("Sleep",  f"{entry.sleep_hours}h" if entry.sleep_hours else "N/A")

                if entry.activities:
                    acts = [a.strip() for a in entry.activities.split(",") if a.strip()]
                    if acts:
                        st.markdown("**Activities:** " + "  ".join(f"`{a}`" for a in acts))

                if entry.journal_notes:
                    with st.container(border=True):
                        st.markdown("**Journal Notes**")
                        st.write(entry.journal_notes)

                if entry.gratitude_notes:
                    with st.container(border=True):
                        st.markdown("**Gratitude**")
                        st.write(entry.gratitude_notes)

                if entry.ai_insight:
                    with st.container(border=True):
                        st.markdown("**AI Insight**")
                        st.info(entry.ai_insight)
                        if entry.ai_suggestion:
                            st.caption(f"Suggestion: {entry.ai_suggestion}")

                if entry.ai_flagged and entry.ai_flag_reason:
                    st.error(f"Flagged: {entry.ai_flag_reason}")
