"""
analytics.py — MindLog v2.0 trend computation, pattern detection, rich Plotly charts.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import (
    C_MOOD, C_STRESS, C_ENERGY, C_SLEEP,
    C_MOOD_ROLL, C_STRESS_ROLL, C_ACCENT, C_BG,
    CONSECUTIVE_CONCERN_DAYS, HIGH_STRESS_THRESHOLD,
    LOW_MOOD_THRESHOLD, ROLLING_WINDOW_DAYS,
    POSITIVE_ACTIVITIES, NEGATIVE_ACTIVITIES,
)
from database import JournalEntry

_PAPER = C_BG
_PLOT  = "#FFFFFF"


# ── Data helpers ───────────────────────────────────────────────────────────────

def entries_to_df(entries: list[JournalEntry]) -> pd.DataFrame:
    if not entries:
        return pd.DataFrame()
    rows = [
        {
            "date":         pd.Timestamp(e.entry_date).normalize(),
            "mood":         e.mood_score,
            "stress":       e.stress_score,
            "energy":       e.energy_level,
            "sleep":        e.sleep_hours,
            "activities":   e.activities or "",
            "journal_notes":e.journal_notes or "",
            "ai_flagged":   bool(e.ai_flagged),
            "ai_flag_reason": e.ai_flag_reason or "",
        }
        for e in entries
    ]
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df["mood_rolling"]   = df["mood"].rolling(ROLLING_WINDOW_DAYS, min_periods=1).mean()
    df["stress_rolling"] = df["stress"].rolling(ROLLING_WINDOW_DAYS, min_periods=1).mean()
    return df


# ── Pattern detection ──────────────────────────────────────────────────────────

@dataclass
class ConcernPattern:
    pattern_type: str
    description:  str
    severity:     str   # "low" | "medium" | "high"
    icon:         str = "⚠️"
    affected_dates: list[str] = field(default_factory=list)


def detect_patterns(df: pd.DataFrame) -> list[ConcernPattern]:
    if df.empty:
        return []
    patterns: list[ConcernPattern] = []

    # 1 ─ Consecutive low mood
    streak, dates = 0, []
    for _, row in df.iterrows():
        if row["mood"] <= LOW_MOOD_THRESHOLD:
            streak += 1; dates.append(str(row["date"].date()))
        else:
            streak, dates = 0, []
        if streak >= CONSECUTIVE_CONCERN_DAYS:
            patterns.append(ConcernPattern(
                "Persistent Low Mood",
                f"Mood at or below {LOW_MOOD_THRESHOLD}/10 for {streak} consecutive days.",
                "high" if streak >= 5 else "medium", "😔", dates.copy(),
            ))

    # 2 ─ Consecutive high stress
    streak, dates = 0, []
    for _, row in df.iterrows():
        if row["stress"] >= HIGH_STRESS_THRESHOLD:
            streak += 1; dates.append(str(row["date"].date()))
        else:
            streak, dates = 0, []
        if streak >= CONSECUTIVE_CONCERN_DAYS:
            patterns.append(ConcernPattern(
                "Elevated Stress",
                f"Stress at or above {HIGH_STRESS_THRESHOLD}/10 for {streak} consecutive days.",
                "high" if streak >= 5 else "medium", "😰", dates.copy(),
            ))

    # 3 ─ Rapid mood decline
    if len(df) >= 5:
        rec   = df.tail(5)
        slope = np.polyfit(range(5), rec["mood"].values, 1)[0]
        if slope <= -1.0:
            patterns.append(ConcernPattern(
                "Rapid Mood Decline",
                f"Mood declining sharply over last 5 entries (slope: {slope:.2f}/day).",
                "high", "📉", [str(d.date()) for d in rec["date"]],
            ))

    # 4 ─ Chronic poor sleep
    sleep_col = df["sleep"].dropna()
    if len(sleep_col) >= 5:
        low_sleep = df[df["sleep"] < 5]
        if len(low_sleep) / len(df) >= 0.4:
            patterns.append(ConcernPattern(
                "Chronic Poor Sleep",
                f"{len(low_sleep)}/{len(df)} entries report less than 5 hours of sleep.",
                "medium", "😴", [str(d.date()) for d in low_sleep["date"]],
            ))

    # 5 ─ Burnout combo
    combo = df[(df["energy"].notna()) & (df["energy"] <= 3) & (df["mood"] <= 4)]
    if len(combo) >= 3:
        patterns.append(ConcernPattern(
            "Burnout Indicators",
            f"{len(combo)} entries show both very low energy (<=3) and low mood (<=4).",
            "high", "🔋", [str(d.date()) for d in combo["date"]],
        ))

    # 6 ─ Social withdrawal
    if df["activities"].notna().any() and len(df) >= 7:
        iso = df["activities"].apply(
            lambda a: "Social Isolation" in a or "Social Time" not in a
        ).sum()
        if iso / len(df) >= 0.6:
            patterns.append(ConcernPattern(
                "Social Withdrawal",
                f"Social activity absent or isolation noted in {iso}/{len(df)} entries.",
                "medium", "🔇", [],
            ))

    # Deduplicate
    srank = {"low": 0, "medium": 1, "high": 2}
    seen: dict[str, ConcernPattern] = {}
    for p in patterns:
        if p.pattern_type not in seen or srank[p.severity] > srank[seen[p.pattern_type].severity]:
            seen[p.pattern_type] = p
    return list(seen.values())


# ── Summary stats ──────────────────────────────────────────────────────────────

def compute_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return {
        "total_entries":  len(df),
        "avg_mood":       round(df["mood"].mean(), 1),
        "avg_stress":     round(df["stress"].mean(), 1),
        "avg_energy":     round(df["energy"].dropna().mean(), 1) if df["energy"].notna().any() else None,
        "avg_sleep":      round(df["sleep"].dropna().mean(), 1) if df["sleep"].notna().any() else None,
        "best_mood":      int(df["mood"].max()),
        "worst_mood":     int(df["mood"].min()),
        "best_mood_date": str(df.loc[df["mood"].idxmax(), "date"].date()),
        "flagged_days":   int(df["ai_flagged"].sum()),
        "date_range":     (str(df["date"].min().date()), str(df["date"].max().date())),
        "mood_trend":     round(df["mood"].diff().mean(), 2) if len(df) > 1 else 0.0,
        "stress_trend":   round(df["stress"].diff().mean(), 2) if len(df) > 1 else 0.0,
    }


# ── Charts ─────────────────────────────────────────────────────────────────────

def chart_mood_stress(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Mood Over Time", "Stress Over Time"),
        vertical_spacing=0.12,
    )
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["mood"], mode="lines+markers", name="Daily Mood",
        line=dict(color=C_MOOD, width=2.5), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(108,99,255,0.08)",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["mood_rolling"], mode="lines",
        name=f"{ROLLING_WINDOW_DAYS}-day Avg",
        line=dict(color=C_MOOD_ROLL, width=2, dash="dot"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["stress"], mode="lines+markers", name="Daily Stress",
        line=dict(color=C_STRESS, width=2.5), marker=dict(size=7),
        fill="tozeroy", fillcolor="rgba(255,79,129,0.08)",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["stress_rolling"], mode="lines",
        name=f"{ROLLING_WINDOW_DAYS}-day Avg",
        line=dict(color=C_STRESS_ROLL, width=2, dash="dot"),
    ), row=2, col=1)
    fig.add_hrect(y0=1, y1=LOW_MOOD_THRESHOLD, row=1, col=1,
                  fillcolor="red", opacity=0.04,
                  annotation_text="Low Mood Zone", annotation_position="top left")
    fig.add_hrect(y0=HIGH_STRESS_THRESHOLD, y1=10, row=2, col=1,
                  fillcolor="orange", opacity=0.04,
                  annotation_text="High Stress Zone", annotation_position="top right")
    fig.update_yaxes(range=[0, 11])
    fig.update_layout(
        height=480, hovermode="x unified",
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
        plot_bgcolor=_PLOT, paper_bgcolor=_PAPER,
        margin=dict(t=60, b=20, l=40, r=20),
    )
    return fig


def chart_sleep_energy(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=df["date"], y=df["sleep"],
        name="Sleep (hrs)", marker_color=C_SLEEP, opacity=0.8,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["energy"],
        mode="lines+markers", name="Energy",
        line=dict(color=C_ENERGY, width=2.5), marker=dict(size=7),
    ), secondary_y=True)
    fig.add_hrect(y0=0, y1=5, fillcolor="red", opacity=0.04,
                  annotation_text="Poor Sleep Zone", annotation_position="top left")
    fig.update_layout(
        title="Sleep & Energy",
        hovermode="x unified", height=320,
        plot_bgcolor=_PLOT, paper_bgcolor=_PAPER,
        margin=dict(t=50, b=20, l=40, r=60),
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
    )
    fig.update_yaxes(title_text="Sleep (hrs)", range=[0, 14], secondary_y=False)
    fig.update_yaxes(title_text="Energy (1-10)", range=[0, 11], secondary_y=True)
    return fig


def chart_radar(summary: dict) -> go.Figure:
    labels = ["Mood", "Energy", "Sleep Quality", "Calmness", "Consistency"]
    values = [
        summary.get("avg_mood") or 5,
        summary.get("avg_energy") or 5,
        min((summary.get("avg_sleep") or 7) / 1.2, 10),
        10 - (summary.get("avg_stress") or 5),
        min((summary.get("total_entries") or 1) / 3, 10),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]], theta=labels + [labels[0]],
        fill="toself",
        fillcolor=f"rgba(242,12,142,0.12)",
        line=dict(color=C_ACCENT, width=2.5),
        marker=dict(size=8, color=C_ACCENT),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        title="Wellness Radar",
        height=320, showlegend=False,
        paper_bgcolor=_PAPER,
        margin=dict(t=60, b=20, l=40, r=40),
    )
    return fig


def chart_mood_dist(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df, x="mood", nbins=10, range_x=[0.5, 10.5],
        color_discrete_sequence=[C_MOOD],
        title="Mood Distribution",
        labels={"mood": "Mood Score (1-10)"},
    )
    fig.update_layout(
        bargap=0.12, height=300,
        plot_bgcolor=_PLOT, paper_bgcolor=_PAPER,
        margin=dict(t=50, b=20, l=40, r=20),
    )
    return fig


def chart_activity_impact(df: pd.DataFrame) -> Optional[go.Figure]:
    rows = []
    for _, row in df.iterrows():
        for act in (row["activities"] or "").split(","):
            act = act.strip()
            if act:
                rows.append({
                    "activity": act, "mood": row["mood"],
                    "type": "Positive" if act in POSITIVE_ACTIVITIES else "Negative",
                })
    if len(rows) < 5:
        return None
    adf = pd.DataFrame(rows)
    counts = adf["activity"].value_counts()
    adf = adf[adf["activity"].isin(counts[counts >= 2].index)]
    if adf.empty:
        return None
    fig = px.box(
        adf, x="activity", y="mood", color="type",
        color_discrete_map={"Positive": C_MOOD, "Negative": C_STRESS},
        title="Mood by Activity",
        labels={"mood": "Mood Score", "activity": "", "type": "Type"},
    )
    fig.update_layout(
        height=360, plot_bgcolor=_PLOT, paper_bgcolor=_PAPER,
        xaxis=dict(tickangle=-30),
        margin=dict(t=50, b=80, l=40, r=20),
        legend=dict(orientation="h", y=-0.35),
    )
    return fig


def chart_correlation(df: pd.DataFrame) -> Optional[go.Figure]:
    cols = [c for c in ["mood", "stress", "energy", "sleep"] if c in df.columns]
    sub  = df[cols].dropna()
    if len(sub) < 4:
        return None
    corr = sub.corr().round(2)
    lbls = [c.capitalize() for c in corr.columns]
    fig  = go.Figure(go.Heatmap(
        z=corr.values, x=lbls, y=lbls,
        colorscale="RdBu", zmid=0,
        text=corr.values, texttemplate="%{text}",
        colorbar=dict(title="r", thickness=12),
    ))
    fig.update_layout(
        title="Metric Correlations", height=300,
        plot_bgcolor=_PLOT, paper_bgcolor=_PAPER,
        margin=dict(t=50, b=20, l=60, r=20),
    )
    return fig


def chart_weekday(df: pd.DataFrame) -> Optional[go.Figure]:
    if len(df) < 7:
        return None
    df2 = df.copy()
    df2["weekday"] = df2["date"].dt.day_name()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = df2.pivot_table(index="weekday", values="mood", aggfunc="mean")
    pivot = pivot.reindex([d for d in order if d in pivot.index])
    fig = go.Figure(go.Bar(
        x=pivot.index.tolist(), y=pivot["mood"].round(1).tolist(),
        marker=dict(
            color=pivot["mood"].tolist(),
            colorscale="RdYlGn", cmin=1, cmax=10,
            showscale=True, colorbar=dict(title="Mood", thickness=12),
        ),
        text=pivot["mood"].round(1).tolist(), textposition="outside",
    ))
    fig.update_layout(
        title="Avg Mood by Day of Week",
        yaxis=dict(range=[0, 11]),
        height=300, plot_bgcolor=_PLOT, paper_bgcolor=_PAPER,
        margin=dict(t=50, b=30, l=40, r=20),
    )
    return fig


# ── Dashboard ──────────────────────────────────────────────────────────────────

def render_analytics_dashboard(entries: list[JournalEntry]) -> None:
    st.markdown("## 📊 Analytics Dashboard")
    st.markdown("Visualise your wellness trends, spot patterns, and track progress over time.")

    if not entries:
        st.info("No entries yet. Head to **Daily Journal** to log your first entry.")
        return

    df_all   = entries_to_df(entries)
    summary  = compute_summary(df_all)
    patterns = detect_patterns(df_all)

    # Period selector
    opts = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "All time": len(df_all)}
    sel  = st.selectbox("View period", list(opts.keys()), index=2, key="dash_period")
    df   = df_all.tail(opts[sel]) if opts[sel] < len(df_all) else df_all
    st.divider()

    # ── KPI row ────────────────────────────────────────────────────────────────
    st.markdown("### Key Metrics")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    mt  = summary.get("mood_trend", 0) or 0
    st2 = summary.get("stress_trend", 0) or 0
    k1.metric("Entries",    summary.get("total_entries", 0))
    k2.metric("Avg Mood",   f"{summary.get('avg_mood','—')}/10",
              delta=f"{mt:+.2f}/day" if mt else None)
    k3.metric("Avg Stress", f"{summary.get('avg_stress','—')}/10",
              delta=f"{st2:+.2f}/day" if st2 else None, delta_color="inverse")
    k4.metric("Avg Energy", f"{summary.get('avg_energy','—')}/10" if summary.get("avg_energy") else "—")
    k5.metric("Avg Sleep",  f"{summary.get('avg_sleep','—')}h" if summary.get("avg_sleep") else "—")
    k6.metric("Flagged",    summary.get("flagged_days", 0))
    st.divider()

    # ── Patterns ───────────────────────────────────────────────────────────────
    if patterns:
        st.markdown("### Concerning Patterns")
        for p in patterns:
            msg = f"{p.icon} **{p.pattern_type}** [{p.severity.upper()}] — {p.description}"
            if p.severity == "high":
                st.error(msg)
            elif p.severity == "medium":
                st.warning(msg)
            else:
                st.info(msg)
            if p.affected_dates:
                st.caption("Dates: " + ", ".join(p.affected_dates[-5:]))
        st.divider()
    else:
        st.success("No concerning patterns detected in this period.")
        st.divider()

    if df.empty:
        st.warning("No data for selected period.")
        return

    # ── Charts ─────────────────────────────────────────────────────────────────
    st.markdown("### Mood & Stress Trends")
    st.plotly_chart(chart_mood_stress(df), use_container_width=True)

    st.markdown("### Sleep, Energy & Wellness Radar")
    r1, r2 = st.columns([3, 2])
    with r1:
        st.plotly_chart(chart_sleep_energy(df), use_container_width=True)
    with r2:
        st.plotly_chart(chart_radar(summary), use_container_width=True)

    st.markdown("### Distribution & Correlations")
    r2a, r2b = st.columns(2)
    with r2a:
        st.plotly_chart(chart_mood_dist(df), use_container_width=True)
    with r2b:
        fig_c = chart_correlation(df)
        if fig_c:
            st.plotly_chart(fig_c, use_container_width=True)
        else:
            st.info("Need at least 4 entries for correlation analysis.")

    r3a, r3b = st.columns(2)
    with r3a:
        fig_w = chart_weekday(df)
        if fig_w:
            st.plotly_chart(fig_w, use_container_width=True)
    with r3b:
        fig_a = chart_activity_impact(df)
        if fig_a:
            st.plotly_chart(fig_a, use_container_width=True)
