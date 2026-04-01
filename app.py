"""GTM Sales Manager Planner – Streamlit Dashboard"""

from __future__ import annotations

import io
from datetime import date, datetime
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
    /* ── Header bar ────────────────────────────────────────────────────── */
    [data-testid="stAppViewContainer"] > .main > div:first-child {
        background: linear-gradient(135deg, #0d2b55 0%, #1a4a8a 100%);
    }
    .gtm-header {
        background: linear-gradient(135deg, #0d2b55 0%, #1a4a8a 100%);
        color: white;
        padding: 1.2rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .gtm-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .gtm-header p  { color: #a8c4e0; margin: 0.25rem 0 0; font-size: 0.9rem; }

    /* ── Segment colour pills ───────────────────────────────────────────── */
    .seg-enterprise  { background:#1565c0; color:white; padding:2px 8px; border-radius:12px; font-size:0.78rem; font-weight:600; }
    .seg-mid-market  { background:#2e7d32; color:white; padding:2px 8px; border-radius:12px; font-size:0.78rem; font-weight:600; }
    .seg-agency      { background:#e65100; color:white; padding:2px 8px; border-radius:12px; font-size:0.78rem; font-weight:600; }

    /* ── Metric card tweaks ─────────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: #f8faff;
        border: 1px solid #d0e0f8;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
    }
    [data-testid="metric-container"] label { color: #444; font-size: 0.78rem; }

    /* ── Plan card ──────────────────────────────────────────────────────── */
    .plan-card {
        border: 1px solid #d0e0f8;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        background: #f8faff;
        margin-bottom: 0.8rem;
    }

    /* ── Sidebar ────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] { background: #0d2b55; }
    [data-testid="stSidebar"] * { color: #d0e8ff !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label { color: #a8c4e0 !important; }
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_currency(amount: float, currency: str = "USD") -> str:
    if currency == "GBP":
        return f"£{amount:,.0f}"
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
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m/%d/%Y", "%-m/%-d/%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(str(val)).date()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Ramp schedule
# ---------------------------------------------------------------------------

def get_ramp_pct(month_num: int) -> float:
    """Return ramp % for a 1-indexed employment month."""
    if month_num <= 0:
        return 0.0
    if month_num == 1:
        return 0.0
    elif month_num == 2:
        return 0.03
    elif 3 <= month_num <= 9:
        return 0.0833
    elif 10 <= month_num <= 12:
        return 0.1289
    else:  # 13+
        return 0.0833


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


# ---------------------------------------------------------------------------
# Plan metrics
# ---------------------------------------------------------------------------

def calculate_plan_metrics(plan: dict) -> dict:
    aes = plan["aes"]
    months_on_plan = calculate_months_on_plan(plan["plan_start"], plan["plan_end"])
    proration = months_on_plan / 12.0

    ae_monthly: dict[str, list[float]] = {}
    for ae in aes:
        monthly = [
            calc_monthly_quota(ae["usd_quota"], ae["on_plan_date"], fm)
            for fm in FISCAL_MONTHS
        ]
        ae_monthly[ae["name"]] = monthly

    total_by_month = [
        sum(ae_monthly[ae["name"]][i] for ae in aes)
        for i in range(12)
    ]
    quota_rollup = sum(total_by_month)

    total_quota    = quota_rollup * plan["quota_factor"]
    prorated_quota = total_quota * proration

    prorated_variable = plan["variable"] * proration
    base_rate = prorated_variable / prorated_quota if prorated_quota > 0 else 0.0

    tier1_threshold = prorated_quota
    tier1_rate      = base_rate * 1.25
    tier2_threshold = prorated_quota * 1.5
    tier2_rate      = base_rate * 1.5

    q1 = sum(total_by_month[0:3])
    q2 = sum(total_by_month[3:6])
    q3 = sum(total_by_month[6:9])
    q4 = sum(total_by_month[9:12])

    return {
        "ae_monthly":       ae_monthly,
        "total_by_month":   total_by_month,
        "quota_rollup":     quota_rollup,
        "total_quota":      total_quota,
        "prorated_quota":   prorated_quota,
        "months_on_plan":   months_on_plan,
        "proration":        proration,
        "prorated_variable": prorated_variable,
        "base_rate":        base_rate,
        "tier1_threshold":  tier1_threshold,
        "tier1_rate":       tier1_rate,
        "tier2_threshold":  tier2_threshold,
        "tier2_rate":       tier2_rate,
        "q1": q1, "q2": q2, "q3": q3, "q4": q4,
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
        # ── Sheet 1: Detailed Plan ────────────────────────────────────────
        rows = []
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
            rows.append(row)

        detail_df = pd.DataFrame(rows)
        detail_df.to_excel(writer, sheet_name="Detailed Plan", index=False)

        # ── Sheet 2: Summary ──────────────────────────────────────────────
        summary_rows = [
            ("Manager",            plan["manager_name"]),
            ("Segment",            plan["segment"]),
            ("Region",             plan["region"]),
            ("Currency",           plan["currency"]),
            ("Base Salary",        plan["base_salary"]),
            ("Variable",           plan["variable"]),
            ("Quota Factor",       plan["quota_factor"]),
            ("Plan Start",         plan["plan_start"]),
            ("Plan End",           plan["plan_end"]),
            ("Months on Plan",     metrics["months_on_plan"]),
            ("Proration",          f"{metrics['proration']:.2%}"),
            ("",                   ""),
            ("Quota Rollup",       metrics["quota_rollup"]),
            ("Total Quota",        metrics["total_quota"]),
            ("Prorated Quota",     metrics["prorated_quota"]),
            ("Prorated Variable",  metrics["prorated_variable"]),
            ("Base Commission Rate", f"{metrics['base_rate']:.2%}"),
            ("",                   ""),
            ("Tier 1 Threshold",   metrics["tier1_threshold"]),
            ("Tier 1 Rate",        f"{metrics['tier1_rate']:.2%}"),
            ("Tier 2 Threshold",   metrics["tier2_threshold"]),
            ("Tier 2 Rate",        f"{metrics['tier2_rate']:.2%}"),
            ("",                   ""),
            ("Q1 (Feb-Apr)",       metrics["q1"]),
            ("Q2 (May-Jul)",       metrics["q2"]),
            ("Q3 (Aug-Oct)",       metrics["q3"]),
            ("Q4 (Nov-Jan)",       metrics["q4"]),
        ]
        # Monthly headcount
        for i, lbl in enumerate(MONTH_LABELS):
            count = sum(
                1 for ae in plan["aes"]
                if calc_monthly_quota(ae["usd_quota"], ae["on_plan_date"], FISCAL_MONTHS[i]) > 0
            )
            summary_rows.append((f"Headcount {lbl}", count))

        summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
ae_df, mgr_df = load_data()

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
      <p>FY2026 · Feb 1 2026 – Jan 31 2027 · Quota, Ramp & Compensation Planning</p>
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

    # Colour-coded segment display
    def _seg_html(seg: str) -> str:
        cls = {
            "Enterprise":  "seg-enterprise",
            "Mid Market":  "seg-mid-market",
            "Agency":      "seg-agency",
        }.get(seg, "")
        return f'<span class="{cls}">{seg}</span>'

    display_df = filtered_ae[[
        "AEs", "Segment", "Region", "Start Date", "On Plan Date",
        "Local Currency", "FX", "Local Variable", "USD Variable",
        "Commission Rate (Fixed)", "USD Quota (Annual)",
    ]].copy()

    display_df["Start Date"]   = display_df["Start Date"].astype(str)
    display_df["On Plan Date"] = display_df["On Plan Date"].astype(str)
    display_df["Commission Rate (Fixed)"] = display_df["Commission Rate (Fixed)"].apply(
        lambda x: f"{x:.2%}"
    )
    display_df["USD Variable"]       = display_df["USD Variable"].apply(lambda x: fmt_currency(x))
    display_df["USD Quota (Annual)"] = display_df["USD Quota (Annual)"].apply(lambda x: fmt_currency(x))
    display_df["Local Variable"]     = display_df["Local Variable"].apply(lambda x: f"{x:,.0f}")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Segment": st.column_config.TextColumn("Segment"),
            "Commission Rate (Fixed)": st.column_config.TextColumn("Commission %"),
        },
    )

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
    st.markdown("### 🏗️ Build a Manager Plan")

    # ── Manager Details ────────────────────────────────────────────────────
    with st.expander("📌 Manager Details", expanded=True):
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
            st.info(f"Currency: **{plan_currency}**  |  FX Rate: **{plan_fx}**")

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
            default_local_var = 120000 if seg == "Enterprise" else 100000
            default_quota     = 1000000 if seg != "Enterprise" else 1166667

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
    st.markdown("### 📊 Live Preview")

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
        st.markdown("#### 📐 Plan Metrics")
        m1, m2, m3 = st.columns(3)
        m1.metric("Quota Rollup",     fmt_currency(metrics["quota_rollup"]))
        m2.metric("Total Quota",      fmt_currency(metrics["total_quota"]),
                  delta=f"×{quota_factor} factor")
        m3.metric("Prorated Quota",   fmt_currency(metrics["prorated_quota"]),
                  delta=f"{metrics['months_on_plan']} mo / {metrics['proration']:.0%}")

        m4, m5, m6 = st.columns(3)
        m4.metric("Prorated Variable", fmt_currency(metrics["prorated_variable"]))
        m5.metric("Base Commission Rate", f"{metrics['base_rate']:.2%}")
        m6.metric("Months on Plan", metrics["months_on_plan"])

        st.markdown("#### 🎯 Accelerator Tiers")
        t1, t2 = st.columns(2)
        t1.metric("Tier 1 Threshold", fmt_currency(metrics["tier1_threshold"]),
                  delta=f"Rate: {metrics['tier1_rate']:.2%}")
        t2.metric("Tier 2 Threshold", fmt_currency(metrics["tier2_threshold"]),
                  delta=f"Rate: {metrics['tier2_rate']:.2%}")

        # ── Quarterly breakdown ────────────────────────────────────────────
        st.markdown("#### 📅 Quarterly Breakdown")
        qa, qb, qc, qd = st.columns(4)
        qa.metric("Q1 (Feb–Apr)", fmt_currency(metrics["q1"]))
        qb.metric("Q2 (May–Jul)", fmt_currency(metrics["q2"]))
        qc.metric("Q3 (Aug–Oct)", fmt_currency(metrics["q3"]))
        qd.metric("Q4 (Nov–Jan)", fmt_currency(metrics["q4"]))

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
    st.markdown("### 📊 Saved Plans Overview")

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
            cur = plan["currency"]

            with st.expander(
                f"📁 {plan_name}  ·  {plan['segment']}  ·  {plan['region']}  ·  "
                f"{len(plan['aes'])} AEs  ·  "
                f"Total Quota: {fmt_currency(metrics['total_quota'], cur)}",
                expanded=False,
            ):
                ov1, ov2, ov3, ov4 = st.columns(4)
                ov1.metric("Manager",     plan_name)
                ov2.metric("Segment",     plan["segment"])
                ov3.metric("Region",      plan["region"])
                ov4.metric("Team Size",   len(plan["aes"]))

                om1, om2, om3, om4 = st.columns(4)
                om1.metric("Quota Rollup",   fmt_currency(metrics["quota_rollup"], cur))
                om2.metric("Total Quota",    fmt_currency(metrics["total_quota"],  cur))
                om3.metric("Prorated Quota", fmt_currency(metrics["prorated_quota"], cur))
                om4.metric("Months on Plan", metrics["months_on_plan"])

                oq1, oq2, oq3, oq4 = st.columns(4)
                oq1.metric("Q1 (Feb–Apr)", fmt_currency(metrics["q1"], cur))
                oq2.metric("Q2 (May–Jul)", fmt_currency(metrics["q2"], cur))
                oq3.metric("Q3 (Aug–Oct)", fmt_currency(metrics["q3"], cur))
                oq4.metric("Q4 (Nov–Jan)", fmt_currency(metrics["q4"], cur))

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
