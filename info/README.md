# GTM Sales Manager Planner

## What It Is

A **compensation planning dashboard** for sales managers that calculates quotas, commission rates, and team-level rollups for FY26.

## The Problem It Solves

Planning sales manager compensation is complex because:
- Manager quotas roll up from their team's individual AE (Account Executive) quotas
- New AEs ramp up gradually over 12 months (0% → 3% → 8.33% → 12.89%)
- Proration is needed for mid-year starts
- Multi-region teams deal with currency conversion (USD/GBP)
- Commission tiers create accelerators at 100% and 150% attainment

Doing this manually in spreadsheets is error-prone and time-consuming.

## How It Helps

**For Sales Operations / Finance:**
- Automatically calculates quota rollups from AE-level to manager-level
- Applies the standard ramp schedule to each AE based on their start date
- Handles proration for managers who start mid-year
- Converts GBP to USD at a standard FX rate
- Computes commission rates and tier thresholds

**For Sales Managers:**
- See your exact quota by month and quarter
- Understand how adding/removing team members affects your plan
- Export your compensation plan to Excel for sharing

## Key Features

| Feature | What It Does |
|---------|--------------|
| **Manager Dashboard** | View compensation plan, quota breakdown, and team roster |
| **Plan Builder** | Create or modify manager plans with custom team assignments |
| **AE Management** | Add existing AEs or TBH (To Be Hired) placeholders |
| **Quota Rollup** | Auto-calculate manager quota from team quotas with ramp |
| **Excel Export** | Download formatted compensation plans |
| **Multi-Region** | Support for NYC (USD) and London (GBP) regions |

## Example Output

For a manager like **Charlie Demuth** (Enterprise, NYC):
- Team of 9 AEs across FY26
- Quota Rollup: $11.6M → Adjusted Quota: $14.6M (1.25x factor)
- Base Commission Rate: 1.20%
- Tier 1 (100% attainment): 1.50%
- Tier 2 (150% attainment): 1.80%

## Running the App

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens in your browser where you can select a manager and view/edit their plan.
