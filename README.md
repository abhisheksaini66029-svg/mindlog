# 🧠 MindLog — AI-Powered Mental Wellness Journal

A privacy-first, AI-powered mental wellness journaling app built with **Streamlit** and **Google Gemini 2.5 Flash**. Log your daily mood, stress, sleep, and notes — then let AI surface trends, flag concerns, and generate therapist-ready reports.

---

## ✨ Features

| Module | What it does |
|---|---|
| 📝 **Daily Journal** | Log mood (1–10), stress (1–10), energy, sleep hours, activities, free-text notes & gratitude |
| 📊 **Analytics Dashboard** | Interactive Plotly charts: mood/stress trends, rolling averages, sleep analysis, activity impact, correlation heatmap |
| ⚠️ **Pattern Detection** | Rule-based engine flags persistent low mood, elevated stress, rapid mood decline, chronic poor sleep, and burnout combos |
| 🤖 **AI Insights** | Gemini 2.5 Flash analyses each entry and your overall trends — personalised insights, coping suggestions |
| 💬 **MindBot Chat** | Conversational AI companion grounded in your journal context |
| 📋 **Therapist Report** | Clinical-grade AI report with risk assessment, patterns, and recommendations — downloadable as `.txt` |
| 📅 **History** | Searchable and filterable log of all past entries with AI annotations |

---

## 🚀 Quick Start

### 1. Clone / download the project

```bash
cd mental_wellness_app
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your Gemini API key

**Option A — `.env` file (recommended)**

```bash
cp .env.example .env
# Edit .env and add your key:
# GEMINI_API_KEY=your_key_here
```

**Option B — In the app sidebar**  
Enter your key directly in the **🔑 Gemini API Key** field in the sidebar — no restart needed.

Get a free key at [https://aistudio.google.com/](https://aistudio.google.com/)

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🗂️ Project Structure

```
mental_wellness_app/
├── app.py              # Main Streamlit entry point & page routing
├── config.py           # Constants, thresholds, scale labels
├── database.py         # SQLAlchemy models (SQLite) + CRUD helpers
├── journal.py          # Journal entry form UI
├── analytics.py        # Trend computation, pattern detection, Plotly charts
├── ai_engine.py        # Gemini 2.5 Flash integration (entry, trend, therapist, chat)
├── requirements.txt    # Python dependencies
├── .env.example        # API key template
└── .streamlit/
    └── config.toml     # Streamlit theme & server config
```

---

## 🤖 AI Capabilities (Gemini 2.5 Flash)

- **Entry Analysis** — Sentiment-aware insight, concern flagging, and a personalised coping suggestion per entry
- **Trend Insights** — Multi-entry pattern analysis with motivational feedback
- **Therapist Report** — Clinical summary, risk assessment (Low/Moderate/High), pattern list, and therapeutic recommendations
- **MindBot Chat** — Conversational support grounded in your journal history

---

## ⚠️ Concerning Pattern Rules

| Pattern | Trigger |
|---|---|
| Persistent Low Mood | Mood ≤ 4 for ≥ 3 consecutive days |
| Elevated Stress | Stress ≥ 7 for ≥ 3 consecutive days |
| Rapid Mood Decline | Slope ≤ −1.0 pts/day over last 5 entries |
| Chronic Poor Sleep | < 5h sleep in ≥ 40% of entries |
| Low Energy & Mood Combo | Energy ≤ 3 AND Mood ≤ 4 in ≥ 3 entries |

---

## 🔒 Privacy

- All data is stored **locally** in a SQLite database (`wellness_journal.db`)
- No data is sent to external servers except your journal text to the Gemini API for AI analysis
- You can use an alias as your username — no account or email required

---

## ☁️ Deploying to Streamlit Cloud

1. Push the `mental_wellness_app/` folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set the main file path to `app.py`
4. Add `GEMINI_API_KEY` as a secret in the Streamlit Cloud dashboard
5. Deploy 🚀

---

## 📄 Disclaimer

MindLog is a **wellness tracking tool**, not a medical device or clinical service. AI-generated content is for informational purposes only. Always consult a licensed mental health professional for clinical advice.
