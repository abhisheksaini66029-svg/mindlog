"""
ai_engine.py — Gemini 2.5 Flash integration for AI-powered wellness insights.
Uses the modern google-genai SDK.
"""

from __future__ import annotations

import textwrap
from typing import Optional

import streamlit as st
from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL
from database import JournalEntry, update_ai_fields, save_therapist_note
from analytics import entries_to_df, detect_patterns, compute_summary

import datetime
import pandas as pd


# ── Gemini client ─────────────────────────────────────────────────────────────

def _get_client() -> Optional[genai.Client]:
    """Return a configured Gemini client, or None if the key is missing."""
    api_key = GEMINI_API_KEY or st.session_state.get("gemini_api_key", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _generate(prompt: str) -> str:
    """Call Gemini and return the text response. Raises on error."""
    client = _get_client()
    if client is None:
        return "__NO_KEY__"
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()


# ── Prompt builders ───────────────────────────────────────────────────────────

def _build_entry_prompt(entry: JournalEntry) -> str:
    return textwrap.dedent(f"""
        You are a compassionate mental wellness AI assistant.
        Analyse the following journal entry and provide a structured response.

        --- Journal Entry ---
        Date        : {entry.entry_date.date() if entry.entry_date else 'Unknown'}
        Mood        : {entry.mood_score}/10
        Stress      : {entry.stress_score}/10
        Energy      : {entry.energy_level or 'N/A'}/10
        Sleep       : {entry.sleep_hours or 'N/A'} hours
        Activities  : {entry.activities or 'None recorded'}
        Notes       : {entry.journal_notes or '(none)'}
        Gratitude   : {entry.gratitude_notes or '(none)'}
        ---

        Respond in this exact format:
        INSIGHT: <3-5 warm empathetic sentences about this specific entry>
        FLAG: FLAGGED or NOT_FLAGGED
        FLAG_REASON: <1-2 clinical sentences if FLAGGED, else None>
        SUGGESTION: <one specific, actionable coping suggestion for today>
    """).strip()


def _build_trend_prompt(df: pd.DataFrame, summary: dict, patterns: list) -> str:
    recent = df.tail(7)
    trend_rows = "\n".join(
        f"  {row['date'].date()} | Mood {row['mood']} | Stress {row['stress']} "
        f"| Energy {row['energy'] or 'N/A'} | Sleep {row['sleep'] or 'N/A'}h"
        for _, row in recent.iterrows()
    )
    pattern_text = (
        "\n".join(f"  - [{p.severity.upper()}] {p.pattern_type}: {p.description}" for p in patterns)
        if patterns else "  None detected."
    )
    return textwrap.dedent(f"""
        You are a compassionate mental wellness AI assistant reviewing a user's recent journal data.
        Provide:
        1. **Trend Summary** - 3-4 sentences about the overall wellness trajectory.
        2. **Key Observations** - 2-3 bullet points about notable patterns or positive developments.
        3. **Encouragement** - one warm, motivating message personalised to this data.
        4. **Coping Strategies** - 2-3 specific, actionable strategies matching the detected patterns.

        --- Recent Data (last 7 entries) ---
{trend_rows}

        --- Summary Stats ---
        Total entries : {summary.get('total_entries')}
        Avg mood      : {summary.get('avg_mood')}/10
        Avg stress    : {summary.get('avg_stress')}/10
        Avg sleep     : {summary.get('avg_sleep')} hrs
        Flagged days  : {summary.get('flagged_days')}

        --- Detected Patterns ---
{pattern_text}
        ---

        Use markdown formatting in your response (bold, bullet lists).
        Be warm, non-clinical, and empowering.
    """).strip()


def _build_therapist_prompt(df: pd.DataFrame, summary: dict, patterns: list, username: str) -> str:
    all_rows = "\n".join(
        f"  {row['date'].date()} | Mood {row['mood']} | Stress {row['stress']} "
        f"| Sleep {row['sleep'] or 'N/A'}h | Flagged: {row['ai_flagged']}"
        for _, row in df.iterrows()
    )
    pattern_text = (
        "\n".join(f"  - [{p.severity.upper()}] {p.pattern_type}: {p.description}" for p in patterns)
        if patterns else "  None detected."
    )
    period_start = str(df["date"].min().date())
    period_end = str(df["date"].max().date())

    return textwrap.dedent(f"""
        You are a clinical mental health AI assistant preparing a structured wellness report
        for a licensed therapist. Write in professional clinical language.

        Patient alias : {username}
        Report period : {period_start} to {period_end}

        Provide the following sections:

        ## Clinical Summary
        (3-5 sentences summarising the patient's mental wellness during the period)

        ## Data Overview
        (Key statistics in a structured format)

        ## Identified Concerning Patterns
        (List each flagged pattern with clinical context and frequency)

        ## Risk Assessment
        (Low / Moderate / High - with brief justification)

        ## Recommendations for Therapist Review
        (3-5 specific therapeutic recommendations or areas to explore)

        ## Positive Indicators
        (Any positive trends, resilience factors, or protective behaviours observed)

        --- Full Data ---
{all_rows}

        --- Detected Patterns ---
{pattern_text}

        --- Summary ---
        Avg mood   : {summary.get('avg_mood')}/10
        Avg stress : {summary.get('avg_stress')}/10
        Flagged    : {summary.get('flagged_days')} of {summary.get('total_entries')} days
        ---

        Use professional clinical language. Use markdown headers and bullet points.
    """).strip()


def _build_chat_prompt(user_message: str, summary: dict) -> str:
    context_block = ""
    if summary:
        context_block = textwrap.dedent(f"""
            Context (user's recent journal summary):
            - Avg mood: {summary.get('avg_mood')}/10
            - Avg stress: {summary.get('avg_stress')}/10
            - Avg sleep: {summary.get('avg_sleep')} hrs
            - Total entries: {summary.get('total_entries')}
            - Flagged days: {summary.get('flagged_days')}
        """)

    return textwrap.dedent(f"""
        You are MindBot, a warm and empathetic AI wellness companion.
        You support users in understanding their mental wellness journal data.
        You are NOT a licensed therapist, but you are knowledgeable about mental wellness,
        coping strategies, and healthy habits. Always encourage professional help when needed.
        {context_block}
        User message: {user_message}

        Respond helpfully, empathetically, and concisely (2-4 paragraphs max).
        Use markdown formatting where helpful.
    """).strip()


# ── Public API ────────────────────────────────────────────────────────────────

def analyse_entry(entry: JournalEntry) -> dict:
    """
    Call Gemini to analyse a single journal entry.
    Returns dict with keys: insight, flagged, flag_reason, suggestion.
    Persists results to DB.
    """
    prompt = _build_entry_prompt(entry)
    try:
        text = _generate(prompt)
    except Exception as exc:
        return {"insight": f"AI analysis failed: {exc}", "flagged": False,
                "flag_reason": "", "suggestion": ""}

    if text == "__NO_KEY__":
        return {"insight": "Add your Gemini API key in the sidebar to enable AI analysis.",
                "flagged": False, "flag_reason": "", "suggestion": ""}

    insight = flag_reason = suggestion = ""
    flagged = False
    for line in text.splitlines():
        if line.startswith("INSIGHT:"):
            insight = line[8:].strip()
        elif line.startswith("FLAG:"):
            flagged = "FLAGGED" in line and "NOT_FLAGGED" not in line
        elif line.startswith("FLAG_REASON:"):
            flag_reason = line[12:].strip()
            if flag_reason.lower() == "none":
                flag_reason = ""
        elif line.startswith("SUGGESTION:"):
            suggestion = line[11:].strip()

    if not insight:
        insight = text

    update_ai_fields(entry.id, insight, flagged, flag_reason, suggestion)
    return {"insight": insight, "flagged": flagged,
            "flag_reason": flag_reason, "suggestion": suggestion}


def get_trend_insights(entries: list[JournalEntry]) -> str:
    """Call Gemini to analyse multi-entry trends. Returns a markdown string."""
    if not entries:
        return "No journal entries found. Start logging to receive AI insights."
    df = entries_to_df(entries)
    summary = compute_summary(df)
    patterns = detect_patterns(df)
    try:
        text = _generate(_build_trend_prompt(df, summary, patterns))
        return "Add your Gemini API key in the sidebar." if text == "__NO_KEY__" else text
    except Exception as exc:
        return f"AI analysis failed: {exc}"


def generate_therapist_report(
    entries: list[JournalEntry], username: str
) -> tuple[str, str, str]:
    """Generate a full clinical therapist report. Returns (report, concerning, recommendations)."""
    if not entries:
        return ("No data available for report generation.", "", "")
    df = entries_to_df(entries)
    summary = compute_summary(df)
    patterns = detect_patterns(df)
    try:
        report_text = _generate(_build_therapist_prompt(df, summary, patterns, username))
        if report_text == "__NO_KEY__":
            return ("Add your Gemini API key in the sidebar.", "", "")
    except Exception as exc:
        return (f"Report generation failed: {exc}", "", "")

    concerning, recommendations = [], []
    in_c = in_r = False
    for line in report_text.splitlines():
        if "## Identified Concerning" in line:
            in_c, in_r = True, False
        elif "## Recommendations" in line:
            in_c, in_r = False, True
        elif line.startswith("## "):
            in_c = in_r = False
        elif in_c:
            concerning.append(line)
        elif in_r:
            recommendations.append(line)

    if df["date"].notna().any():
        save_therapist_note(
            username=username,
            period_start=df["date"].min().to_pydatetime(),
            period_end=df["date"].max().to_pydatetime(),
            report_text=report_text,
            concerning_patterns="\n".join(concerning).strip(),
            recommendations="\n".join(recommendations).strip(),
        )
    return report_text, "\n".join(concerning).strip(), "\n".join(recommendations).strip()


def chat_with_ai(user_message: str, context_entries: list[JournalEntry]) -> str:
    """Free-form AI chat grounded in the user's journal context."""
    df = entries_to_df(context_entries) if context_entries else pd.DataFrame()
    summary = compute_summary(df) if not df.empty else {}
    try:
        text = _generate(_build_chat_prompt(user_message, summary))
        return "Add your Gemini API key in the sidebar." if text == "__NO_KEY__" else text
    except Exception as exc:
        return f"Error communicating with AI: {exc}"
