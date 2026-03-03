import pandas as pd
import numpy as np

# ---------- CONFIG ----------
INPUT_PATH = "data/jobs.csv"
OUTPUT_FACT_PATH = "data/job_costing_fact.csv"
OUTPUT_DICT_PATH = "data/data_dictionary.csv"

# ---------- LOAD ----------
df = pd.read_csv(INPUT_PATH)

# ---------- CLEAN / TYPES ----------
# dates
df["job_date"] = pd.to_datetime(df["job_date"], errors="coerce")

# numeric columns (force to numbers in case Excel saved as text)
num_cols = [
    "crew_size",
    "estimated_hours",
    "actual_hours",
    "estimated_material_cost",
    "actual_material_cost",
    "labor_rate",
]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# drop rows missing critical fields
df = df.dropna(subset=["job_id", "job_date", "job_type", "estimated_hours", "actual_hours",
                       "estimated_material_cost", "actual_material_cost", "labor_rate"])

# ---------- DERIVED DATE FIELDS ----------
df["year"] = df["job_date"].dt.year
df["month_num"] = df["job_date"].dt.month
df["month"] = df["job_date"].dt.strftime("%b")
df["quarter"] = "Q" + df["job_date"].dt.quarter.astype(str)

# season (simple)
def season_from_month(m: int) -> str:
    if m in (12, 1, 2):
        return "Winter"
    if m in (3, 4, 5):
        return "Spring"
    if m in (6, 7, 8):
        return "Summer"
    return "Fall"

df["season"] = df["month_num"].apply(season_from_month)

# ---------- COST CALCS ----------
df["estimated_labor_cost"] = df["estimated_hours"] * df["labor_rate"]
df["actual_labor_cost"] = df["actual_hours"] * df["labor_rate"]

df["estimated_total_cost"] = df["estimated_labor_cost"] + df["estimated_material_cost"]
df["actual_total_cost"] = df["actual_labor_cost"] + df["actual_material_cost"]

# ---------- REVENUE / PROFIT (SIMULATED BUT REALISTIC) ----------
# Revenue is typically cost + markup. We'll vary markup by job_type a bit to make patterns.
markup_map = {
    "Repaint": 0.35,
    "Interior Repaint": 0.38,
    "Exterior Repaint": 0.40,
    "Patching": 0.30,
    "New Construction": 0.32,
}

# default markup if job_type is unexpected
default_markup = 0.35

df["markup_pct"] = df["job_type"].map(markup_map).fillna(default_markup)

# add small randomness to avoid identical results (±5%)
rng = np.random.default_rng(42)
df["markup_pct"] = (df["markup_pct"] + rng.normal(0, 0.03, size=len(df))).clip(0.20, 0.55)

# revenue based on *estimated* cost, like a real estimate/bid
df["revenue"] = df["estimated_total_cost"] * (1 + df["markup_pct"])

# profit and margins (based on actual costs)
df["profit"] = df["revenue"] - df["actual_total_cost"]
df["profit_margin_pct"] = np.where(df["revenue"] != 0, df["profit"] / df["revenue"], np.nan)

# ---------- VARIANCES / OVERRUN FLAGS ----------
df["labor_hours_variance"] = df["actual_hours"] - df["estimated_hours"]
df["labor_cost_variance"] = df["actual_labor_cost"] - df["estimated_labor_cost"]
df["material_cost_variance"] = df["actual_material_cost"] - df["estimated_material_cost"]
df["total_cost_variance"] = df["actual_total_cost"] - df["estimated_total_cost"]

# percent variance relative to estimate
df["total_cost_variance_pct"] = np.where(
    df["estimated_total_cost"] != 0,
    df["total_cost_variance"] / df["estimated_total_cost"],
    np.nan
)

# overrun if actual total cost > estimate
df["is_overrun"] = (df["actual_total_cost"] > df["estimated_total_cost"]).astype(int)

# ---------- ORDER COLUMNS (clean fact table) ----------
fact_cols = [
    "job_id", "job_date", "year", "quarter", "month_num", "month", "season",
    "customer_name", "address", "city", "state",
    "job_type", "crew_size",
    "estimated_hours", "actual_hours",
    "labor_rate",
    "estimated_material_cost", "actual_material_cost",
    "estimated_labor_cost", "actual_labor_cost",
    "estimated_total_cost", "actual_total_cost",
    "revenue", "profit", "profit_margin_pct",
    "labor_hours_variance", "labor_cost_variance",
    "material_cost_variance", "total_cost_variance", "total_cost_variance_pct",
    "is_overrun", "markup_pct"
]

# keep only columns that exist (safety)
fact_cols = [c for c in fact_cols if c in df.columns]
df_fact = df[fact_cols].copy()

# ---------- EXPORT ----------
df_fact.to_csv(OUTPUT_FACT_PATH, index=False)

# ---------- DATA DICTIONARY (for resume bullet) ----------
data_dict = [
    ("job_id", "Unique job identifier (e.g., J001)."),
    ("job_date", "Date the job started."),
    ("job_type", "Painting job category (Repaint, Interior Repaint, Exterior Repaint, Patching, New Construction)."),
    ("crew_size", "Number of workers assigned to the job."),
    ("estimated_hours", "Estimated labor hours."),
    ("actual_hours", "Actual labor hours."),
    ("labor_rate", "Hourly labor rate used for costing."),
    ("estimated_material_cost", "Estimated cost of materials."),
    ("actual_material_cost", "Actual cost of materials."),
    ("estimated_labor_cost", "estimated_hours * labor_rate."),
    ("actual_labor_cost", "actual_hours * labor_rate."),
    ("estimated_total_cost", "estimated_labor_cost + estimated_material_cost."),
    ("actual_total_cost", "actual_labor_cost + actual_material_cost."),
    ("revenue", "Simulated bid revenue based on estimated_total_cost and markup_pct."),
    ("profit", "revenue - actual_total_cost."),
    ("profit_margin_pct", "profit / revenue."),
    ("total_cost_variance", "actual_total_cost - estimated_total_cost."),
    ("total_cost_variance_pct", "total_cost_variance / estimated_total_cost."),
    ("is_overrun", "1 if actual_total_cost > estimated_total_cost else 0."),
    ("season", "Season derived from job_date."),
]

pd.DataFrame(data_dict, columns=["field", "definition"]).to_csv(OUTPUT_DICT_PATH, index=False)

print("Done!")
print(f"Created: {OUTPUT_FACT_PATH}")
print(f"Created: {OUTPUT_DICT_PATH}")
print(f"Rows: {len(df_fact)}")
