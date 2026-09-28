"""
config.py — MindLog v2.0 application constants, labels, and settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-2.5-flash"

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH: str = "wellness_journal.db"
DB_URL: str = f"sqlite:///{DB_PATH}"

# ── Scale bounds ──────────────────────────────────────────────────────────────
MOOD_MIN, MOOD_MAX = 1, 10
STRESS_MIN, STRESS_MAX = 1, 10

# ── Mood labels: (name, emoji, hex_color) ─────────────────────────────────────
MOOD_LABELS: dict[int, tuple] = {
    1:  ("Terrible",      "😭", "#E53935"),
    2:  ("Very Bad",      "😢", "#EF5350"),
    3:  ("Bad",           "😟", "#F4511E"),
    4:  ("Below Average", "😕", "#FB8C00"),
    5:  ("Neutral",       "😐", "#FDD835"),
    6:  ("Okay",          "🙂", "#C0CA33"),
    7:  ("Good",          "😊", "#7CB342"),
    8:  ("Great",         "😁", "#43A047"),
    9:  ("Excellent",     "🤩", "#00897B"),
    10: ("Amazing",       "🥳", "#1E88E5"),
}

# ── Stress labels: (name, emoji, hex_color) ───────────────────────────────────
STRESS_LABELS: dict[int, tuple] = {
    1:  ("Completely Calm",    "🧘", "#1E88E5"),
    2:  ("Very Relaxed",       "😌", "#00897B"),
    3:  ("Relaxed",            "😊", "#43A047"),
    4:  ("Mild Stress",        "🙂", "#7CB342"),
    5:  ("Moderate",           "😐", "#FDD835"),
    6:  ("Noticeable Stress",  "😕", "#FB8C00"),
    7:  ("Stressed",           "😟", "#F4511E"),
    8:  ("Very Stressed",      "😰", "#EF5350"),
    9:  ("Extremely Stressed", "😱", "#E53935"),
    10: ("Overwhelmed",        "🤯", "#B71C1C"),
}

# ── Energy labels ─────────────────────────────────────────────────────────────
ENERGY_LABELS: dict[int, str] = {
    1:  "Completely Drained",
    2:  "Very Low",
    3:  "Low Energy",
    4:  "Sluggish",
    5:  "Moderate",
    6:  "Getting There",
    7:  "Energised",
    8:  "High Energy",
    9:  "Very High",
    10: "Fully Charged",
}

# ── Activities ────────────────────────────────────────────────────────────────
POSITIVE_ACTIVITIES: list[str] = [
    "Exercise / Gym", "Morning Walk", "Meditation", "Yoga",
    "Reading", "Journaling", "Creative Activity", "Cooking Healthy",
    "Social Time", "Time in Nature", "Therapy Session",
    "Healthy Eating", "Music / Podcast", "Acts of Kindness",
]
NEGATIVE_ACTIVITIES: list[str] = [
    "Poor Sleep", "Skipped Meals", "Alcohol / Substances",
    "Excessive Screen Time", "Social Isolation", "Overworking",
    "Late Night", "Conflict / Argument", "Skipped Exercise", "Junk Food",
]
ALL_ACTIVITIES: list[str] = POSITIVE_ACTIVITIES + NEGATIVE_ACTIVITIES

# ── Analytics thresholds ──────────────────────────────────────────────────────
LOW_MOOD_THRESHOLD:       int = 4
HIGH_STRESS_THRESHOLD:    int = 7
CONSECUTIVE_CONCERN_DAYS: int = 3
ROLLING_WINDOW_DAYS:      int = 7

# ── Chart colours ─────────────────────────────────────────────────────────────
C_MOOD        = "#6C63FF"
C_STRESS      = "#FF4F81"
C_ENERGY      = "#FF9800"
C_SLEEP       = "#00C9A7"
C_MOOD_ROLL   = "#B3B0FF"
C_STRESS_ROLL = "#FFB3CC"
C_ACCENT      = "#f20c8e"
C_BG          = "#e5f9fe"
C_CARD        = "#FFFFFF"

# ── Pages ─────────────────────────────────────────────────────────────────────
PAGES: dict[str, str] = {
    "Daily Journal":       "📝",
    "Analytics Dashboard": "📊",
    "AI Insights":         "🤖",
    "Therapist Report":    "📋",
    "My History":          "📅",
}

# ── App metadata ──────────────────────────────────────────────────────────────
APP_TITLE   = "MindLog"
APP_TAGLINE = "Your private AI-powered mental wellness companion"
APP_ICON    = "🧠"
APP_VERSION = "2.0"
