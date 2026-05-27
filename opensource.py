"""
Gujarat OSINT Intelligence Dashboard  ·  v2.0
==============================================
Fully fixed version — all 9 charts render correctly.

Root-cause fixes applied:
  1. Explicit height in every fig.update_layout() — Plotly 6 + Dash 4
     do NOT infer height from the CSS container style.
  2. Separate pie_layout() (no xaxis/yaxis keys) for Pie charts.
  3. Plotly 6 colorbar API: title=dict(text=...) replaces titlefont.
  4. n_weeks cast to int in filter_df (Dash 4 Slider returns float).
  5. suppress_callback_exceptions=True for dcc.Tabs.
  6. District bar height = 700 px for 33 districts.
  7. Heatmap height = 620 px.
  8. New tab: Raw OSINT Data Sources (samples from osint_raw_data.py).
"""

import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

from osint_raw_data import ALL_SOURCES

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
    "Tapi", "Vadodara", "Valsad",
]

GRIEVANCE_CATEGORIES = {
    "Water Supply":           {"icon": "Water",  "color": "#2196F3", "base": 85},
    "Roads & Infrastructure": {"icon": "Roads",  "color": "#FF9800", "base": 92},
    "Electricity":            {"icon": "Power",  "color": "#FFEB3B", "base": 78},
    "Healthcare":             {"icon": "Health", "color": "#E91E63", "base": 65},
    "Sanitation & Waste":     {"icon": "Sanit",  "color": "#9C27B0", "base": 70},
    "Education":              {"icon": "Edu",    "color": "#00BCD4", "base": 55},
    "Law & Order":            {"icon": "Law",    "color": "#F44336", "base": 60},
    "Agriculture":            {"icon": "Agri",   "color": "#4CAF50", "base": 75},
    "Land & Revenue":         {"icon": "Land",   "color": "#795548", "base": 50},
    "Corruption/Bribery":     {"icon": "Corrupt","color": "#FF5722", "base": 40},
    "Ration & PDS":           {"icon": "Ration", "color": "#607D8B", "base": 62},
    "Employment/MGNREGA":     {"icon": "Jobs",   "color": "#8BC34A", "base": 58},
}

OSINT_SOURCES = list(ALL_SOURCES.keys())
SOURCE_COLORS = [v["color"] for v in ALL_SOURCES.values()]


def _src_col(s):
    return ("src_" + s
            .replace("/", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(".", ""))


SRC_COLS = [_src_col(s) for s in OSINT_SOURCES]
PRIORITY_LABELS = ["Critical", "High", "Medium", "Low"]

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
BG_DARK  = "#0a0e1a"
BG_CARD  = "#111827"
BG_PANEL = "#1a2235"
ACCENT   = "#00d4ff"
ACCENT2  = "#7c3aed"
DANGER   = "#ef4444"
SUCCESS  = "#22c55e"
WARNING  = "#f59e0b"
TEXT_PRI = "#f1f5f9"
TEXT_SEC = "#94a3b8"
BORDER   = "#1e293b"
CAT_COLORS = [m["color"] for m in GRIEVANCE_CATEGORIES.values()]


# ── Layout helpers ────────────────────────────────────────────────────────────
def base_layout(height=320):
    """For Bar / Scatter / Heatmap — includes xaxis/yaxis keys."""
    return dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, font=dict(size=10)),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, tickfont=dict(size=10)),
    )


def pie_layout(height=320):
    """For Pie/Donut — NO xaxis/yaxis to avoid Plotly 6 conflicts."""
    return dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=11),
        margin=dict(l=10, r=120, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER,
                    font=dict(size=9), x=1.02, y=0.5,
                    orientation="v"),
        showlegend=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DATA GENERATION — Realistic OSINT simulation (last 16 weeks)
# ─────────────────────────────────────────────────────────────────────────────
def _weekly_dates(n=16):
    today  = datetime.today()
    monday = today - timedelta(days=today.weekday())
    return [(monday - timedelta(weeks=i)).strftime("%Y-%m-%d")
            for i in range(n - 1, -1, -1)]


def _seasonal(wi, amp):
    s = 0.0
    if 3 <= wi <= 5:   s += amp * 0.25
    if 7 <= wi <= 10:  s += amp * 0.30
    if 12 <= wi <= 14: s += amp * 0.40
    return s


np.random.seed(42)
random.seed(42)

WEEKLY_DATES = _weekly_dates(16)

POP_MOD = {
    "Ahmedabad": 2.5, "Surat": 2.2, "Vadodara": 1.8, "Rajkot": 1.6,
    "Gandhinagar": 1.2, "Mehsana": 1.1, "Bhavnagar": 1.1,
}

records = []
for district in GUJARAT_DISTRICTS:
    pm = POP_MOD.get(district, 0.7 + random.random() * 0.6)
    for cat, meta in GRIEVANCE_CATEGORIES.items():
        base = meta["base"] * pm
        for wi, week in enumerate(WEEKLY_DATES):
            val = max(0, int(base + _seasonal(wi, base) +
                             np.random.normal(0, base * 0.15)))
            src_vals = np.random.dirichlet(np.ones(len(OSINT_SOURCES)) * 2) * val
            records.append({
                "week":          week,
                "district":      district,
                "category":      cat,
                "count":         val,
                "resolved":      max(0, int(val * (0.55 + random.random() * 0.30))),
                "sentiment_neg": int(val * (0.50 + random.random() * 0.20)),
                "sentiment_neu": int(val * (0.25 + random.random() * 0.10)),
                "sentiment_pos": int(val * (0.05 + random.random() * 0.10)),
                **{col: int(v) for col, v in zip(SRC_COLS, src_vals)},
            })

df = pd.DataFrame(records)
df["week"]            = pd.to_datetime(df["week"])
df["pending"]         = df["count"] - df["resolved"]
df["resolution_rate"] = (df["resolved"] / df["count"].replace(0, 1) * 100).round(1)

category_total = (df.groupby("category")["count"].sum()
                    .reset_index()
                    .sort_values("count", ascending=False))

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def filter_df(district, category, n_weeks):
    n   = int(n_weeks)                          # FIX: Dash 4 returns float
    cut = pd.to_datetime(WEEKLY_DATES[-n])
    fdf = df[df["week"] >= cut].copy()
    if district != "ALL":
        fdf = fdf[fdf["district"] == district]
    if category != "ALL":
        fdf = fdf[fdf["category"] == category]
    return fdf


def kpi_card(title, value, sub="", color=ACCENT, icon=""):
    return html.Div([
        html.Div([
            html.Span(icon + " ", style={"fontSize": "18px"}),
            html.Span(title, style={"color": TEXT_SEC, "fontSize": "11px",
                                    "fontWeight": "600", "textTransform": "uppercase",
                                    "letterSpacing": "1px"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"}),
        html.Div(
            f"{value:,}" if isinstance(value, int) else str(value),
            style={"fontSize": "24px", "fontWeight": "700",
                   "color": color, "lineHeight": "1"},
        ),
        html.Div(sub, style={"color": TEXT_SEC, "fontSize": "11px", "marginTop": "4px"}),
    ], style={
        "background": BG_CARD, "border": f"1px solid {BORDER}",
        "borderTop": f"3px solid {color}",
        "borderRadius": "10px", "padding": "12px 16px",
        "flex": "1", "minWidth": "150px",
    })


def stitle(text):
    return html.Div(text, style={
        "color": ACCENT, "fontSize": "12px", "fontWeight": "700",
        "letterSpacing": "0.8px", "padding": "10px 14px 4px",
    })


def card(children, style_extra=None):
    s = {"background": BG_CARD, "borderRadius": "10px",
         "border": f"1px solid {BORDER}", "overflow": "hidden"}
    if style_extra:
        s.update(style_extra)
    return html.Div(children, style=s)


# ─────────────────────────────────────────────────────────────────────────────
# RAW SOURCES TAB — built once at startup
# ─────────────────────────────────────────────────────────────────────────────
def _raw_table(data, color):
    if not data:
        return html.Div("No data", style={"color": TEXT_SEC, "padding": "8px"})
    cols = list(data[0].keys())
    return dash_table.DataTable(
        data=data,
        columns=[{"name": c, "id": c} for c in cols],
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": BG_PANEL, "color": color,
            "fontWeight": "700", "fontSize": "11px",
            "borderBottom": f"1px solid {BORDER}",
            "textTransform": "uppercase", "letterSpacing": "0.8px",
        },
        style_cell={
            "backgroundColor": "transparent", "color": TEXT_PRI,
            "fontSize": "12px", "border": f"1px solid {BORDER}",
            "padding": "7px 10px", "textAlign": "left",
            "whiteSpace": "normal", "maxWidth": "340px",
            "overflow": "hidden", "textOverflow": "ellipsis",
        },
        page_size=len(data),
        tooltip_data=[
            {col: {"value": str(row.get(col, "")), "type": "markdown"}
             for col in cols}
            for row in data
        ],
        tooltip_delay=0,
        tooltip_duration=None,
    )


def build_raw_tab():
    blocks = []
    for src_name, meta in ALL_SOURCES.items():
        color = meta["color"]
        icon  = meta["icon"]
        blocks.append(html.Div([
            html.Div([
                html.Span(icon + "  " + src_name,
                          style={"fontSize": "14px", "fontWeight": "700",
                                 "color": color, "letterSpacing": "0.4px"}),
                html.Span(f"  |  {len(meta['data'])} sample records",
                          style={"color": TEXT_SEC, "fontSize": "11px",
                                 "marginLeft": "8px"}),
            ], style={"padding": "12px 16px 6px",
                      "borderBottom": f"2px solid {color}50"}),
            html.Div(_raw_table(meta["data"], color),
                     style={"padding": "8px 12px 14px"}),
        ], style={
            "background": BG_CARD, "borderRadius": "10px",
            "border": f"1px solid {color}40", "marginBottom": "16px",
        }))
    return html.Div(blocks, style={"padding": "16px"})


RAW_TAB_CONTENT = build_raw_tab()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
SIDEBAR = html.Div([
    html.Div("FILTERS", style={"color": ACCENT, "fontSize": "11px", "fontWeight": "700",
                                "letterSpacing": "2px", "marginBottom": "14px"}),

    html.Label("District", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
    dcc.Dropdown(
        id="dd-district",
        options=[{"label": "All Districts", "value": "ALL"}] +
                [{"label": d, "value": d} for d in GUJARAT_DISTRICTS],
        value="ALL", clearable=False,
        style={"marginBottom": "12px", "fontSize": "12px"},
    ),

    html.Label("Category", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
    dcc.Dropdown(
        id="dd-category",
        options=[{"label": "All Categories", "value": "ALL"}] +
                [{"label": k, "value": k} for k in GRIEVANCE_CATEGORIES],
        value="ALL", clearable=False,
        style={"marginBottom": "12px", "fontSize": "12px"},
    ),

    html.Label("Weeks", style={"color": TEXT_SEC, "fontSize": "11px", "fontWeight": "600"}),
    dcc.Slider(
        id="sl-weeks", min=4, max=16, step=1, value=12,
        marks={4: "4w", 8: "8w", 12: "12w", 16: "16w"},
        tooltip={"placement": "bottom", "always_visible": False},
    ),

    html.Hr(style={"borderColor": BORDER, "margin": "16px 0"}),

    html.Div("OSINT SOURCES", style={"color": ACCENT, "fontSize": "11px",
                                      "fontWeight": "700", "letterSpacing": "2px",
                                      "marginBottom": "10px"}),
    *[html.Div([
        html.Div(style={"width": "8px", "height": "8px", "borderRadius": "50%",
                        "backgroundColor": c, "marginRight": "8px", "flexShrink": "0"}),
        html.Span(s, style={"color": TEXT_SEC, "fontSize": "11px"}),
    ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"})
      for s, c in zip(OSINT_SOURCES, SOURCE_COLORS)],

    html.Hr(style={"borderColor": BORDER, "margin": "16px 0"}),

    html.Div("PRIORITY", style={"color": ACCENT, "fontSize": "11px",
                                 "fontWeight": "700", "letterSpacing": "2px",
                                 "marginBottom": "10px"}),
    *[html.Div([
        html.Div(style={"width": "8px", "height": "8px", "borderRadius": "2px",
                        "backgroundColor": c, "marginRight": "8px"}),
        html.Span(lbl, style={"color": TEXT_SEC, "fontSize": "11px"}),
    ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"})
      for lbl, c in zip(PRIORITY_LABELS, [DANGER, WARNING, ACCENT, SUCCESS])],

], style={
    "width": "210px", "minWidth": "210px", "background": BG_CARD,
    "padding": "16px", "borderRight": f"1px solid {BORDER}",
    "overflowY": "auto",
})

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD TAB LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
DASHBOARD_PANEL = html.Div([
    SIDEBAR,
    html.Div([

        # KPI row
        html.Div(id="kpi-strip",
                 style={"display": "flex", "gap": "12px",
                        "flexWrap": "wrap", "marginBottom": "14px"}),

        # Row 1 — trend + source pie
        html.Div([
            card([stitle("Weekly Grievance Trends by Category"),
                  dcc.Graph(id="graph-weekly-trend",
                            config={"displayModeBar": False})],
                 {"flex": "2"}),
            card([stitle("Grievances by OSINT Source (Latest Week)"),
                  dcc.Graph(id="graph-source-pie",
                            config={"displayModeBar": False})],
                 {"flex": "1"}),
        ], style={"display": "flex", "gap": "12px", "marginBottom": "12px"}),

        # Row 2 — district bar + category donut
        html.Div([
            card([stitle("District-wise Grievance Intensity (All Weeks)"),
                  dcc.Graph(id="graph-district-bar",
                            config={"displayModeBar": False})],
                 {"flex": "3"}),
            card([stitle("Category Breakdown"),
                  dcc.Graph(id="graph-category-donut",
                            config={"displayModeBar": False})],
                 {"flex": "1"}),
        ], style={"display": "flex", "gap": "12px", "marginBottom": "12px"}),

        # Row 3 — resolution + sentiment + wow
        html.Div([
            card([stitle("Resolution Rate Trend"),
                  dcc.Graph(id="graph-resolution",
                            config={"displayModeBar": False})]),
            card([stitle("Sentiment Analysis (Latest Week)"),
                  dcc.Graph(id="graph-sentiment",
                            config={"displayModeBar": False})]),
            card([stitle("Week-over-Week Spike Detection"),
                  dcc.Graph(id="graph-wow",
                            config={"displayModeBar": False})]),
        ], style={"display": "flex", "gap": "12px", "marginBottom": "12px"}),

        # Row 4 — heatmap
        card([stitle("District x Category Heatmap (Latest Week)"),
              dcc.Graph(id="graph-heatmap",
                        config={"displayModeBar": False})],
             {"marginBottom": "12px"}),

        # Row 5 — alerts
        html.Div([
            html.Div([
                html.Div([
                    html.Span("INTELLIGENCE ALERTS",
                              style={"color": DANGER, "fontSize": "12px",
                                     "fontWeight": "700", "letterSpacing": "1px"}),
                    html.Span("  —  Districts with abnormal spikes this week",
                              style={"color": TEXT_SEC, "fontSize": "11px"}),
                ], style={"padding": "10px 14px 4px"}),
                html.Div(id="alert-table", style={"padding": "0 14px 14px"}),
            ], style={"background": BG_CARD, "borderRadius": "10px",
                      "border": f"1px solid {DANGER}40"}),
        ], style={"marginBottom": "12px"}),

        # Row 6 — data explorer
        card([
            html.Div([
                html.Span("OSINT Data Explorer",
                          style={"color": ACCENT, "fontSize": "12px",
                                 "fontWeight": "700", "letterSpacing": "1px"}),
                html.Span("  (latest week, top 50)",
                          style={"color": TEXT_SEC, "fontSize": "11px"}),
            ], style={"padding": "10px 14px 6px"}),
            html.Div(id="data-table", style={"padding": "0 14px 14px"}),
        ]),

    ], style={"flex": "1", "padding": "14px", "overflowY": "auto"}),

], style={"display": "flex", "height": "calc(100vh - 104px)"})

# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    title="Gujarat OSINT Intelligence Dashboard",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server

HEADER = html.Div([
    html.Div([
        html.Div("OSINT", style={"fontSize": "22px", "fontWeight": "900",
                                  "color": ACCENT, "marginRight": "10px",
                                  "letterSpacing": "3px"}),
        html.Div([
            html.Div("Gujarat OSINT Intelligence Dashboard",
                     style={"fontSize": "17px", "fontWeight": "700",
                            "color": TEXT_PRI, "margin": "0"}),
            html.Div("Real-time open-source intelligence across all 33 districts"
                     " | Citizen Grievances & Government Feedback",
                     style={"color": TEXT_SEC, "fontSize": "11px", "marginTop": "2px"}),
        ]),
    ], style={"display": "flex", "alignItems": "center"}),
    html.Div([
        html.Span("LIVE", style={"color": SUCCESS, "fontWeight": "700",
                                  "fontSize": "11px", "border": f"1px solid {SUCCESS}",
                                  "padding": "2px 6px", "borderRadius": "4px"}),
        html.Span(f"  {datetime.now().strftime('%d %b %Y %H:%M')}",
                  style={"color": TEXT_SEC, "fontSize": "11px", "marginLeft": "8px"}),
        html.Div(f"Data: {WEEKLY_DATES[0]} to {WEEKLY_DATES[-1]}",
                 style={"color": TEXT_SEC, "fontSize": "10px", "marginTop": "2px",
                        "textAlign": "right"}),
    ], style={"textAlign": "right"}),
], style={
    "background": "linear-gradient(90deg,#0d1526 0%,#111827 100%)",
    "borderBottom": f"2px solid {ACCENT}",
    "padding": "10px 22px", "display": "flex",
    "justifyContent": "space-between", "alignItems": "center",
    "height": "56px",
})

app.layout = html.Div([
    HEADER,
    dcc.Tabs(
        id="main-tabs",
        value="tab-dashboard",
        children=[
            dcc.Tab(
                label="Intelligence Dashboard",
                value="tab-dashboard",
                children=[DASHBOARD_PANEL],
                style={"backgroundColor": BG_DARK, "color": TEXT_SEC,
                       "border": f"1px solid {BORDER}",
                       "borderBottom": "none",
                       "padding": "7px 16px", "fontSize": "12px"},
                selected_style={"backgroundColor": BG_PANEL, "color": ACCENT,
                                "border": f"1px solid {ACCENT}",
                                "borderBottom": "none",
                                "padding": "7px 16px", "fontSize": "12px",
                                "fontWeight": "700"},
            ),
            dcc.Tab(
                label="Raw OSINT Data Sources",
                value="tab-raw-sources",
                children=[
                    html.Div([
                        html.Div([
                            html.Div("RAW OSINT SAMPLE RECORDS",
                                     style={"color": ACCENT, "fontSize": "13px",
                                            "fontWeight": "700", "letterSpacing": "1px",
                                            "marginBottom": "4px"}),
                            html.P(
                                "Sample records (5-8 rows per channel) showing "
                                "the actual data structure fetched from each OSINT source. "
                                "Hover over any cell to see the full text.",
                                style={"color": TEXT_SEC, "fontSize": "12px", "margin": "0"}
                            ),
                        ], style={"padding": "14px 16px 10px",
                                  "borderBottom": f"1px solid {BORDER}"}),
                        html.Div(RAW_TAB_CONTENT,
                                 style={"overflowY": "auto",
                                        "height": "calc(100vh - 130px)"}),
                    ]),
                ],
                style={"backgroundColor": BG_DARK, "color": TEXT_SEC,
                       "border": f"1px solid {BORDER}",
                       "borderBottom": "none",
                       "padding": "7px 16px", "fontSize": "12px"},
                selected_style={"backgroundColor": BG_PANEL, "color": ACCENT,
                                "border": f"1px solid {ACCENT}",
                                "borderBottom": "none",
                                "padding": "7px 16px", "fontSize": "12px",
                                "fontWeight": "700"},
            ),
        ],
        style={"backgroundColor": BG_DARK,
               "borderBottom": f"1px solid {BORDER}",
               "height": "36px"},
        colors={"border": BORDER, "primary": ACCENT, "background": BG_DARK},
    ),
], style={"background": BG_DARK, "minHeight": "100vh",
          "fontFamily": "Inter, Segoe UI, Arial, sans-serif", "color": TEXT_PRI})

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("kpi-strip", "children"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_kpis(district, category, n_weeks):
    fdf  = filter_df(district, category, n_weeks)
    lw   = fdf["week"].max()
    pw   = lw - timedelta(weeks=1)
    cur  = int(fdf[fdf["week"] == lw]["count"].sum())
    prv  = int(fdf[fdf["week"] == pw]["count"].sum())
    chg  = round((cur - prv) / max(prv, 1) * 100, 1)
    res  = int(fdf[fdf["week"] == lw]["resolved"].sum())
    pend = int(fdf[fdf["week"] == lw]["pending"].sum())
    rr   = round(res / max(cur, 1) * 100, 1)
    tot  = int(fdf["count"].sum())
    sgn, col = ("UP", DANGER) if chg > 0 else ("DOWN", SUCCESS)
    return [
        kpi_card("Total Grievances", tot,  f"Across {int(n_weeks)} weeks", ACCENT,  ">>"),
        kpi_card("This Week",        cur,  f"{sgn} {abs(chg)}% vs prev",  col,     "><"),
        kpi_card("Resolved",         res,  f"{rr}% resolution rate",      SUCCESS, "OK"),
        kpi_card("Pending",          pend, "Awaiting action",             WARNING, "!!"),
        kpi_card("Districts",        len(fdf["district"].unique()),
                 "Active reporting", ACCENT2, "GJ"),
        kpi_card("OSINT Sources",    len(OSINT_SOURCES),
                 "Live channels",    "#1DA1F2", ">>"),
    ]


@app.callback(
    Output("graph-weekly-trend", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_trend(district, category, n_weeks):
    fdf = filter_df(district, category, n_weeks)
    fig = go.Figure()

    if category == "ALL":
        grp = fdf.groupby(["week", "category"])["count"].sum().reset_index()
        for cat, meta in GRIEVANCE_CATEGORIES.items():
            sub = grp[grp["category"] == cat]
            fig.add_trace(go.Scatter(
                x=sub["week"], y=sub["count"],
                name=cat,
                mode="lines+markers",
                line=dict(color=meta["color"], width=2),
                marker=dict(size=4),
                hovertemplate="%{y:,}<extra>" + cat + "</extra>",
            ))
    else:
        grp  = fdf.groupby("week")["count"].sum().reset_index()
        meta = GRIEVANCE_CATEGORIES.get(category, {"color": ACCENT})
        fig.add_trace(go.Scatter(
            x=grp["week"], y=grp["count"],
            name=category,
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color=meta["color"], width=2.5),
            fillcolor=meta["color"] + "33",
            hovertemplate="%{y:,} grievances<extra></extra>",
        ))
        if len(grp) >= 3:
            grp["ma"] = grp["count"].rolling(3, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=grp["week"], y=grp["ma"],
                name="3-week MA",
                mode="lines",
                line=dict(color="white", width=1.5, dash="dot"),
            ))

    lo = base_layout(height=300)
    fig.update_layout(**lo)
    fig.update_xaxes(tickformat="%d %b")
    return fig


@app.callback(
    Output("graph-source-pie", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_source_pie(district, category):
    fdf    = filter_df(district, category, 1)
    values = [max(int(fdf[c].sum()), 0) for c in SRC_COLS]

    fig = go.Figure(go.Pie(
        labels=OSINT_SOURCES,
        values=values,
        hole=0.55,
        marker=dict(colors=SOURCE_COLORS,
                    line=dict(color=BG_DARK, width=2)),
        textinfo="percent",
        hoverinfo="label+value",
        textfont=dict(color="white", size=10),
    ))
    lo = pie_layout(height=300)
    lo["annotations"] = [dict(text="Sources", x=0.5, y=0.5,
                               font_size=12, font_color=TEXT_PRI,
                               showarrow=False)]
    fig.update_layout(**lo)
    return fig


@app.callback(
    Output("graph-district-bar", "figure"),
    Input("dd-category", "value"),
    Input("sl-weeks", "value"),
)
def update_district_bar(category, n_weeks):
    fdf = filter_df("ALL", category, n_weeks)
    grp = (fdf.groupby("district")["count"].sum()
              .reset_index()
              .sort_values("count", ascending=True))
    mx  = grp["count"].max()
    colors = [
        DANGER  if v > mx * 0.80 else
        WARNING if v > mx * 0.55 else
        ACCENT  if v > mx * 0.35 else SUCCESS
        for v in grp["count"]
    ]

    fig = go.Figure(go.Bar(
        x=grp["count"], y=grp["district"],
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}: %{x:,}<extra></extra>",
        text=grp["count"].apply(lambda v: f"{v:,}"),
        textposition="auto",
        textfont=dict(size=9, color=TEXT_PRI),
        cliponaxis=False,
    ))
    lo = base_layout(height=720)           # 33 districts need height
    lo["margin"] = dict(l=10, r=60, t=30, b=10)
    fig.update_layout(**lo)
    fig.update_xaxes(title_text="Total Grievances")
    return fig


@app.callback(
    Output("graph-category-donut", "figure"),
    Input("dd-district", "value"),
    Input("sl-weeks", "value"),
)
def update_category_donut(district, n_weeks):
    fdf = filter_df(district, "ALL", n_weeks)
    grp = fdf.groupby("category")["count"].sum().reset_index()

    fig = go.Figure(go.Pie(
        labels=grp["category"].tolist(),
        values=grp["count"].tolist(),
        hole=0.50,
        marker=dict(colors=CAT_COLORS,
                    line=dict(color=BG_DARK, width=1)),
        textinfo="percent",
        hoverinfo="label+value",
        textfont=dict(color="white", size=9),
    ))
    fig.update_layout(**pie_layout(height=720))
    return fig


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
        x=grp["week"], y=grp["count"],
        name="Total", marker_color=ACCENT + "44", yaxis="y",
        hovertemplate="Total: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=grp["week"], y=grp["rate"],
        name="Resolution %", yaxis="y2",
        mode="lines+markers",
        line=dict(color=SUCCESS, width=2.5),
        marker=dict(size=5),
        hovertemplate="Rate: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        height=270,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        barmode="overlay",
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.08, x=0, font=dict(size=10)),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER,
                   tickfont=dict(size=10), tickformat="%d %b"),
        yaxis=dict(title="Count", gridcolor=BORDER,
                   zerolinecolor=BORDER, tickfont=dict(size=10)),
        yaxis2=dict(title="Resolution %", overlaying="y", side="right",
                    range=[0, 110], ticksuffix="%",
                    gridcolor="transparent", tickfont=dict(size=10)),
    )
    return fig


@app.callback(
    Output("graph-sentiment", "figure"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_sentiment(district, category):
    fdf   = filter_df(district, category, 1)
    neg   = int(fdf["sentiment_neg"].sum())
    neu   = int(fdf["sentiment_neu"].sum())
    pos   = int(fdf["sentiment_pos"].sum())
    total = max(neg + neu + pos, 1)

    fig = go.Figure()
    for val, lbl, clr in [
        (neg, "Negative", DANGER),
        (neu, "Neutral",  WARNING),
        (pos, "Positive", SUCCESS),
    ]:
        pct = val / total * 100
        fig.add_trace(go.Bar(
            x=[val], y=[lbl],
            orientation="h",
            marker_color=clr,
            name=lbl,
            text=[f"{val:,}  ({pct:.1f}%)"],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
            hovertemplate=f"{lbl}: %{{x:,}}<extra></extra>",
        ))

    fig.update_layout(
        height=270,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False,
        barmode="relative",
        xaxis=dict(title="Mentions", gridcolor=BORDER,
                   zerolinecolor=BORDER, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER,
                   tickfont=dict(size=12)),
    )
    return fig


@app.callback(
    Output("graph-wow", "figure"),
    Input("dd-district", "value"),
    Input("sl-weeks", "value"),
)
def update_wow(district, n_weeks):
    fdf = filter_df(district, "ALL", n_weeks)
    grp = fdf.groupby(["week", "category"])["count"].sum().reset_index()
    lw  = grp["week"].max()
    pw  = lw - timedelta(weeks=1)

    cur = grp[grp["week"] == lw].set_index("category")["count"]
    prv = grp[grp["week"] == pw].set_index("category")["count"]
    wow = ((cur - prv) / prv.replace(0, 1) * 100).round(1).sort_values()

    labels = wow.index.tolist()
    values = wow.values.tolist()
    colors = [DANGER if v > 0 else SUCCESS for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker_color=colors,
        text=[("UP " if v > 0 else "DN ") + str(abs(round(v, 1))) + "%" for v in values],
        textposition="outside",
        textfont=dict(size=10, color=TEXT_PRI),
        hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
        cliponaxis=False,
    ))
    fig.add_vline(x=0, line_color=TEXT_SEC, line_width=1)

    fig.update_layout(
        height=270,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=11),
        margin=dict(l=10, r=70, t=30, b=10),
        showlegend=False,
        xaxis=dict(title="WoW Change (%)", gridcolor=BORDER,
                   zerolinecolor=BORDER, ticksuffix="%",
                   tickfont=dict(size=10)),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER,
                   tickfont=dict(size=10)),
    )
    return fig


@app.callback(
    Output("graph-heatmap", "figure"),
    Input("sl-weeks", "value"),
)
def update_heatmap(n_weeks):
    fdf   = filter_df("ALL", "ALL", 1)
    pivot = fdf.pivot_table(index="district", columns="category",
                            values="count", aggfunc="sum").fillna(0)

    col_order = category_total["category"].tolist()
    pivot = pivot.reindex(
        columns=[c for c in col_order if c in pivot.columns], fill_value=0)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0.00, "#0a0e1a"],
            [0.25, "#1a3a5c"],
            [0.50, "#1a6b9e"],
            [0.75, "#f59e0b"],
            [1.00, "#ef4444"],
        ],
        hovertemplate="<b>%{y}</b><br>%{x}<br>Grievances: %{z:,}<extra></extra>",
        colorbar=dict(
            title=dict(text="Count", font=dict(color=TEXT_PRI)),   # Plotly 6 API
            tickfont=dict(color=TEXT_PRI),
        ),
    ))
    fig.update_layout(
        height=640,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRI, family="Inter, Segoe UI, sans-serif", size=10),
        margin=dict(l=10, r=20, t=20, b=110),
        xaxis=dict(tickangle=-40, tickfont=dict(size=9),
                   gridcolor="transparent"),
        yaxis=dict(tickfont=dict(size=9), gridcolor="transparent"),
    )
    return fig


@app.callback(
    Output("alert-table", "children"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_alerts(district, category):
    fdf    = filter_df(district, category, 4)
    grp    = fdf.groupby(["district", "category", "week"])["count"].sum().reset_index()
    lw     = grp["week"].max()
    pw     = lw - timedelta(weeks=1)
    cur    = grp[grp["week"] == lw].set_index(["district", "category"])["count"]
    prv    = grp[grp["week"] == pw].set_index(["district", "category"])["count"]
    wow    = ((cur - prv) / prv.replace(0, 1) * 100).round(1)
    spikes = wow[wow > 20].sort_values(ascending=False).head(15).reset_index()

    if spikes.empty:
        return html.Div("No critical spikes detected this week.",
                        style={"color": SUCCESS, "padding": "8px", "fontSize": "13px"})

    spikes.columns = ["District", "Category", "WoW %"]
    spikes["Count"] = cur.reindex(
        pd.MultiIndex.from_frame(spikes[["District", "Category"]])).values
    spikes["Priority"] = spikes["WoW %"].apply(
        lambda v: "CRITICAL" if v > 50 else "HIGH" if v > 35 else "MEDIUM")
    spikes["WoW %"] = spikes["WoW %"].apply(lambda v: f"UP {v:.1f}%")

    return dash_table.DataTable(
        data=spikes.to_dict("records"),
        columns=[{"name": c, "id": c} for c in spikes.columns],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": BG_PANEL, "color": ACCENT,
                      "fontWeight": "700", "fontSize": "11px",
                      "borderBottom": f"1px solid {BORDER}",
                      "textTransform": "uppercase", "letterSpacing": "1px"},
        style_cell={"backgroundColor": "transparent", "color": TEXT_PRI,
                    "fontSize": "12px", "border": f"1px solid {BORDER}",
                    "padding": "6px 12px", "textAlign": "left"},
        style_data_conditional=[
            {"if": {"filter_query": '{Priority} = "CRITICAL"'},
             "color": DANGER, "fontWeight": "600"},
            {"if": {"filter_query": '{Priority} = "HIGH"'},
             "color": WARNING},
        ],
        page_size=10, sort_action="native",
    )


@app.callback(
    Output("data-table", "children"),
    Input("dd-district", "value"),
    Input("dd-category", "value"),
)
def update_data_table(district, category):
    fdf = filter_df(district, category, 1)
    out = fdf[["week", "district", "category", "count",
               "resolved", "pending", "resolution_rate"]].copy()
    out["week"] = out["week"].dt.strftime("%Y-%m-%d")
    out = out.rename(columns={
        "week": "Week", "district": "District", "category": "Category",
        "count": "Total", "resolved": "Resolved",
        "pending": "Pending", "resolution_rate": "Resolution %",
    }).sort_values("Total", ascending=False).head(50)

    return dash_table.DataTable(
        data=out.to_dict("records"),
        columns=[{"name": c, "id": c} for c in out.columns],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": BG_PANEL, "color": ACCENT,
                      "fontWeight": "700", "fontSize": "11px",
                      "borderBottom": f"1px solid {BORDER}",
                      "textTransform": "uppercase", "letterSpacing": "1px"},
        style_cell={"backgroundColor": "transparent", "color": TEXT_PRI,
                    "fontSize": "12px", "border": f"1px solid {BORDER}",
                    "padding": "6px 12px", "textAlign": "left",
                    "minWidth": "80px"},
        style_data_conditional=[
            {"if": {"column_id": "Total",
                    "filter_query": "{Total} > 200"},
             "color": DANGER, "fontWeight": "600"},
            {"if": {"column_id": "Resolution %",
                    "filter_query": "{Resolution %} > 75"},
             "color": SUCCESS},
            {"if": {"column_id": "Resolution %",
                    "filter_query": "{Resolution %} < 50"},
             "color": WARNING},
        ],
        page_size=15, sort_action="native", filter_action="native",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
_css_bg      = BG_DARK
_css_card    = BG_CARD
_css_panel   = BG_PANEL
_css_border  = BORDER
_css_accent  = ACCENT
_css_text    = TEXT_PRI

app.index_string = (
    "<!DOCTYPE html><html><head>"
    "{%metas%}<title>{%title%}</title>{%favicon%}{%css%}"
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>"
    "* { box-sizing: border-box; }"
    "body { margin: 0; background: " + _css_bg + "; }"
    "::-webkit-scrollbar { width: 6px; height: 6px; }"
    "::-webkit-scrollbar-track { background: " + _css_card + "; }"
    "::-webkit-scrollbar-thumb { background: " + _css_border + "; border-radius: 3px; }"
    ".Select-control { background-color: " + _css_panel + " !important; border-color: " + _css_border + " !important; }"
    ".Select-value-label, .Select-placeholder { color: " + _css_text + " !important; }"
    ".Select-menu-outer { background-color: " + _css_panel + " !important; border-color: " + _css_border + " !important; }"
    ".Select-option { color: " + _css_text + " !important; }"
    ".Select-option:hover { background: " + _css_accent + "22 !important; }"
    ".rc-slider-track { background-color: " + _css_accent + " !important; }"
    ".rc-slider-handle { border-color: " + _css_accent + " !important; background: " + _css_accent + " !important; }"
    ".dash-spreadsheet-inner td:hover { background: " + _css_accent + "18 !important; }"
    ".tab-content { border: none !important; }"
    "@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }"
    "</style></head><body>"
    "{%app_entry%}"
    "<footer>{%config%}{%scripts%}{%renderer%}</footer>"
    "</body></html>"
)

# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 65)
    print("  Gujarat OSINT Intelligence Dashboard  v2.0")
    print("  Tab 1: Intelligence Dashboard (all 9 charts)")
    print("  Tab 2: Raw OSINT Data Sources (7 sources, 8 rows each)")
    print("  Open: http://127.0.0.1:8050")
    print("=" * 65)
    app.run(debug=True, host="127.0.0.1", port=8050)
