"""
Gujarat OSINT Intelligence Dashboard
=====================================
Open-source intelligence aggregator for all 33 districts of Gujarat.
Tracks citizen grievances, government feedback, and weekly trends
from publicly available data sources.

Sources simulated:
  • Twitter/X social mentions
  • Online news (Divya Bhaskar, Sandesh, TOI Gujarat, Navbharat Times)
  • PG Portal (public grievance portal - pgportal.gov.in)
  • MyGov Portal citizen feedback
  • RTI application filings
  • Reddit (r/india, r/gujarat)
  • Local forums & WhatsApp public aggregators
"""

import dash
from dash import dcc, html, dash_table, Input, Output, callback_context
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

GUJARAT_DISTRICTS = [
    "Ahmedabad", "Amreli", "Anand", "Aravalli", "Banaskantha",
    "Bharuch", "Bhavnagar", "Botad", "Chhota Udaipur", "Dahod",
    "Dang", "Devbhumi Dwarka", "Gandhinagar", "Gir Somnath", "Jamnagar",
    "Junagadh", "Kheda", "Kutch", "Mahisagar", "Mehsana",
    "Morbi", "Narmada", "Navsari", "Panchmahal", "Patan",
    "Porbandar", "Rajkot", "Sabarkantha", "Surat", "Surendranagar",
    "Tapi", "Vadodara", "Valsad"
]

GRIEVANCE_CATEGORIES = {
    "Water Supply":        {"icon": "💧", "color": "#2196F3", "base": 85},
    "Roads & Infrastructure": {"icon": "🏗️", "color": "#FF9800", "base": 92},
    "Electricity":         {"icon": "⚡", "color": "#FFEB3B", "base": 78},
    "Healthcare":          {"icon": "🏥", "color": "#E91E63", "base": 65},
    "Sanitation & Waste":  {"icon": "🗑️", "color": "#9C27B0", "base": 70},
    "Education":           {"icon": "📚", "color": "#00BCD4", "base": 55},
    "Law & Order":         {"icon": "⚖️", "color": "#F44336", "base": 60},
    "Agriculture":         {"icon": "🌾", "color": "#4CAF50", "base": 75},
    "Land & Revenue":      {"icon": "📋", "color": "#795548", "color2": "#A1887F", "base": 50},
    "Corruption/Bribery":  {"icon": "💰", "color": "#FF5722", "base": 40},
    "Ration & PDS":        {"icon": "🛒", "color": "#607D8B", "base": 62},
    "Employment/MGNREGA":  {"icon": "👷", "color": "#8BC34A", "base": 58},
}

OSINT_SOURCES = [
    "Twitter/X Social",
    "PG Portal (Govt.)",
    "MyGov Portal",
    "News Articles",
    "RTI Filings",
    "Reddit/Forums",
    "Local Media",
]

SENTIMENT_LABELS = ["Negative", "Neutral", "Positive"]
PRIORITY_LABELS  = ["Critical", "High", "Medium", "Low"]

# ─────────────────────────────────────────────────────────────────────────────
# DATA GENERATION — Realistic OSINT simulation (last 16 weeks)
# ─────────────────────────────────────────────────────────────────────────────

def generate_weekly_dates(n_weeks: int = 16) -> list:
    today = datetime.today()
    monday = today - timedelta(days=today.weekday())
    return [(monday - timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(n_weeks - 1, -1, -1)]

def seasonal_noise(week_idx: int, amplitude: float = 1.0) -> float:
    """Add realistic seasonal / event spikes."""
    spike = 0
    # Budget announcement spike around week 3–4
    if 3 <= week_idx <= 5:
        spike += amplitude * 0.25
    # Monsoon water grievances peak weeks 7–10
    if 7 <= week_idx <= 10:
        spike += amplitude * 0.30
    # Election / rally period weeks 12–14
    if 12 <= week_idx <= 14:
        spike += amplitude * 0.40
    return spike

np.random.seed(42)
random.seed(42)

weekly_dates = generate_weekly_dates(16)
N_WEEKS = len(weekly_dates)

# ── Master DataFrame: district × category × week ──────────────────────────
records = []
for district in GUJARAT_DISTRICTS:
    # Population-weighted district modifier
    pop_mod = {
        "Ahmedabad": 2.5, "Surat": 2.2, "Vadodara": 1.8, "Rajkot": 1.6,
        "Gandhinagar": 1.2, "Mehsana": 1.1, "Bhavnagar": 1.1,
    }.get(district, 0.7 + random.random() * 0.6)

    for cat, meta in GRIEVANCE_CATEGORIES.items():
        base = meta["base"] * pop_mod
        for wi, week in enumerate(weekly_dates):
            val = max(0, int(
                base
                + seasonal_noise(wi, base)
                + np.random.normal(0, base * 0.15)
            ))
            source_dist = np.random.dirichlet(np.ones(len(OSINT_SOURCES)) * 2) * val
            records.append({
                "week":     week,
                "district": district,
                "category": cat,
                "count":    val,
                "resolved": max(0, int(val * (0.55 + random.random() * 0.30))),
                "sentiment_neg": int(val * (0.50 + random.random() * 0.20)),
                "sentiment_neu": int(val * (0.25 + random.random() * 0.10)),
                "sentiment_pos": int(val * (0.05 + random.random() * 0.10)),
                **{f"src_{s.replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '').replace('.', '')}": int(v)
                   for s, v in zip(OSINT_SOURCES, source_dist)},
            })

df = pd.DataFrame(records)
df["week"] = pd.to_datetime(df["week"])
df["pending"] = df["count"] - df["resolved"]
df["resolution_rate"] = (df["resolved"] / df["count"].replace(0, 1) * 100).round(1)

# Aggregate helpers
weekly_total   = df.groupby("week")["count"].sum().reset_index()
district_total = df.groupby("district")["count"].sum().reset_index().sort_values("count", ascending=False)
category_total = df.groupby("category")["count"].sum().reset_index().sort_values("count", ascending=False)
latest_week    = df["week"].max()
prev_week      = latest_week - timedelta(weeks=1)

kpi_latest   = df[df["week"] == latest_week]["count"].sum()
kpi_prev     = df[df["week"] == prev_week]["count"].sum()
kpi_change   = round((kpi_latest - kpi_prev) / max(kpi_prev, 1) * 100, 1)
kpi_resolved = df[df["week"] == latest_week]["resolved"].sum()
kpi_pending  = df[df["week"] == latest_week]["pending"].sum()
kpi_critical = df[(df["week"] == latest_week) & (df["count"] > df["count"].quantile(0.85))].shape[0]

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE (dark intelligence theme)
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK   = "#0a0e1a"
BG_CARD   = "#111827"
BG_PANEL  = "#1a2235"
ACCENT    = "#00d4ff"
ACCENT2   = "#7c3aed"
DANGER    = "#ef4444"
SUCCESS   = "#22c55e"
WARNING   = "#f59e0b"
TEXT_PRI  = "#f1f5f9"
TEXT_SEC  = "#94a3b8"
BORDER    = "#1e293b"

CAT_COLORS = [m["color"] for m in GRIEVANCE_CATEGORIES.values()]

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=11),
    margin=dict(l=10, r=10, t=35, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(size=10)),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, tickfont=dict(size=10)),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, tickfont=dict(size=10)),
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER — KPI card
# ─────────────────────────────────────────────────────────────────────────────
def kpi_card(title: str, value, sub: str = "", color: str = ACCENT, icon: str = ""):
    return html.Div([
        html.Div([
            html.Span(icon, style={"fontSize": "22px", "marginRight": "8px"}),
            html.Span(title, style={"color": TEXT_SEC, "fontSize": "12px", "fontWeight": "600",
                                    "textTransform": "uppercase", "letterSpacing": "1px"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px"}),
        html.Div(f"{value:,}" if isinstance(value, int) else str(value),
                 style={"fontSize": "28px", "fontWeight": "700", "color": color, "lineHeight": "1"}),
        html.Div(sub, style={"color": TEXT_SEC, "fontSize": "11px", "marginTop": "4px"}),
    ], style={
        "background": BG_CARD, "border": f"1px solid {BORDER}",
        "borderTop": f"3px solid {color}",
        "borderRadius": "10px", "padding": "16px 20px",
        "flex": "1", "minWidth": "160px",
    })

# ─────────────────────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    title="Gujarat OSINT Intelligence Dashboard",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
app.layout = html.Div([

    # ── TOP HEADER ──────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Div("🔍", style={"fontSize": "28px", "marginRight": "12px"}),
            html.Div([
                html.H1("Gujarat OSINT Intelligence Dashboard",
                        style={"margin": "0", "fontSize": "20px", "fontWeight": "700",
                               "color": ACCENT, "letterSpacing": "0.5px"}),
                html.P("Real-time open-source intelligence across all 33 districts · Citizen Grievances & Government Feedback",
                       style={"margin": "2px 0 0", "color": TEXT_SEC, "fontSize": "12px"}),
            ]),
        ], style={"display": "flex", "alignItems": "center"}),

        html.Div([
            html.Div([
                html.Span("● LIVE", style={"color": SUCCESS, "fontWeight": "700", "fontSize": "12px",
                                           "animation": "blink 1.5s infinite"}),
                html.Span(f"  Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
                          style={"color": TEXT_SEC, "fontSize": "12px", "marginLeft": "8px"}),
            ]),
            html.Div(f"Data window: {weekly_dates[0]}  →  {weekly_dates[-1]}",
                     style={"color": TEXT_SEC, "fontSize": "11px", "marginTop": "3px"}),
        ], style={"textAlign": "right"}),
    ], style={
        "background": "linear-gradient(90deg, #0d1526 0%, #111827 100%)",
        "borderBottom": f"2px solid {ACCENT}",
        "padding": "14px 24px", "display": "flex",
        "justifyContent": "space-between", "alignItems": "center",
    }),

    # ── MAIN BODY ───────────────────────────────────────────────────────────
    html.Div([

        # ── LEFT SIDEBAR ────────────────────────────────────────────────────
        html.Div([
            html.Div("🗺 FILTERS", style={"color": ACCENT, "fontSize": "11px", "fontWeight": "700",
                                          "letterSpacing": "2px", "marginBottom": "14px"}),

            html.Label("District", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
            dcc.Dropdown(
                id="dd-district",
                options=[{"label": "All Districts", "value": "ALL"}] +
                        [{"label": d, "value": d} for d in GUJARAT_DISTRICTS],
                value="ALL", clearable=False,
                style={"marginBottom": "14px", "fontSize": "12px"},
            ),

            html.Label("Grievance Category", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
            dcc.Dropdown(
                id="dd-category",
                options=[{"label": "All Categories", "value": "ALL"}] +
                        [{"label": f"{v['icon']} {k}", "value": k}
                         for k, v in GRIEVANCE_CATEGORIES.items()],
                value="ALL", clearable=False,
                style={"marginBottom": "14px", "fontSize": "12px"},
            ),

            html.Label("OSINT Source", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
            dcc.Dropdown(
                id="dd-source",
                options=[{"label": "All Sources", "value": "ALL"}] +
                        [{"label": s, "value": s} for s in OSINT_SOURCES],
                value="ALL", clearable=False,
                style={"marginBottom": "14px", "fontSize": "12px"},
            ),

            html.Label("Weeks to Display", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
            dcc.Slider(
                id="sl-weeks", min=4, max=16, step=1, value=12,
                marks={4: "4w", 8: "8w", 12: "12w", 16: "16w"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),

            html.Hr(style={"borderColor": BORDER, "margin": "18px 0"}),

            # Source legend
            html.Div("📡 OSINT SOURCES", style={"color": ACCENT, "fontSize": "11px",
                                                 "fontWeight": "700", "letterSpacing": "2px",
                                                 "marginBottom": "10px"}),
            *[html.Div([
                html.Div(style={"width": "8px", "height": "8px", "borderRadius": "50%",
                                "backgroundColor": c, "marginRight": "8px", "flexShrink": "0"}),
                html.Span(s, style={"color": TEXT_SEC, "fontSize": "11px"}),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px"})
              for s, c in zip(OSINT_SOURCES,
                              ["#1DA1F2", "#FF6B35", "#00BFA5", "#FF4081",
                               "#AB47BC", "#FF7043", "#26C6DA"])],

            html.Hr(style={"borderColor": BORDER, "margin": "18px 0"}),

            # Priority legend
            html.Div("🚨 PRIORITY LEVELS", style={"color": ACCENT, "fontSize": "11px",
                                                    "fontWeight": "700", "letterSpacing": "2px",
                                                    "marginBottom": "10px"}),
            *[html.Div([
                html.Div(style={"width": "8px", "height": "8px", "borderRadius": "2px",
                                "backgroundColor": c, "marginRight": "8px"}),
                html.Span(lbl, style={"color": TEXT_SEC, "fontSize": "11px"}),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px"})
              for lbl, c in zip(PRIORITY_LABELS, [DANGER, WARNING, ACCENT, SUCCESS])],

        ], style={
            "width": "220px", "minWidth": "220px", "background": BG_CARD,
            "padding": "18px", "borderRight": f"1px solid {BORDER}",
            "overflowY": "auto", "height": "calc(100vh - 64px)",
        }),

        # ── RIGHT CONTENT AREA ───────────────────────────────────────────────
        html.Div([

            # ── KPI STRIP ───────────────────────────────────────────────────
            html.Div(id="kpi-strip", style={"display": "flex", "gap": "12px",
                                             "flexWrap": "wrap", "marginBottom": "16px"}),

            # ── ROW 1: Weekly trend + Source breakdown ────────────────────
            html.Div([
                html.Div([
                    html.Div("📈 Weekly Grievance Trends by Category",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "marginBottom": "4px",
                                    "padding": "10px 14px 0"}),
                    dcc.Graph(id="graph-weekly-trend", style={"height": "280px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "2", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),

                html.Div([
                    html.Div("📡 Grievances by OSINT Source (Latest Week)",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "marginBottom": "4px",
                                    "padding": "10px 14px 0"}),
                    dcc.Graph(id="graph-source-pie", style={"height": "280px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "1", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),
            ], style={"display": "flex", "gap": "12px", "marginBottom": "12px"}),

            # ── ROW 2: District heatmap + Category bar ─────────────────────
            html.Div([
                html.Div([
                    html.Div("🏙️ District-wise Grievance Intensity (All Time)",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "marginBottom": "4px",
                                    "padding": "10px 14px 0"}),
                    dcc.Graph(id="graph-district-bar", style={"height": "300px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "3", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),

                html.Div([
                    html.Div("📊 Category Breakdown",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "marginBottom": "4px",
                                    "padding": "10px 14px 0"}),
                    dcc.Graph(id="graph-category-donut", style={"height": "300px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "1", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),
            ], style={"display": "flex", "gap": "12px", "marginBottom": "12px"}),

            # ── ROW 3: Resolution rate + Sentiment + Week-over-week ────────
            html.Div([
                html.Div([
                    html.Div("✅ Resolution Rate Trend",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "padding": "10px 14px 4px"}),
                    dcc.Graph(id="graph-resolution", style={"height": "240px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "1", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),

                html.Div([
                    html.Div("😠 Sentiment Analysis (Latest Week)",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "padding": "10px 14px 4px"}),
                    dcc.Graph(id="graph-sentiment", style={"height": "240px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "1", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),

                html.Div([
                    html.Div("🔥 Week-over-Week Spike Detection",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "padding": "10px 14px 4px"}),
                    dcc.Graph(id="graph-wow", style={"height": "240px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "1", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),
            ], style={"display": "flex", "gap": "12px", "marginBottom": "12px"}),

            # ── ROW 4: Heatmap matrix district × category ─────────────────
            html.Div([
                html.Div([
                    html.Div("🗺️ District × Category Heatmap (Latest Week)",
                             style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                    "letterSpacing": "1px", "padding": "10px 14px 4px"}),
                    dcc.Graph(id="graph-heatmap", style={"height": "420px"},
                              config={"displayModeBar": False}),
                ], style={"flex": "1", "background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),
            ], style={"marginBottom": "12px"}),

            # ── ROW 5: Alert table ─────────────────────────────────────────
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("🚨 Active Intelligence Alerts",
                                  style={"color": DANGER, "fontSize": "12px", "fontWeight": "700",
                                         "letterSpacing": "1px"}),
                        html.Span(" — Districts with abnormal grievance spikes this week",
                                  style={"color": TEXT_SEC, "fontSize": "11px"}),
                    ], style={"padding": "10px 14px 4px"}),
                    html.Div(id="alert-table", style={"padding": "0 14px 14px"}),
                ], style={"background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {DANGER}33"}),
            ], style={"marginBottom": "12px"}),

            # ── ROW 6: Raw data explorer ───────────────────────────────────
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("🔎 OSINT Data Explorer",
                                  style={"color": ACCENT, "fontSize": "12px", "fontWeight": "700",
                                         "letterSpacing": "1px"}),
                        html.Span(" (latest week · top 50 rows)",
                                  style={"color": TEXT_SEC, "fontSize": "11px"}),
                    ], style={"padding": "10px 14px 8px"}),
                    html.Div(id="data-table", style={"padding": "0 14px 14px"}),
                ], style={"background": BG_CARD, "borderRadius": "10px",
                          "border": f"1px solid {BORDER}"}),
            ]),

        ], style={"flex": "1", "padding": "16px", "overflowY": "auto",
                  "height": "calc(100vh - 64px)"}),

    ], style={"display": "flex", "height": "calc(100vh - 64px)"}),

], style={"background": BG_DARK, "minHeight": "100vh",
          "fontFamily": "Inter, Segoe UI, Arial, sans-serif", "color": TEXT_PRI})

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

def filter_df(district: str, category: str, n_weeks: int) -> pd.DataFrame:
    cutoff = pd.to_datetime(weekly_dates[-n_weeks])
    filtered = df[df["week"] >= cutoff].copy()
    if district != "ALL":
        filtered = filtered[filtered["district"] == district]
    if category != "ALL":
        filtered = filtered[filtered["category"] == category]
    return filtered


# ── KPI Strip ────────────────────────────────────────────────────────────────
@app.callback(
    Output("kpi-strip", "children"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_kpis(district, category, n_weeks):
    fdf = filter_df(district, category, n_weeks)
    latest = fdf["week"].max()
    prev   = latest - timedelta(weeks=1)
    cur    = fdf[fdf["week"] == latest]["count"].sum()
    prv    = fdf[fdf["week"] == prev]["count"].sum()
    chg    = round((cur - prv) / max(prv, 1) * 100, 1)
    res    = fdf[fdf["week"] == latest]["resolved"].sum()
    pend   = fdf[fdf["week"] == latest]["pending"].sum()
    res_rt = round(res / max(cur, 1) * 100, 1)
    total  = fdf["count"].sum()
    chg_col = DANGER if chg > 0 else SUCCESS
    chg_sign = "▲" if chg > 0 else "▼"

    return [
        kpi_card("Total Grievances",  int(total),  f"Across {n_weeks} weeks",    ACCENT,   "📋"),
        kpi_card("This Week",         int(cur),    f"{chg_sign} {abs(chg)}% vs last week", chg_col, "📅"),
        kpi_card("Resolved",          int(res),    f"{res_rt}% resolution rate",  SUCCESS,  "✅"),
        kpi_card("Pending",           int(pend),   "Awaiting action",             WARNING,  "⏳"),
        kpi_card("Districts Covered", len(fdf["district"].unique()), "Active reporting", ACCENT2, "🗺️"),
        kpi_card("Data Sources",      len(OSINT_SOURCES), "OSINT channels",       "#1DA1F2", "📡"),
    ]


# ── Weekly Trend Line ─────────────────────────────────────────────────────────
@app.callback(
    Output("graph-weekly-trend", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_trend(district, category, n_weeks):
    fdf = filter_df(district, category, n_weeks)
    if category == "ALL":
        grp = fdf.groupby(["week", "category"])["count"].sum().reset_index()
        fig = go.Figure()
        for i, (cat, meta) in enumerate(GRIEVANCE_CATEGORIES.items()):
            sub = grp[grp["category"] == cat]
            fig.add_trace(go.Scatter(
                x=sub["week"], y=sub["count"], name=f"{meta['icon']} {cat}",
                mode="lines+markers", line=dict(color=meta["color"], width=2),
                marker=dict(size=4), hovertemplate="%{y:,} grievances<extra>%{fullData.name}</extra>",
            ))
    else:
        grp = fdf.groupby("week")["count"].sum().reset_index()
        meta = GRIEVANCE_CATEGORIES.get(category, {"color": ACCENT, "icon": "📋"})
        fig = go.Figure(go.Scatter(
            x=grp["week"], y=grp["count"], name=category,
            mode="lines+markers", fill="tozeroy",
            line=dict(color=meta["color"], width=2.5),
            fillcolor=meta["color"] + "33",
            hovertemplate="%{y:,} grievances<extra></extra>",
        ))
        # Add 7-day moving average
        if len(grp) >= 3:
            grp["ma"] = grp["count"].rolling(3, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=grp["week"], y=grp["ma"], name="3-week MA",
                mode="lines", line=dict(color="white", width=1.5, dash="dot"),
            ))

    fig.update_layout(**PLOT_LAYOUT)
    fig.update_xaxes(tickformat="%d %b")
    return fig


# ── Source Pie ────────────────────────────────────────────────────────────────
@app.callback(
    Output("graph-source-pie", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_source_pie(district, category):
    fdf = filter_df(district, category, 1)
    src_cols = [c for c in df.columns if c.startswith("src_")]
    totals = fdf[src_cols].sum()
    labels = [s for s in OSINT_SOURCES]
    values = [int(totals.get(sc, 0)) for sc in src_cols]
    colors = ["#1DA1F2", "#FF6B35", "#00BFA5", "#FF4081", "#AB47BC", "#FF7043", "#26C6DA"]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color=BG_DARK, width=2)),
        textinfo="percent", hoverinfo="label+value",
        insidetextfont=dict(color="white", size=10),
    ))
    fig.update_layout(
        **PLOT_LAYOUT,
        annotations=[dict(text="Sources", x=0.5, y=0.5, font_size=13,
                          font_color=TEXT_PRI, showarrow=False)],
        showlegend=True,
        legend=dict(font=dict(size=10), orientation="v", x=1.0, y=0.5),
        margin=dict(l=10, r=90, t=35, b=10),
    )
    return fig


# ── District Bar ──────────────────────────────────────────────────────────────
@app.callback(
    Output("graph-district-bar", "figure"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_district_bar(category, n_weeks):
    fdf = filter_df("ALL", category, n_weeks)
    grp = fdf.groupby("district")["count"].sum().reset_index().sort_values("count", ascending=True)

    max_v = grp["count"].max()
    colors = [
        DANGER if v > max_v * 0.80 else
        WARNING if v > max_v * 0.55 else
        ACCENT if v > max_v * 0.35 else SUCCESS
        for v in grp["count"]
    ]

    fig = go.Figure(go.Bar(
        x=grp["count"], y=grp["district"],
        orientation="h", marker_color=colors,
        hovertemplate="%{y}: %{x:,}<extra></extra>",
        text=grp["count"].apply(lambda v: f"{v:,}"),
        textposition="outside", textfont=dict(size=9, color=TEXT_SEC),
    ))
    fig.update_layout(**PLOT_LAYOUT, bargap=0.25)
    fig.update_xaxes(title_text="Total Grievances")
    return fig


# ── Category Donut ────────────────────────────────────────────────────────────
@app.callback(
    Output("graph-category-donut", "figure"),
    Input("dd-district", "value"),
    Input("sl-weeks", "value"),
)
def update_category_donut(district, n_weeks):
    fdf = filter_df(district, "ALL", n_weeks)
    grp = fdf.groupby("category")["count"].sum().reset_index()
    icons = [GRIEVANCE_CATEGORIES[c]["icon"] for c in grp["category"]]
    labels = [f"{i} {c}" for i, c in zip(icons, grp["category"])]

    fig = go.Figure(go.Pie(
        labels=labels, values=grp["count"], hole=0.5,
        marker=dict(colors=CAT_COLORS, line=dict(color=BG_DARK, width=1)),
        textinfo="percent", hoverinfo="label+value",
        insidetextfont=dict(color="white", size=9),
    ))
    fig.update_layout(
        **PLOT_LAYOUT,
        showlegend=True,
        legend=dict(font=dict(size=8.5), orientation="v", x=1.0, y=0.5),
        margin=dict(l=5, r=100, t=35, b=5),
    )
    return fig


# ── Resolution Rate ───────────────────────────────────────────────────────────
@app.callback(
    Output("graph-resolution", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_resolution(district, category, n_weeks):
    fdf = filter_df(district, category, n_weeks)
    grp = fdf.groupby("week").agg({"count": "sum", "resolved": "sum"}).reset_index()
    grp["rate"] = (grp["resolved"] / grp["count"].replace(0, 1) * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grp["week"], y=grp["count"], name="Total",
        marker_color=ACCENT + "55", yaxis="y",
        hovertemplate="Total: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=grp["week"], y=grp["rate"], name="Resolution %",
        mode="lines+markers", line=dict(color=SUCCESS, width=2.5),
        marker=dict(size=5), yaxis="y2",
        hovertemplate="Rate: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **PLOT_LAYOUT,
        yaxis=dict(title="Count", gridcolor=BORDER, tickfont=dict(size=10)),
        yaxis2=dict(title="Resolution %", overlaying="y", side="right",
                    range=[0, 105], ticksuffix="%", gridcolor="transparent",
                    tickfont=dict(size=10)),
        legend=dict(orientation="h", y=1.08, x=0),
        barmode="overlay",
    )
    fig.update_xaxes(tickformat="%d %b")
    return fig


# ── Sentiment Bars ────────────────────────────────────────────────────────────
@app.callback(
    Output("graph-sentiment", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_sentiment(district, category):
    fdf = filter_df(district, category, 1)
    neg = int(fdf["sentiment_neg"].sum())
    neu = int(fdf["sentiment_neu"].sum())
    pos = int(fdf["sentiment_pos"].sum())
    total = max(neg + neu + pos, 1)

    fig = go.Figure()
    for val, label, color in zip(
        [neg, neu, pos],
        ["😠 Negative", "😐 Neutral", "😊 Positive"],
        [DANGER, WARNING, SUCCESS]
    ):
        fig.add_trace(go.Bar(
            x=[val], y=[label], orientation="h",
            marker_color=color,
            text=[f"{val:,}  ({val/total*100:.1f}%)"],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
            hovertemplate=f"{label}: %{{x:,}}<extra></extra>",
            name=label,
        ))
    fig.update_layout(**PLOT_LAYOUT, showlegend=False, barmode="relative",
                      xaxis=dict(title="Mentions", gridcolor=BORDER))
    return fig


# ── WoW Spike Detection ────────────────────────────────────────────────────────
@app.callback(
    Output("graph-wow", "figure"),
    Input("dd-district", "value"),
    Input("sl-weeks", "value"),
)
def update_wow(district, n_weeks):
    fdf = filter_df(district, "ALL", n_weeks)
    grp = fdf.groupby(["week", "category"])["count"].sum().reset_index()
    latest = grp["week"].max()
    prev   = latest - timedelta(weeks=1)

    cur_wk = grp[grp["week"] == latest].set_index("category")["count"]
    prv_wk = grp[grp["week"] == prev].set_index("category")["count"]
    wow = ((cur_wk - prv_wk) / prv_wk.replace(0, 1) * 100).round(1).sort_values()

    colors = [DANGER if v > 0 else SUCCESS for v in wow.values]
    icons  = [GRIEVANCE_CATEGORIES.get(c, {}).get("icon", "📋") for c in wow.index]
    labels = [f"{i} {c}" for i, c in zip(icons, wow.index)]

    fig = go.Figure(go.Bar(
        x=wow.values, y=labels, orientation="h",
        marker_color=colors,
        text=[f"{'▲' if v > 0 else '▼'} {abs(v):.1f}%" for v in wow.values],
        textposition="outside", textfont=dict(size=10),
        hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=TEXT_SEC, line_width=1)
    fig.update_layout(**PLOT_LAYOUT, showlegend=False,
                      xaxis=dict(title="WoW Change (%)", gridcolor=BORDER, ticksuffix="%"))
    return fig


# ── District × Category Heatmap ───────────────────────────────────────────────
@app.callback(
    Output("graph-heatmap", "figure"),
    Input("sl-weeks", "value"),
)
def update_heatmap(n_weeks):
    fdf = filter_df("ALL", "ALL", 1)
    pivot = fdf.pivot_table(index="district", columns="category",
                            values="count", aggfunc="sum").fillna(0)

    # Reorder columns by total
    col_order = category_total["category"].tolist()
    pivot = pivot[[c for c in col_order if c in pivot.columns]]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{GRIEVANCE_CATEGORIES[c]['icon']} {c}" for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[
            [0.0,  "#0a0e1a"],
            [0.25, "#1a3a5c"],
            [0.50, "#1a6b9e"],
            [0.75, "#f59e0b"],
            [1.0,  "#ef4444"],
        ],
        hovertemplate="District: %{y}<br>Category: %{x}<br>Grievances: %{z:,}<extra></extra>",
        colorbar=dict(
            title="Count", tickfont=dict(color=TEXT_PRI),
            titlefont=dict(color=TEXT_PRI),
        ),
    ))
    fig.update_layout(
        **PLOT_LAYOUT,
        margin=dict(l=10, r=10, t=30, b=80),
        xaxis=dict(tickangle=-35, tickfont=dict(size=9), gridcolor="transparent"),
        yaxis=dict(tickfont=dict(size=9), gridcolor="transparent"),
    )
    return fig


# ── Alert Table ────────────────────────────────────────────────────────────────
@app.callback(
    Output("alert-table", "children"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_alerts(district, category):
    fdf  = filter_df(district, category, 4)
    grp  = fdf.groupby(["district", "category", "week"])["count"].sum().reset_index()
    latest = grp["week"].max()
    prev   = latest - timedelta(weeks=1)

    cur_grp = grp[grp["week"] == latest].set_index(["district", "category"])["count"]
    prv_grp = grp[grp["week"] == prev].set_index(["district", "category"])["count"]
    wow = ((cur_grp - prv_grp) / prv_grp.replace(0, 1) * 100).round(1)
    spikes = wow[wow > 20].sort_values(ascending=False).head(15).reset_index()
    spikes.columns = ["District", "Category", "WoW Change %"]
    spikes["Current Count"] = cur_grp.reindex(
        pd.MultiIndex.from_frame(spikes[["District", "Category"]])).values
    spikes["Priority"] = spikes["WoW Change %"].apply(
        lambda v: "🔴 Critical" if v > 50 else "🟠 High" if v > 35 else "🟡 Medium"
    )
    spikes["Category"] = spikes["Category"].apply(
        lambda c: f"{GRIEVANCE_CATEGORIES.get(c, {}).get('icon', '')} {c}"
    )
    spikes["WoW Change %"] = spikes["WoW Change %"].apply(lambda v: f"▲ {v:.1f}%")

    if spikes.empty:
        return html.Div("✅ No critical spikes detected this week.",
                        style={"color": SUCCESS, "padding": "8px", "fontSize": "13px"})

    return dash_table.DataTable(
        data=spikes.to_dict("records"),
        columns=[{"name": c, "id": c} for c in spikes.columns],
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": BG_PANEL, "color": ACCENT,
            "fontWeight": "700", "fontSize": "11px",
            "borderBottom": f"1px solid {BORDER}",
            "textTransform": "uppercase", "letterSpacing": "1px",
        },
        style_cell={
            "backgroundColor": "transparent", "color": TEXT_PRI,
            "fontSize": "12px", "border": f"1px solid {BORDER}",
            "padding": "6px 12px", "textAlign": "left",
        },
        style_data_conditional=[
            {"if": {"filter_query": '{Priority} contains "Critical"'},
             "color": DANGER, "fontWeight": "600"},
            {"if": {"filter_query": '{Priority} contains "High"'},
             "color": WARNING},
        ],
        page_size=10, sort_action="native",
    )


# ── Data Table Explorer ────────────────────────────────────────────────────────
@app.callback(
    Output("data-table", "children"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_data_table(district, category):
    fdf = filter_df(district, category, 1)
    display = fdf[["week", "district", "category", "count", "resolved",
                    "pending", "resolution_rate"]].copy()
    display["week"] = display["week"].dt.strftime("%Y-%m-%d")
    display["Category"] = display["category"].apply(
        lambda c: f"{GRIEVANCE_CATEGORIES.get(c, {}).get('icon', '')} {c}"
    )
    display = display.rename(columns={
        "week": "Week", "district": "District", "category": "Raw Category",
        "count": "Total", "resolved": "Resolved", "pending": "Pending",
        "resolution_rate": "Resolution %",
    })
    display = display[["Week", "District", "Category", "Total",
                        "Resolved", "Pending", "Resolution %"]].sort_values(
        "Total", ascending=False).head(50)

    return dash_table.DataTable(
        data=display.to_dict("records"),
        columns=[{"name": c, "id": c} for c in display.columns],
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": BG_PANEL, "color": ACCENT,
            "fontWeight": "700", "fontSize": "11px",
            "borderBottom": f"1px solid {BORDER}",
            "textTransform": "uppercase", "letterSpacing": "1px",
        },
        style_cell={
            "backgroundColor": "transparent", "color": TEXT_PRI,
            "fontSize": "12px", "border": f"1px solid {BORDER}",
            "padding": "6px 12px", "textAlign": "left",
            "minWidth": "100px", "maxWidth": "200px",
        },
        style_data_conditional=[
            {"if": {"column_id": "Total", "filter_query": "{Total} > 200"},
             "color": DANGER, "fontWeight": "600"},
            {"if": {"column_id": "Resolution %", "filter_query": "{Resolution %} > 75"},
             "color": SUCCESS},
            {"if": {"column_id": "Resolution %", "filter_query": "{Resolution %} < 50"},
             "color": WARNING},
        ],
        page_size=15, sort_action="native", filter_action="native",
        tooltip_data=[{
            "Resolution %": {"value": f"{'Good' if r['Resolution %'] >= 70 else 'Needs attention'}",
                             "type": "markdown"}
        } for _, r in display.iterrows()],
    )


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS INJECTION
# ─────────────────────────────────────────────────────────────────────────────
app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; background: """ + BG_DARK + """; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: """ + BG_CARD + """; }
        ::-webkit-scrollbar-thumb { background: """ + BORDER + """; border-radius: 3px; }
        .Select-control { background-color: """ + BG_PANEL + """ !important;
                          border-color: """ + BORDER + """ !important; }
        .Select-value-label, .Select-placeholder { color: """ + TEXT_PRI + """ !important; }
        .Select-menu-outer { background-color: """ + BG_PANEL + """ !important;
                             border-color: """ + BORDER + """ !important; }
        .VirtualizedSelectOption { color: """ + TEXT_PRI + """ !important; }
        .VirtualizedSelectFocusedOption { background-color: """ + ACCENT + """33 !important; }
        .rc-slider-track { background-color: """ + ACCENT + """ !important; }
        .rc-slider-handle { border-color: """ + ACCENT + """ !important; background: """ + ACCENT + """ !important; }
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td:hover {
            background-color: """ + ACCENT + """22 !important; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  Gujarat OSINT Intelligence Dashboard")
    print("  Open: http://127.0.0.1:8050")
    print("=" * 65)
    app.run(debug=True, host="127.0.0.1", port=8050)
