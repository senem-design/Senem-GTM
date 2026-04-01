"""GTM Sales Manager Planner – Streamlit Dashboard"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config – MUST be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GTM Sales Manager Planner",
    layout="wide",
    page_icon="📊",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ── Base ───────────────────────────────────────────────────────────── */
    body, [data-testid="stAppViewContainer"] { background: #f8fafc; }

    /* ── Header bar ────────────────────────────────────────────────────── */
    .gtm-header {
        background: #1e293b;
        color: white;
        padding: 1.4rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
        border-left: 4px solid #3b82f6;
    }
    .gtm-header h1 { color: white; margin: 0; font-size: 1.65rem; font-weight: 700; letter-spacing: -0.3px; }
    .gtm-header p  { color: #94a3b8; margin: 0.3rem 0 0; font-size: 0.88rem; }

    /* ── Section dividers ───────────────────────────────────────────────── */
    .section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin: 1.5rem 0 0.6rem;
        padding-bottom: 0.35rem;
        border-bottom: 2px solid #e2e8f0;
    }

    /* ── Status badges ──────────────────────────────────────────────────── */
    .badge-active   { display:inline-block; background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; border:1px solid #bbf7d0; }
    .badge-inactive { display:inline-block; background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; border:1px solid #fecaca; }

    /* ── Segment colour pills ───────────────────────────────────────────── */
    .seg-enterprise { background:#dbeafe; color:#1e40af; padding:2px 9px; border-radius:20px; font-size:0.75rem; font-weight:600; }
    .seg-mid-market { background:#dcfce7; color:#14532d; padding:2px 9px; border-radius:20px; font-size:0.75rem; font-weight:600; }
    .seg-agency     { background:#ffedd5; color:#9a3412; padding:2px 9px; border-radius:20px; font-size:0.75rem; font-weight:600; }

    /* ── Metric cards ───────────────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    [data-testid="metric-container"] label { color: #64748b; font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    [data-testid="stMetricValue"] { color: #1e293b; font-size: 1.3rem; font-weight: 700; }

    /* ── Quota section card ─────────────────────────────────────────────── */
    .quota-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .quota-card-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #3b82f6;
        margin-bottom: 0.5rem;
    }
    .quota-card-adjusted .quota-card-title { color: #10b981; }

    /* ── Plan card ──────────────────────────────────────────────────────── */
    .plan-card {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        background: #ffffff;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    /* ── Dataframe polish ───────────────────────────────────────────────── */
    [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

    /* ── Sidebar ────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] { background: #1e293b; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label { color: #94a3b8 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FISCAL_MONTHS = [
    date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1),
    date(2026, 5, 1), date(2026, 6, 1), date(2026, 7, 1),
    date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1),
    date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1),
]
MONTH_LABELS = ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan"]

SEGMENTS = ["Enterprise", "Mid Market", "Agency"]
REGIONS  = ["NYC", "LDN"]
CURRENCIES = {"NYC": "USD", "LDN": "GBP"}
FX_RATES   = {"USD": 1.00, "GBP": 1.34}

DATA_PATH = "info/AEs and Managers - Sheet1.csv"

FY26_START = date(2026, 2, 1)            # Start of FY26
EFFECTIVE_UNTIL_DEFAULT = date(2028, 2, 1)  # Default effective-until for all plans

# Default TBH compensation values (USD local variable / annual quota)
DEFAULT_VARIABLE_ENTERPRISE = 120_000    # Enterprise AE base variable
DEFAULT_VARIABLE_STANDARD   = 100_000   # Mid Market / Agency AE base variable
DEFAULT_QUOTA_ENTERPRISE    = 1_166_667  # $140k variable / 12% commission rate
DEFAULT_QUOTA_STANDARD      = 1_000_000  # $120k variable / 12% commission rate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_currency(amount: float) -> str:
    """Format amount as USD ($X,XXX). All outputs are in USD."""
    return f"${amount:,.0f}"


def _clean_money(val: Any) -> float:
    """Strip $, £, commas and convert to float."""
    if pd.isna(val):
        return 0.0
    return float(str(val).replace("$", "").replace("£", "").replace(",", "").strip() or 0)


def _clean_pct(val: Any) -> float:
    """Strip % and convert to fraction (e.g. 12.00% → 0.12)."""
    if pd.isna(val):
        return 0.0
    return float(str(val).replace("%", "").strip() or 0) / 100.0


def _parse_date(val: Any) -> date | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%#m/%#d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AE version helpers
# ---------------------------------------------------------------------------

def _build_version_from_row(row: pd.Series, version_id: int = 0) -> dict:
    """Build a version dict from a CSV AE row."""
    start_d = row["Start Date"]
    # effective_from = earlier of the AE's start date or FY26 start (2026-02-01)
    eff_from = min(start_d, FY26_START) if isinstance(start_d, date) else FY26_START
    return {
        "version_id":        version_id,
        "effective_from":    eff_from,
        "effective_until":   EFFECTIVE_UNTIL_DEFAULT,
        "name":              str(row["AEs"]),
        "segment":           str(row["Segment"]),
        "region":            str(row["Region"]),
        "payment_frequency": str(row.get("Payment Frequency", "Monthly")),
        "plan_period":       str(row.get("Plan period", "Annual")),
        "local_currency":    str(row["Local Currency"]),
        "fx":                float(row["FX"]),
        "local_variable":    float(row["Local Variable"]),
        "usd_variable":      float(row["USD Variable"]),
        "commission_rate":   float(row["Commission Rate (Fixed)"]),
        "usd_quota":         float(row["USD Quota (Annual)"]),
        "start_date":        row["Start Date"],
        "on_plan_date":      row["On Plan Date"],
    }


def _init_ae_versions(ae_df: pd.DataFrame) -> None:
    """Populate st.session_state['ae_versions'] from ae_df (runs once per session)."""
    if "ae_versions" not in st.session_state:
        st.session_state["ae_versions"] = {}
    for _, row in ae_df.iterrows():
        ae_name = str(row["AEs"])
        if ae_name not in st.session_state["ae_versions"]:
            st.session_state["ae_versions"][ae_name] = [
                _build_version_from_row(row, version_id=0)
            ]


def get_current_version(ae_name: str) -> dict | None:
    """Return the active version for today, or the latest version if none covers today."""
    versions = st.session_state["ae_versions"].get(ae_name, [])
    if not versions:
        return None
    today = date.today()
    for v in reversed(versions):
        if v["effective_from"] <= today:
            return v
    return versions[-1]


def ae_version_to_plan_dict(version: dict) -> dict:
    """Convert an AE version dict to the plan AE dict format."""
    return {
        "name":            version["name"],
        "status":          "Started",
        "start_date":      version.get("start_date"),
        "on_plan_date":    version.get("on_plan_date"),
        "segment":         version["segment"],
        "region":          version["region"],
        "currency":        version["local_currency"],
        "fx":              version["fx"],
        "local_variable":  version["local_variable"],
        "usd_variable":    version["usd_variable"],
        "commission_rate": version["commission_rate"],
        "usd_quota":       version["usd_quota"],
    }


# ---------------------------------------------------------------------------
# Ramp schedule
# ---------------------------------------------------------------------------

_RAMP_M3_9 = 1 / 12                    # 8.3333...%
_RAMP_M10_12 = (1 - 0.03 - 7 / 12) / 3  # 12.8889...%


def get_ramp_pct(month_num: int) -> float:
    """Return ramp % for a 1-indexed employment month."""
    if month_num <= 1:
        return 0.0
    elif month_num == 2:
        return 0.03
    elif 3 <= month_num <= 9:
        return _RAMP_M3_9
    elif 10 <= month_num <= 12:
        return _RAMP_M10_12
    else:  # 13+
        return _RAMP_M3_9


def calc_monthly_quota(annual_quota: float, on_plan_date: date, fiscal_month: date) -> float:
    """Quota contribution for a given fiscal month, respecting ramp."""
    if fiscal_month < on_plan_date:
        return 0.0
    delta_months = (
        (fiscal_month.year - on_plan_date.year) * 12
        + (fiscal_month.month - on_plan_date.month)
        + 1
    )
    return annual_quota * get_ramp_pct(delta_months)


def calculate_months_on_plan(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return max(1, min(months, 12))


def plan_status(plan: dict) -> str:
    """Return 'Active' if today falls within the plan period, else 'Inactive'."""
    today = date.today()
    ps = plan.get("plan_start")
    pe = plan.get("plan_end")
    if ps is None or pe is None:
        return "Inactive"
    return "Active" if ps <= today <= pe else "Inactive"


def status_badge_html(status: str) -> str:
    if status == "Active":
        return '<span class="badge-active">&#9679; ACTIVE</span>'
    return '<span class="badge-inactive">&#9679; INACTIVE</span>'


# ---------------------------------------------------------------------------
# Plan metrics
# ---------------------------------------------------------------------------

def calculate_plan_metrics(plan: dict) -> dict:
    aes = plan["aes"]
    months_on_plan = calculate_months_on_plan(plan["plan_start"], plan["plan_end"])
    proration = months_on_plan / 12.0

    plan_start = plan["plan_start"]
    plan_end = plan["plan_end"]

    ae_monthly: dict[str, list[float]] = {}
    for ae in aes:
        monthly = []
        for fm in FISCAL_MONTHS:
            # Only count months within the manager's plan period
            if fm < plan_start or fm > plan_end:
                monthly.append(0.0)
            else:
                monthly.append(calc_monthly_quota(ae["usd_quota"], ae["on_plan_date"], fm))
        ae_monthly[ae["name"]] = monthly

    total_by_month = [
        sum(ae_monthly[ae["name"]][i] for ae in aes)
        for i in range(12)
    ]
    quota_rollup = sum(total_by_month)

    total_quota    = quota_rollup * plan["quota_factor"]
    managed_quota  = total_quota  # rollup already covers only plan-period months

    prorated_variable = plan["variable"] * proration
    base_rate = prorated_variable / managed_quota if managed_quota > 0 else 0.0

    tier1_threshold = managed_quota
    tier1_rate      = base_rate * 1.25
    tier2_threshold = managed_quota * 1.5
    tier2_rate      = base_rate * 1.5

    q1 = sum(total_by_month[0:3])
    q2 = sum(total_by_month[3:6])
    q3 = sum(total_by_month[6:9])
    q4 = sum(total_by_month[9:12])

    q1_adjusted = q1 * plan["quota_factor"]
    q2_adjusted = q2 * plan["quota_factor"]
    q3_adjusted = q3 * plan["quota_factor"]
    q4_adjusted = q4 * plan["quota_factor"]

    # pilot_rate ≈ base_rate * (5/12) ≈ base_rate / 2.4
    # Based on source data: for Charlie Demuth base_rate=1.20%, pilot=0.50% (ratio ≈ 0.4167)
    pilot_rate          = base_rate / 2.4
    contract_break_rate = pilot_rate

    return {
        "ae_monthly":        ae_monthly,
        "total_by_month":    total_by_month,
        "quota_rollup":      quota_rollup,
        "total_quota":       total_quota,
        "managed_quota":     managed_quota,
        "months_on_plan":    months_on_plan,
        "proration":         proration,
        "prorated_variable": prorated_variable,
        "base_rate":         base_rate,
        "tier1_threshold":   tier1_threshold,
        "tier1_rate":        tier1_rate,
        "tier2_threshold":   tier2_threshold,
        "tier2_rate":        tier2_rate,
        "pilot_rate":            pilot_rate,
        "contract_break_rate":   contract_break_rate,
        "q1": q1, "q2": q2, "q3": q3, "q4": q4,
        "q1_adjusted": q1_adjusted,
        "q2_adjusted": q2_adjusted,
        "q3_adjusted": q3_adjusted,
        "q4_adjusted": q4_adjusted,
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (ae_df, manager_df) from the CSV."""
    raw = pd.read_csv(DATA_PATH, dtype=str)

    # Find the "Managers" separator row index
    sep_idx = raw.index[raw.iloc[:, 0].str.strip() == "Managers"].tolist()
    sep = sep_idx[0] if sep_idx else len(raw)

    ae_raw = raw.iloc[:sep].copy()
    mgr_raw = raw.iloc[sep + 1:].copy()

    # ── AEs ──────────────────────────────────────────────────────────────
    ae_raw.columns = raw.columns
    ae_raw = ae_raw[
        ae_raw.iloc[:, 0].notna()
        & (ae_raw.iloc[:, 0].str.strip() != "")
        & (ae_raw.iloc[:, 0].str.strip() != "AEs")
    ].copy()

    ae_raw["Segment"] = (
        ae_raw["Segment"]
        .str.strip()
        .str.replace("Enteprise", "Enterprise", regex=False)
    )
    ae_raw["Start Date"]   = ae_raw["Start Date"].apply(_parse_date)
    ae_raw["On Plan Date"] = ae_raw["On Plan Date"].apply(_parse_date)
    ae_raw["FX"]           = ae_raw["FX"].apply(lambda v: float(str(v).strip()) if pd.notna(v) else 1.0)
    ae_raw["Local Variable"] = ae_raw["Local Variable"].apply(_clean_money)
    ae_raw["USD Variable"]   = ae_raw["USD Variable"].apply(_clean_money)
    ae_raw["Commission Rate (Fixed)"] = ae_raw["Commission Rate (Fixed)"].apply(_clean_pct)
    ae_raw["USD Quota (Annual)"]      = ae_raw["USD Quota (Annual)"].apply(_clean_money)

    ae_df = ae_raw.reset_index(drop=True)

    # ── Managers ─────────────────────────────────────────────────────────
    mgr_raw.columns = raw.columns
    mgr_raw = mgr_raw[
        mgr_raw.iloc[:, 0].notna()
        & (mgr_raw.iloc[:, 0].str.strip() != "")
    ].copy()

    mgr_raw["Segment"] = (
        mgr_raw["Segment"]
        .str.strip()
        .str.replace("Enteprise", "Enterprise", regex=False)
    )
    mgr_raw["Start Date"]   = mgr_raw["Start Date"].apply(_parse_date)
    mgr_raw["On Plan Date"] = mgr_raw["On Plan Date"].apply(_parse_date)

    mgr_df = mgr_raw[["AEs", "Start Date", "On Plan Date", "Segment", "Region", "Local Currency"]].reset_index(drop=True)
    mgr_df = mgr_df.rename(columns={"AEs": "Name", "Local Currency": "Currency"})

    return ae_df, mgr_df


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def build_excel(plan: dict, metrics: dict) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # ── Sheet 1: Compensation Plan Summary ───────────────────────────
        summary_rows: list[tuple] = []

        # Header
        mgr_name = plan["manager_name"]
        summary_rows.append((f"{mgr_name} — FY26 Compensation Plan", ""))
        summary_rows.append((
            f"1st Line Manager — {plan['segment']} | Currency: USD", ""
        ))
        summary_rows.append(("", ""))

        # Plan Parameters
        summary_rows.append(("PLAN PARAMETERS", ""))
        summary_rows.append(("Plan Start Date",    str(plan["plan_start"])))
        summary_rows.append(("Plan End Date",       str(plan["plan_end"])))
        summary_rows.append(("Months on Plan",      metrics["months_on_plan"]))
        summary_rows.append(("Proration",           f"{metrics['proration']:.0%}"))
        summary_rows.append(("Base Salary",         fmt_currency(plan["base_salary"])))
        summary_rows.append(("Annual Variable",     fmt_currency(plan["variable"])))
        summary_rows.append(("Prorated Variable",   fmt_currency(metrics["prorated_variable"])))
        summary_rows.append(("Quota Rollup",        fmt_currency(metrics["quota_rollup"])))
        summary_rows.append(("Quota Factor",        f"{plan['quota_factor']}x"))
        summary_rows.append((
            "Quota Rollup (adjusted for Quota Factor)",
            fmt_currency(metrics["total_quota"]),
        ))
        summary_rows.append(("Base Commission Rate", f"{metrics['base_rate']:.2%}"))
        summary_rows.append(("", ""))

        # Accelerators
        br_pct = metrics["base_rate"] * 100
        t1_pct = metrics["tier1_rate"] * 100
        t2_pct = metrics["tier2_rate"] * 100
        pilot_pct = metrics["pilot_rate"] * 100
        cb_pct    = metrics["contract_break_rate"] * 100

        summary_rows.append(("ACCELERATORS", ""))
        summary_rows.append(("Tier", "Threshold to Quota", "Rate Multiplier", "Quota Threshold", "Actual Rate"))
        summary_rows.append(("Standard",       "0%",    "1.00x", "$0",                          f"{br_pct:.2f}%"))
        summary_rows.append(("Tier 1",         "100%",  "1.25x", fmt_currency(metrics["tier1_threshold"]), f"{t1_pct:.2f}%"))
        summary_rows.append(("Tier 2",         "150%",  "1.50x", fmt_currency(metrics["tier2_threshold"]), f"{t2_pct:.2f}%"))
        summary_rows.append(("Pilot Rate",     "",      "",       "",                            f"{pilot_pct:.2f}%"))
        summary_rows.append(("Contract Break", "",      "",       "",                            f"{cb_pct:.2f}%"))
        summary_rows.append(("", ""))

        # Quarterly Quota (Adjusted)
        summary_rows.append(("QUARTERLY QUOTA", "Adjusted for Quota Factor"))
        summary_rows.append(("Quarter", "Quota"))
        summary_rows.append(("Q1", fmt_currency(metrics["q1_adjusted"])))
        summary_rows.append(("Q2", fmt_currency(metrics["q2_adjusted"])))
        summary_rows.append(("Q3", fmt_currency(metrics["q3_adjusted"])))
        summary_rows.append(("Q4", fmt_currency(metrics["q4_adjusted"])))
        summary_rows.append(("Total", fmt_currency(metrics["total_quota"])))
        summary_rows.append(("", ""))

        # Team Roster
        summary_rows.append(("TEAM ROSTER", ""))
        summary_rows.append(("#", "Rep Name", "Status", "Start Date", "Plan Date"))
        for idx, ae in enumerate(plan["aes"], start=1):
            summary_rows.append((
                idx,
                ae["name"],
                ae.get("status", "Started"),
                str(ae.get("start_date", "")),
                str(ae.get("on_plan_date", "")),
            ))
        summary_rows.append(("EOY FY26 Team Count", len(plan["aes"])))

        # Pad rows to EXCEL_SUMMARY_COLS columns (matches the widest row: accelerator header)
        EXCEL_SUMMARY_COLS = 5
        padded = [r + ("",) * (EXCEL_SUMMARY_COLS - len(r)) if len(r) < EXCEL_SUMMARY_COLS else r for r in summary_rows]
        summary_df = pd.DataFrame(padded, columns=["A", "B", "C", "D", "E"])
        summary_df.to_excel(writer, sheet_name="Compensation Plan", index=False, header=False)

        # ── Sheet 2: Monthly Rollup Detail ───────────────────────────────
        detail_rows = []
        for ae in plan["aes"]:
            monthly = metrics["ae_monthly"].get(ae["name"], [0.0] * 12)
            row: dict[str, Any] = {
                "Name":            ae["name"],
                "Status":          ae.get("status", "Started"),
                "Start Date":      ae["start_date"],
                "On Plan Date":    ae["on_plan_date"],
                "Segment":         ae["segment"],
                "Region":          ae["region"],
                "USD Variable":    ae["usd_variable"],
                "Commission Rate": ae["commission_rate"],
                "Annual Quota":    ae["usd_quota"],
            }
            for lbl, val in zip(MONTH_LABELS, monthly):
                row[lbl] = val
            row["Total"] = sum(monthly)
            detail_rows.append(row)

        detail_df = pd.DataFrame(detail_rows)
        detail_df.to_excel(writer, sheet_name="Monthly Rollup", index=False)

    return output.getvalue()


# ---------------------------------------------------------------------------
# AE → plan dict helper
# ---------------------------------------------------------------------------

def ae_row_to_dict(row: pd.Series) -> dict:
    return {
        "name":            str(row["AEs"]),
        "status":          "Started",
        "start_date":      row["Start Date"],
        "on_plan_date":    row["On Plan Date"],
        "segment":         str(row["Segment"]),
        "region":          str(row["Region"]),
        "currency":        str(row["Local Currency"]),
        "fx":              float(row["FX"]),
        "local_variable":  float(row["Local Variable"]),
        "usd_variable":    float(row["USD Variable"]),
        "commission_rate": float(row["Commission Rate (Fixed)"]),
        "usd_quota":       float(row["USD Quota (Annual)"]),
    }


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        "plans":              {},
        "tbh_counter":        {},
        "builder_selected_aes": [],
        "builder_tbhs":       [],
        "ae_versions":        {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
ae_df, mgr_df = load_data()
_init_ae_versions(ae_df)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📊 GTM Planner")
    st.markdown("---")

    # Global filters (affect Roster tab)
    st.markdown("### 🔍 Roster Filters")
    all_segs = sorted(ae_df["Segment"].dropna().unique().tolist())
    all_regs = sorted(ae_df["Region"].dropna().unique().tolist())

    sel_segments = st.multiselect("Segment", all_segs, default=all_segs, key="sb_seg")
    sel_regions  = st.multiselect("Region",  all_regs, default=all_regs,  key="sb_reg")

    st.markdown("---")
    st.markdown("### 📈 Quick Stats")
    c1, c2 = st.columns(2)
    c1.metric("AEs",      len(ae_df))
    c2.metric("Managers", len(mgr_df))
    st.metric("Plans Saved", len(st.session_state.plans))


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="gtm-header">
      <h1>📊 GTM Sales Manager Planner</h1>
      <p>FY2026 · Feb 1, 2026 – Jan 31, 2027 · Quota, Ramp & Compensation Planning</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_roster, tab_builder, tab_overview = st.tabs(
    ["📋 Roster", "🏗️ Plan Builder", "📊 Plans Overview"]
)

# ===========================================================================
# TAB 1 – ROSTER
# ===========================================================================
with tab_roster:
    # Apply sidebar filters
    filtered_ae = ae_df[
        ae_df["Segment"].isin(sel_segments) & ae_df["Region"].isin(sel_regions)
    ].copy()

    # Summary metrics
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total AEs (filtered)", len(filtered_ae))
    col_m2.metric(
        "Enterprise",
        len(filtered_ae[filtered_ae["Segment"] == "Enterprise"]),
    )
    col_m3.metric(
        "Mid Market",
        len(filtered_ae[filtered_ae["Segment"] == "Mid Market"]),
    )
    col_m4.metric(
        "Agency",
        len(filtered_ae[filtered_ae["Segment"] == "Agency"]),
    )

    st.markdown("### 👥 Account Executives")

    # Build display from current versions (reflects any overrides)
    current_version_rows = []
    for _, row in filtered_ae.iterrows():
        ae_name = str(row["AEs"])
        version = get_current_version(ae_name)
        if version:
            n_ver = len(st.session_state["ae_versions"].get(ae_name, []))
            current_version_rows.append({
                "AEs":                   ae_name,
                "Segment":               version["segment"],
                "Region":                version["region"],
                "Start Date":            str(version.get("start_date", "")),
                "On Plan Date":          str(version.get("on_plan_date", "")),
                "Local Currency":        version["local_currency"],
                "FX":                    version["fx"],
                "Local Variable":        f"{version['local_variable']:,.0f}",
                "USD Variable":          fmt_currency(version["usd_variable"]),
                "Commission Rate":       f"{version['commission_rate']:.2%}",
                "USD Quota (Annual)":    fmt_currency(version["usd_quota"]),
                "Effective From":        str(version["effective_from"]),
                "Effective Until":       str(version["effective_until"]),
                "Versions":              n_ver,
            })

    disp_df = pd.DataFrame(current_version_rows) if current_version_rows else pd.DataFrame()
    st.dataframe(
        disp_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Segment":    st.column_config.TextColumn("Segment"),
            "Commission Rate": st.column_config.TextColumn("Commission %"),
            "Versions":   st.column_config.NumberColumn("Versions", format="%d"),
        },
    )

    # ── Per-AE Edit section ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ✏️ Edit AE Records")
    st.caption(
        "Click **✏️ Edit** to override any field for an AE. "
        "Edits create a new versioned plan; the original CSV is not modified."
    )

    for _, row in filtered_ae.iterrows():
        ae_name = str(row["AEs"])
        current_v = get_current_version(ae_name)
        if not current_v:
            continue

        versions = st.session_state["ae_versions"].get(ae_name, [])
        n_ver = len(versions)
        ver_badge = f"  ·  **{n_ver} versions**" if n_ver > 1 else ""

        col_info, col_btn = st.columns([6, 1])
        col_info.markdown(
            f"**{ae_name}** · {current_v['segment']} · {current_v['region']}"
            f" · Eff: {current_v['effective_from']} → {current_v['effective_until']}"
            f"{ver_badge}"
        )
        if col_btn.button("✏️ Edit", key=f"edit_btn_{ae_name}"):
            st.session_state[f"ae_edit_open_{ae_name}"] = not st.session_state.get(
                f"ae_edit_open_{ae_name}", False
            )

        if st.session_state.get(f"ae_edit_open_{ae_name}", False):
            with st.container():
                st.markdown(f"**Editing: {ae_name}**")
                ec1, ec2, ec3 = st.columns(3)

                with ec1:
                    new_name = st.text_input(
                        "Name", value=current_v["name"], key=f"edit_name_{ae_name}"
                    )
                    new_seg = st.selectbox(
                        "Segment", SEGMENTS,
                        index=SEGMENTS.index(current_v["segment"]) if current_v["segment"] in SEGMENTS else 0,
                        key=f"edit_seg_{ae_name}",
                    )
                    new_reg = st.selectbox(
                        "Region", REGIONS,
                        index=REGIONS.index(current_v["region"]) if current_v["region"] in REGIONS else 0,
                        key=f"edit_reg_{ae_name}",
                    )
                    new_pay_freq = st.text_input(
                        "Payment Frequency",
                        value=current_v.get("payment_frequency", "Monthly"),
                        key=f"edit_pay_{ae_name}",
                    )
                    new_plan_period = st.text_input(
                        "Plan Period",
                        value=current_v.get("plan_period", "Annual"),
                        key=f"edit_period_{ae_name}",
                    )

                with ec2:
                    new_currency = st.selectbox(
                        "Local Currency", ["USD", "GBP"],
                        index=0 if current_v["local_currency"] == "USD" else 1,
                        key=f"edit_cur_{ae_name}",
                    )
                    new_fx = st.number_input(
                        "FX Rate", min_value=0.0001, value=float(current_v["fx"]),
                        step=0.01, format="%.4f", key=f"edit_fx_{ae_name}",
                    )
                    new_local_var = st.number_input(
                        "Local Variable", min_value=0.0,
                        value=float(current_v["local_variable"]),
                        step=5000.0, format="%.0f", key=f"edit_local_var_{ae_name}",
                    )
                    new_usd_var = st.number_input(
                        "USD Variable", min_value=0.0,
                        value=float(current_v["usd_variable"]),
                        step=5000.0, format="%.0f", key=f"edit_usd_var_{ae_name}",
                    )

                with ec3:
                    new_cr = st.number_input(
                        "Commission Rate %", min_value=0.0, max_value=100.0,
                        value=float(current_v["commission_rate"] * 100),
                        step=0.5, format="%.2f", key=f"edit_cr_{ae_name}",
                    )
                    new_quota = st.number_input(
                        "USD Quota (Annual)", min_value=0.0,
                        value=float(current_v["usd_quota"]),
                        step=10000.0, format="%.0f", key=f"edit_quota_{ae_name}",
                    )
                    new_start = st.date_input(
                        "Start Date",
                        value=current_v.get("start_date") or date.today(),
                        key=f"edit_start_{ae_name}",
                    )
                    new_on_plan = st.date_input(
                        "On Plan Date",
                        value=current_v.get("on_plan_date") or date.today(),
                        key=f"edit_on_plan_{ae_name}",
                    )

                new_eff_from = st.date_input(
                    "🗓️ New Effective As Of (start of this new version)",
                    value=date.today(),
                    key=f"edit_eff_{ae_name}",
                )

                btn_save_col, btn_cancel_col = st.columns(2)
                if btn_save_col.button(
                    "💾 Save New Version", key=f"save_ver_{ae_name}", type="primary"
                ):
                    new_version = {
                        "version_id":        n_ver,
                        "effective_from":    new_eff_from,
                        "effective_until":   EFFECTIVE_UNTIL_DEFAULT,
                        "name":              new_name,
                        "segment":           new_seg,
                        "region":            new_reg,
                        "payment_frequency": new_pay_freq,
                        "plan_period":       new_plan_period,
                        "local_currency":    new_currency,
                        "fx":                new_fx,
                        "local_variable":    new_local_var,
                        "usd_variable":      new_usd_var,
                        "commission_rate":   new_cr / 100.0,
                        "usd_quota":         new_quota,
                        "start_date":        new_start,
                        "on_plan_date":      new_on_plan,
                    }
                    # Update previous version's effective_until
                    st.session_state["ae_versions"][ae_name][-1]["effective_until"] = (
                        new_eff_from - timedelta(days=1)
                    )
                    st.session_state["ae_versions"][ae_name].append(new_version)
                    st.session_state[f"ae_edit_open_{ae_name}"] = False
                    st.success(
                        f"✅ New version saved for **{ae_name}** "
                        f"(effective {new_eff_from})"
                    )
                    st.rerun()

                if btn_cancel_col.button("❌ Cancel", key=f"cancel_ver_{ae_name}"):
                    st.session_state[f"ae_edit_open_{ae_name}"] = False
                    st.rerun()

                # Version history (only show when there are multiple versions)
                if n_ver > 1:
                    st.markdown("---")
                    st.markdown("**📜 Version History**")
                    for v in versions:
                        is_current = v.get("version_id") == current_v.get("version_id")
                        indicator = "🟢 **(current)**" if is_current else "⚪"
                        st.markdown(
                            f"{indicator} "
                            f"**v{v['version_id'] + 1}** · "
                            f"Effective: `{v['effective_from']}` → `{v['effective_until']}` · "
                            f"Segment: {v['segment']} · Region: {v['region']} · "
                            f"USD Variable: {fmt_currency(v['usd_variable'])} · "
                            f"Quota: {fmt_currency(v['usd_quota'])}"
                        )

        st.divider()

    # Segment chart
    seg_counts = filtered_ae["Segment"].value_counts().reset_index()
    seg_counts.columns = ["Segment", "Count"]
    seg_colors = {"Enterprise": "#1565c0", "Mid Market": "#2e7d32", "Agency": "#e65100"}

    col_ch1, col_ch2 = st.columns(2)
    with col_ch1:
        fig_seg = px.pie(
            seg_counts, names="Segment", values="Count",
            title="AEs by Segment",
            color="Segment",
            color_discrete_map=seg_colors,
        )
        fig_seg.update_layout(margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_seg, use_container_width=True)

    with col_ch2:
        reg_counts = filtered_ae["Region"].value_counts().reset_index()
        reg_counts.columns = ["Region", "Count"]
        fig_reg = px.bar(
            reg_counts, x="Region", y="Count",
            title="AEs by Region",
            color="Region",
            color_discrete_sequence=["#1a4a8a", "#0d7c6e"],
        )
        fig_reg.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_reg, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🏆 Managers")

    mgr_display = mgr_df.copy()
    mgr_display["Start Date"]   = mgr_display["Start Date"].astype(str)
    mgr_display["On Plan Date"] = mgr_display["On Plan Date"].astype(str)
    st.dataframe(mgr_display, use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 2 – PLAN BUILDER
# ===========================================================================
with tab_builder:
    st.markdown("### Plan Builder")

    # ── Manager Details ────────────────────────────────────────────────────
    with st.expander("Manager Details", expanded=True):
        col_md1, col_md2 = st.columns(2)

        with col_md1:
            existing_managers = mgr_df["Name"].tolist() + ["New Manager..."]
            selected_mgr = st.selectbox(
                "Manager Name", existing_managers, key="builder_mgr_select"
            )
            if selected_mgr == "New Manager...":
                manager_name = st.text_input("Enter Manager Name", key="builder_mgr_name_input")
            else:
                manager_name = selected_mgr
                # Pre-fill segment/region from mgr_df
                mgr_row = mgr_df[mgr_df["Name"] == selected_mgr].iloc[0] if len(
                    mgr_df[mgr_df["Name"] == selected_mgr]
                ) > 0 else None

            base_salary = st.number_input(
                "Base Salary (USD)", min_value=0.0, value=150000.0,
                step=5000.0, format="%.0f", key="builder_base_salary"
            )
            variable = st.number_input(
                "Variable Compensation (USD)", min_value=0.0, value=100000.0,
                step=5000.0, format="%.0f", key="builder_variable"
            )

        with col_md2:
            default_seg_idx = 0
            default_reg_idx = 0
            if selected_mgr != "New Manager..." and mgr_row is not None:
                seg_val = str(mgr_row.get("Segment", "Enterprise"))
                reg_val = str(mgr_row.get("Region", "NYC"))
                default_seg_idx = SEGMENTS.index(seg_val) if seg_val in SEGMENTS else 0
                default_reg_idx = REGIONS.index(reg_val) if reg_val in REGIONS else 0

            plan_segment = st.selectbox(
                "Segment", SEGMENTS, index=default_seg_idx, key="builder_segment"
            )
            plan_region = st.selectbox(
                "Region", REGIONS, index=default_reg_idx, key="builder_region"
            )
            plan_currency = CURRENCIES[plan_region]
            plan_fx       = FX_RATES[plan_currency]

            quota_factor = st.number_input(
                "Quota Factor", min_value=1.0, max_value=3.0, value=1.25,
                step=0.05, format="%.2f", key="builder_quota_factor"
            )

        col_pd1, col_pd2 = st.columns(2)
        with col_pd1:
            plan_start = st.date_input(
                "Plan Start Date", value=date(2026, 3, 1), key="builder_plan_start"
            )
        with col_pd2:
            plan_end = st.date_input(
                "Plan End Date", value=date(2027, 1, 31), key="builder_plan_end"
            )

    # ── Assign AEs ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 👤 Assign AEs from Roster")

    ae_names = ae_df["AEs"].tolist()
    selected_ae_names = st.multiselect(
        "Select AEs to include in this plan",
        ae_names,
        default=st.session_state["builder_selected_aes"],
        key="builder_ae_multiselect",
    )
    st.session_state["builder_selected_aes"] = selected_ae_names

    # ── Version picker (shown only for AEs with multiple versions) ─────────
    selected_ae_versions: dict[str, dict] = {}
    aes_with_multiple = [
        n for n in selected_ae_names
        if len(st.session_state["ae_versions"].get(n, [])) > 1
    ]
    if aes_with_multiple:
        st.markdown("##### 📅 Version Selection")
        st.caption("These AEs have multiple plan versions — select which one to use:")
        for ae_name in aes_with_multiple:
            ae_vers = st.session_state["ae_versions"].get(ae_name, [])
            ver_labels = [
                f"v{v['version_id'] + 1}: {v['effective_from']} → {v['effective_until']}"
                f"  |  {v['segment']} · {v['region']}"
                f"  |  Quota: {fmt_currency(v['usd_quota'])}"
                for v in ae_vers
            ]
            cur_v = get_current_version(ae_name)
            default_idx = (
                ae_vers.index(cur_v)
                if cur_v and cur_v in ae_vers
                else len(ae_vers) - 1
            )
            sel_idx = st.selectbox(
                ae_name,
                range(len(ae_vers)),
                format_func=lambda i, vl=ver_labels: vl[i],
                index=default_idx,
                key=f"version_picker_{ae_name}",
            )
            selected_ae_versions[ae_name] = ae_vers[sel_idx]

    # ── TBH Quick-Add ──────────────────────────────────────────────────────
    st.markdown("#### ➕ Add TBH Placeholders")
    tbh_combos = [
        ("Enterprise", "NYC"), ("Enterprise", "LDN"),
        ("Mid Market", "NYC"), ("Mid Market", "LDN"),
        ("Agency",     "NYC"), ("Agency",     "LDN"),
    ]

    tbh_cols = st.columns(len(tbh_combos))
    for col, (seg, reg) in zip(tbh_cols, tbh_combos):
        label = f"{seg[:3]} {reg}"
        if col.button(f"+ {label}", key=f"tbh_btn_{seg}_{reg}"):
            key = f"{seg}_{reg}"
            st.session_state["tbh_counter"][key] = (
                st.session_state["tbh_counter"].get(key, 0) + 1
            )
            num = st.session_state["tbh_counter"][key]
            cur = CURRENCIES[reg]
            fx  = FX_RATES[cur]
            default_local_var = DEFAULT_VARIABLE_ENTERPRISE if seg == "Enterprise" else DEFAULT_VARIABLE_STANDARD
            default_quota     = DEFAULT_QUOTA_ENTERPRISE if seg == "Enterprise" else DEFAULT_QUOTA_STANDARD

            st.session_state["builder_tbhs"].append({
                "name":            f"TBH – {seg} {reg} #{num}",
                "status":          "TBH",
                "segment":         seg,
                "region":          reg,
                "currency":        cur,
                "fx":              fx,
                "local_variable":  float(default_local_var),
                "usd_variable":    float(default_local_var) * fx,
                "commission_rate": 0.12,
                "usd_quota":       float(default_quota),
                "start_month_idx": 0,  # index into FISCAL_MONTHS
            })

    # ── TBH editable list ─────────────────────────────────────────────────
    if st.session_state["builder_tbhs"]:
        st.markdown("##### TBH Placeholders")
        tbhs_to_remove = []

        for i, tbh in enumerate(st.session_state["builder_tbhs"]):
            with st.expander(f"🔲 {tbh['name']}", expanded=False):
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    new_name = st.text_input(
                        "Name", value=tbh["name"], key=f"tbh_name_{i}"
                    )
                    new_seg = st.selectbox(
                        "Segment", SEGMENTS,
                        index=SEGMENTS.index(tbh["segment"]) if tbh["segment"] in SEGMENTS else 0,
                        key=f"tbh_seg_{i}",
                    )
                with tc2:
                    new_reg = st.selectbox(
                        "Region", REGIONS,
                        index=REGIONS.index(tbh["region"]) if tbh["region"] in REGIONS else 0,
                        key=f"tbh_reg_{i}",
                    )
                    new_start_idx = st.selectbox(
                        "Start Month",
                        list(range(len(MONTH_LABELS))),
                        format_func=lambda x: MONTH_LABELS[x],
                        index=tbh.get("start_month_idx", 0),
                        key=f"tbh_start_{i}",
                    )
                with tc3:
                    new_local_var = st.number_input(
                        "Local Variable", min_value=0.0,
                        value=float(tbh["local_variable"]),
                        step=5000.0, format="%.0f", key=f"tbh_lv_{i}",
                    )
                    new_cr = st.number_input(
                        "Commission Rate %", min_value=0.0, max_value=100.0,
                        value=float(tbh["commission_rate"] * 100),
                        step=0.5, format="%.2f", key=f"tbh_cr_{i}",
                    )

                if st.button("🗑️ Remove", key=f"tbh_remove_{i}"):
                    tbhs_to_remove.append(i)
                else:
                    new_cur = CURRENCIES[new_reg]
                    new_fx  = FX_RATES[new_cur]
                    new_usd_var = new_local_var * new_fx
                    # Derive annual quota: usd_variable / commission_rate
                    new_cr_frac = new_cr / 100.0
                    new_quota = new_usd_var / new_cr_frac if new_cr_frac > 0 else 0.0
                    on_plan = FISCAL_MONTHS[new_start_idx]

                    st.session_state["builder_tbhs"][i] = {
                        "name":            new_name,
                        "status":          "TBH",
                        "segment":         new_seg,
                        "region":          new_reg,
                        "currency":        new_cur,
                        "fx":              new_fx,
                        "local_variable":  new_local_var,
                        "usd_variable":    new_usd_var,
                        "commission_rate": new_cr_frac,
                        "usd_quota":       new_quota,
                        "start_month_idx": new_start_idx,
                        "start_date":      on_plan,
                        "on_plan_date":    on_plan,
                    }

        for idx in sorted(tbhs_to_remove, reverse=True):
            st.session_state["builder_tbhs"].pop(idx)

    # ── Assemble current AE list ───────────────────────────────────────────
    plan_aes: list[dict] = []

    for ae_name in selected_ae_names:
        # Use explicitly selected version, or fall back to current version
        if ae_name in selected_ae_versions:
            version = selected_ae_versions[ae_name]
        else:
            version = get_current_version(ae_name)

        if version:
            plan_aes.append(ae_version_to_plan_dict(version))
        else:
            # Fallback: read directly from ae_df
            rows = ae_df[ae_df["AEs"] == ae_name]
            if not rows.empty:
                plan_aes.append(ae_row_to_dict(rows.iloc[0]))

    for tbh in st.session_state["builder_tbhs"]:
        tbh_dict = dict(tbh)
        # Ensure start_date / on_plan_date set
        if "on_plan_date" not in tbh_dict or tbh_dict.get("on_plan_date") is None:
            idx = tbh_dict.get("start_month_idx", 0)
            tbh_dict["on_plan_date"] = FISCAL_MONTHS[idx]
            tbh_dict["start_date"]   = FISCAL_MONTHS[idx]
        plan_aes.append(tbh_dict)

    # ── Live Preview ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Live Preview")

    if not plan_aes:
        st.info("Add AEs or TBHs above to see the quota preview.")
    else:
        tmp_plan = {
            "manager_name": manager_name or "—",
            "base_salary":  base_salary,
            "variable":     variable,
            "segment":      plan_segment,
            "region":       plan_region,
            "currency":     plan_currency,
            "fx_rate":      plan_fx,
            "plan_start":   plan_start,
            "plan_end":     plan_end,
            "quota_factor": quota_factor,
            "aes":          plan_aes,
        }
        metrics = calculate_plan_metrics(tmp_plan)

        # ── AE quota table ─────────────────────────────────────────────────
        table_rows = []
        for ae in plan_aes:
            monthly = metrics["ae_monthly"].get(ae["name"], [0.0] * 12)
            row: dict[str, Any] = {
                "Name":       ae["name"],
                "Status":     ae.get("status", "Started"),
                "Segment":    ae["segment"],
                "Region":     ae["region"],
                "Annual Quota": fmt_currency(ae["usd_quota"]),
            }
            for lbl, val in zip(MONTH_LABELS, monthly):
                row[lbl] = fmt_currency(val) if val > 0 else "—"
            row["Total"] = fmt_currency(sum(monthly))
            table_rows.append(row)

        preview_df = pd.DataFrame(table_rows)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        # ── Monthly bar chart ──────────────────────────────────────────────
        chart_data = pd.DataFrame({
            "Month": MONTH_LABELS,
            "Quota": metrics["total_by_month"],
        })
        fig_bar = px.bar(
            chart_data, x="Month", y="Quota",
            title="Monthly Quota Contribution (Team Total)",
            color_discrete_sequence=["#1a4a8a"],
            text_auto=".2s",
        )
        fig_bar.update_layout(
            yaxis_tickformat="$,.0f",
            margin=dict(t=40, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Summary metrics ────────────────────────────────────────────────
        _status = plan_status(tmp_plan)
        st.markdown(
            f"<div class='section-title'>Plan Metrics &nbsp; {status_badge_html(_status)}</div>",
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("Base Salary",       fmt_currency(base_salary))
        m2.metric("Annual Variable",   fmt_currency(variable))
        m3.metric("Prorated Variable", fmt_currency(metrics["prorated_variable"]))

        m4, m5, m6 = st.columns(3)
        m4.metric("Months on Plan",       metrics["months_on_plan"])
        m5.metric("Proration",            f"{metrics['proration']:.0%}")
        m6.metric("Base Commission Rate", f"{metrics['base_rate']:.2%}")

        # ── Quarterly Quota – Rollup (before factor) ───────────────────────
        st.markdown(
            "<div class='section-title'>Quarterly Quota — Rollup (before Quota Factor)</div>",
            unsafe_allow_html=True,
        )
        qa, qb, qc, qd, qt = st.columns(5)
        qa.metric("Q1 (Feb–Apr)", fmt_currency(metrics["q1"]))
        qb.metric("Q2 (May–Jul)", fmt_currency(metrics["q2"]))
        qc.metric("Q3 (Aug–Oct)", fmt_currency(metrics["q3"]))
        qd.metric("Q4 (Nov–Jan)", fmt_currency(metrics["q4"]))
        qt.metric("Total Rollup", fmt_currency(metrics["quota_rollup"]))

        # ── Quarterly Quota – Adjusted (after factor) ──────────────────────
        st.markdown(
            f"<div class='section-title'>Quarterly Quota — Adjusted for Quota Factor ({quota_factor}×)</div>",
            unsafe_allow_html=True,
        )
        ra, rb, rc, rd, rt = st.columns(5)
        ra.metric("Q1 (Feb–Apr)", fmt_currency(metrics["q1_adjusted"]))
        rb.metric("Q2 (May–Jul)", fmt_currency(metrics["q2_adjusted"]))
        rc.metric("Q3 (Aug–Oct)", fmt_currency(metrics["q3_adjusted"]))
        rd.metric("Q4 (Nov–Jan)", fmt_currency(metrics["q4_adjusted"]))
        rt.metric("Total Quota",  fmt_currency(metrics["total_quota"]))

        st.markdown(
            "<div class='section-title'>Accelerator Tiers</div>",
            unsafe_allow_html=True,
        )
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Tier 1 Threshold", fmt_currency(metrics["tier1_threshold"]),
                  delta=f"Rate: {metrics['tier1_rate']:.2%}")
        t2.metric("Tier 2 Threshold", fmt_currency(metrics["tier2_threshold"]),
                  delta=f"Rate: {metrics['tier2_rate']:.2%}")
        t3.metric("Pilot Rate",          f"{metrics['pilot_rate']:.2%}")
        t4.metric("Contract Break Rate", f"{metrics['contract_break_rate']:.2%}")

    # ── Save Plan ──────────────────────────────────────────────────────────
    st.markdown("---")
    col_save, col_clear = st.columns([2, 1])
    with col_save:
        if st.button("💾 Save Plan", type="primary", use_container_width=True):
            if not manager_name:
                st.error("Please enter a manager name before saving.")
            elif not plan_aes:
                st.warning("Add at least one AE or TBH before saving.")
            else:
                st.session_state.plans[manager_name] = {
                    "manager_name": manager_name,
                    "base_salary":  base_salary,
                    "variable":     variable,
                    "segment":      plan_segment,
                    "region":       plan_region,
                    "currency":     plan_currency,
                    "fx_rate":      plan_fx,
                    "plan_start":   plan_start,
                    "plan_end":     plan_end,
                    "quota_factor": quota_factor,
                    "aes":          plan_aes,
                }
                st.success(f"✅ Plan saved for **{manager_name}**!")
                # Reset builder
                st.session_state["builder_selected_aes"] = []
                st.session_state["builder_tbhs"] = []

    with col_clear:
        if st.button("🗑️ Clear Builder", use_container_width=True):
            st.session_state["builder_selected_aes"] = []
            st.session_state["builder_tbhs"] = []
            st.rerun()


# ===========================================================================
# TAB 3 – PLANS OVERVIEW
# ===========================================================================
with tab_overview:
    st.markdown("### Saved Plans Overview")

    if not st.session_state.plans:
        st.info("No plans saved yet. Use the **Plan Builder** tab to create and save a plan.")
    else:
        plans_list = list(st.session_state.plans.items())

        # Aggregate chart across all plans
        all_totals = [0.0] * 12
        for _pname, _plan in plans_list:
            _m = calculate_plan_metrics(_plan)
            for i in range(12):
                all_totals[i] += _m["total_by_month"][i]

        agg_df = pd.DataFrame({"Month": MONTH_LABELS, "Total Quota": all_totals})
        fig_agg = px.bar(
            agg_df, x="Month", y="Total Quota",
            title="Aggregate Monthly Quota – All Plans",
            color_discrete_sequence=["#0d7c6e"],
            text_auto=".2s",
        )
        fig_agg.update_layout(yaxis_tickformat="$,.0f", margin=dict(t=40, b=10))
        st.plotly_chart(fig_agg, use_container_width=True)

        st.markdown("---")

        for plan_name, plan in plans_list:
            metrics = calculate_plan_metrics(plan)
            _status = plan_status(plan)
            _badge  = status_badge_html(_status)

            with st.expander(
                f"{plan_name}  ·  {plan['segment']}  ·  {plan['region']}  ·  "
                f"{len(plan['aes'])} AEs  ·  "
                f"Total Quota: {fmt_currency(metrics['total_quota'])}",
                expanded=False,
            ):
                ov1, ov2, ov3, ov4 = st.columns(4)
                ov1.metric("Manager",   plan_name)
                ov2.metric("Segment",   plan["segment"])
                ov3.metric("Region",    plan["region"])
                ov4.metric("Team Size", len(plan["aes"]))

                st.markdown(
                    f"<div style='margin-bottom:0.75rem;'>"
                    f"<strong>Status:</strong> &nbsp; {_badge} &nbsp;&nbsp; "
                    f"<strong>Plan Period:</strong> {plan['plan_start']} → {plan['plan_end']} &nbsp;&nbsp; "
                    f"<strong>Months:</strong> {metrics['months_on_plan']} &nbsp;&nbsp; "
                    f"<strong>Proration:</strong> {metrics['proration']:.0%}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                om1, om2, om3 = st.columns(3)
                om1.metric("Prorated Variable",   fmt_currency(metrics["prorated_variable"]))
                om2.metric("Base Commission Rate", f"{metrics['base_rate']:.2%}")
                om3.metric("Quota Factor",         f"{plan['quota_factor']}×")

                # Quarterly Rollup (before factor)
                st.markdown(
                    "<div class='section-title'>Quarterly Quota — Rollup (before Quota Factor)</div>",
                    unsafe_allow_html=True,
                )
                oqa, oqb, oqc, oqd, oqt = st.columns(5)
                oqa.metric("Q1 (Feb–Apr)", fmt_currency(metrics["q1"]))
                oqb.metric("Q2 (May–Jul)", fmt_currency(metrics["q2"]))
                oqc.metric("Q3 (Aug–Oct)", fmt_currency(metrics["q3"]))
                oqd.metric("Q4 (Nov–Jan)", fmt_currency(metrics["q4"]))
                oqt.metric("Total Rollup", fmt_currency(metrics["quota_rollup"]))

                # Quarterly Adjusted (after factor)
                st.markdown(
                    f"<div class='section-title'>Quarterly Quota — Adjusted for Quota Factor ({plan['quota_factor']}×)</div>",
                    unsafe_allow_html=True,
                )
                ora, orb, orc, ord_, ort = st.columns(5)
                ora.metric("Q1 (Feb–Apr)", fmt_currency(metrics["q1_adjusted"]))
                orb.metric("Q2 (May–Jul)", fmt_currency(metrics["q2_adjusted"]))
                orc.metric("Q3 (Aug–Oct)", fmt_currency(metrics["q3_adjusted"]))
                ord_.metric("Q4 (Nov–Jan)", fmt_currency(metrics["q4_adjusted"]))
                ort.metric("Total Quota",  fmt_currency(metrics["total_quota"]))

                # Mini plan chart
                plan_chart_df = pd.DataFrame({
                    "Month": MONTH_LABELS,
                    "Quota": metrics["total_by_month"],
                })
                fig_plan = px.bar(
                    plan_chart_df, x="Month", y="Quota",
                    color_discrete_sequence=["#1565c0"],
                    text_auto=".2s",
                )
                fig_plan.update_layout(
                    height=250, showlegend=False,
                    yaxis_tickformat="$,.0f",
                    margin=dict(t=10, b=10, l=10, r=10),
                )
                st.plotly_chart(fig_plan, use_container_width=True)

                # AE list
                st.markdown("**AEs in this plan:**")
                ae_tbl = []
                for ae in plan["aes"]:
                    monthly = metrics["ae_monthly"].get(ae["name"], [0.0] * 12)
                    ae_tbl.append({
                        "Name":   ae["name"],
                        "Status": ae.get("status", "Started"),
                        "Segment": ae["segment"],
                        "Region":  ae["region"],
                        "Annual Quota": fmt_currency(ae["usd_quota"]),
                        "Plan Total":   fmt_currency(sum(monthly)),
                    })
                st.dataframe(pd.DataFrame(ae_tbl), use_container_width=True, hide_index=True)

                # Action buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    excel_bytes = build_excel(plan, metrics)
                    st.download_button(
                        label="⬇️ Export to Excel",
                        data=excel_bytes,
                        file_name=f"plan_{plan_name.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"dl_{plan_name}",
                    )
                with btn_col2:
                    if st.button(
                        "🗑️ Delete Plan",
                        key=f"del_{plan_name}",
                        use_container_width=True,
                    ):
                        del st.session_state.plans[plan_name]
                        st.rerun()
