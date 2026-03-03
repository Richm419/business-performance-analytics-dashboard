import os
import re
import numpy as np
import pandas as pd

# =====================
# CONFIG
# =====================
NEW_ROWS = 100  # <-- change if you want
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")

JOBS_PATH = os.path.join(DATA_DIR, "jobs.csv")
FACT_PATH = os.path.join(DATA_DIR, "job_costing_fact.csv")

np.random.seed(42)

# =====================
# HELPERS
# =====================
def season_from_month(m: int) -> str:
    if m in (12, 1, 2):
        return "Winter"
    if m in (3, 4, 5):
        return "Spring"
    if m in (6, 7, 8):
        return "Summer"
    return "Fall"

def get_next_job_number(job_id_series: pd.Series) -> int:
    # Handles IDs like J001, J120, etc.
    extracted = job_id_series.astype(str).str.extract(r"(\d+)")[0]
    extracted = pd.to_numeric(extracted, errors="coerce")
    return int(extracted.max()) + 1

def format_job_id(n: int) -> str:
    return f"J{n:03d}"

def random_dates_jun_dec(n: int) -> pd.Series:
    start_date = pd.to_datetime("2025-06-01")
    end_date = pd.to_datetime("2025-12-31")
    rand_days = np.random.randint(0, (end_date - start_date).days + 1, size=n)
    return (start_date + pd.to_timedelta(rand_days, unit="D")).date


def get_markup(job_type: str) -> float:
    # More realistic: new construction tends to have better margin
    ranges = {
        "New Construction": (0.30, 0.45),
        "Exterior Repaint": (0.25, 0.40),
        "Interior Repaint": (0.20, 0.35),
        "Patching": (0.15, 0.30),
        "Repaint": (0.10, 0.25),
    }
    low, high = ranges.get(job_type, (0.15, 0.30))
    return float(np.round(np.random.uniform(low, high), 2))

def job_type_params(job_type: str):
    """
    Returns realistic ranges by job type:
    (crew_low, crew_high, est_hours_low, est_hours_high, mat_low, mat_high, labor_rate_low, labor_rate_high)
    """
    if job_type == "New Construction":
        return (4, 8, 80, 220, 3000, 12000, 55, 90)
    if job_type == "Exterior Repaint":
        return (3, 6, 40, 120, 1200, 6000, 50, 85)
    if job_type == "Interior Repaint":
        return (2, 5, 30, 90, 600, 3500, 45, 80)
    if job_type == "Patching":
        return (1, 3, 8, 35, 150, 1200, 40, 70)
    # Repaint (general)
    return (2, 4, 20, 70, 400, 2500, 45, 80)

def make_address() -> str:
    street_num = np.random.randint(10, 9999)
    street_names = ["Main", "Maple", "Oak", "Pine", "Cedar", "Elm", "Washington", "High", "Park", "School", "Prospect"]
    street_types = ["St", "Ave", "Rd", "Ln", "Dr", "Ct", "Blvd"]
    return f"{street_num} {np.random.choice(street_names)} {np.random.choice(street_types)}"

# =====================
# LOAD EXISTING
# =====================
jobs = pd.read_csv(JOBS_PATH)
fact = pd.read_csv(FACT_PATH)

# Ensure job_id exists
if "job_id" not in jobs.columns:
    raise ValueError("jobs.csv must have a 'job_id' column.")
if "job_id" not in fact.columns:
    raise ValueError("job_costing_fact.csv must have a 'job_id' column.")

# =====================
# GENERATE NEW JOBS (JUN-DEC)
# =====================
job_types = ["Repaint", "Interior Repaint", "Exterior Repaint", "Patching", "New Construction"]

cities = [
    "Boston", "Quincy", "Braintree", "Weymouth", "Hingham", "Hull", "Rockland", "Hanover", "Norwell",
    "Plymouth", "Kingston", "Duxbury", "Marshfield", "Scituate", "Brockton", "Abington", "Holbrook",
    "Randolph", "Milton", "Somerville", "Cambridge", "Medford", "Malden", "Chelsea", "Newton", "Waltham",
    "Dedham", "Needham", "Woburn", "Peabody", "Salem"
]
states = ["MA", "RI", "NH", "CT"]

next_num = get_next_job_number(jobs["job_id"])
new_nums = np.arange(next_num, next_num + NEW_ROWS)
new_job_ids = [format_job_id(n) for n in new_nums]

new_job_dates = random_dates_jun_dec(NEW_ROWS)
new_job_types = np.random.choice(job_types, size=NEW_ROWS, replace=True)

# Customer names (simple but realistic-ish)
last_names = ["Mansfield", "Johnson", "Murphy", "Sullivan", "Donovan", "McCarthy", "Rossi", "Parker", "Baker", "O'Neil"]
first_names = ["Chris", "Pat", "Taylor", "Jordan", "Alex", "Sam", "Casey", "Jamie", "Morgan", "Riley"]

customer_names = [f"{np.random.choice(first_names)} {np.random.choice(last_names)}" for _ in range(NEW_ROWS)]

crew_sizes = []
estimated_hours = []
actual_hours = []
labor_rates = []
estimated_materials = []
actual_materials = []
markups = []
addresses = []
city_vals = []
state_vals = []

for jt in new_job_types:
    crew_low, crew_high, eh_low, eh_high, mat_low, mat_high, lr_low, lr_high = job_type_params(jt)

    crew = np.random.randint(crew_low, crew_high + 1)
    est_h = np.random.randint(eh_low, eh_high + 1)

    # actual hours: around estimated, sometimes overruns
    # use multiplier for realism
    hour_mult = np.random.normal(loc=1.05, scale=0.15)  # slight tendency to overrun
    act_h = int(max(1, round(est_h * hour_mult)))

    lr = np.random.randint(lr_low, lr_high + 1)

    est_mat = np.random.randint(mat_low, mat_high + 1)
    mat_mult = np.random.normal(loc=1.03, scale=0.18)
    act_mat = int(max(50, round(est_mat * mat_mult)))

    crew_sizes.append(crew)
    estimated_hours.append(est_h)
    actual_hours.append(act_h)
    labor_rates.append(lr)
    estimated_materials.append(est_mat)
    actual_materials.append(act_mat)
    markups.append(get_markup(jt))
    addresses.append(make_address())
    city_vals.append(np.random.choice(cities))
    state_vals.append(np.random.choice(states))

new_jobs = pd.DataFrame({
    "job_id": new_job_ids,
    "job_date": new_job_dates,
    "job_type": new_job_types,
    "customer_name": customer_names,
    "address": addresses,
    "city": city_vals,
    "state": state_vals,
    "crew_size": crew_sizes,
    "estimated_hours": estimated_hours,
    "actual_hours": actual_hours,
    "labor_rate": labor_rates,
    "estimated_material_cost": estimated_materials,
    "actual_material_cost": actual_materials,
    "markup_pct": markups
})

# =====================
# BUILD NEW FACT ROWS (derive fields)
# =====================
new_fact = new_jobs.copy()

# derived costs
new_fact["estimated_labor_cost"] = new_fact["estimated_hours"] * new_fact["labor_rate"]
new_fact["actual_labor_cost"] = new_fact["actual_hours"] * new_fact["labor_rate"]

new_fact["estimated_total_cost"] = new_fact["estimated_labor_cost"] + new_fact["estimated_material_cost"]
new_fact["actual_total_cost"] = new_fact["actual_labor_cost"] + new_fact["actual_material_cost"]

# revenue (based on estimated_total_cost and markup)
new_fact["revenue"] = (new_fact["estimated_total_cost"] * (1 + new_fact["markup_pct"])).round(2)

# profit + margin
new_fact["profit"] = (new_fact["revenue"] - new_fact["actual_total_cost"]).round(2)
new_fact["profit_margin_pct"] = np.where(
    new_fact["revenue"] == 0,
    0,
    (new_fact["profit"] / new_fact["revenue"]).round(4)
)

# variances
new_fact["total_cost_variance"] = (new_fact["actual_total_cost"] - new_fact["estimated_total_cost"]).round(2)
new_fact["total_cost_variance_pct"] = np.where(
    new_fact["estimated_total_cost"] == 0,
    0,
    (new_fact["total_cost_variance"] / new_fact["estimated_total_cost"]).round(4)
)

new_fact["labor_hours_variance"] = (new_fact["actual_hours"] - new_fact["estimated_hours"]).astype(int)
new_fact["labor_cost_variance"] = (new_fact["actual_labor_cost"] - new_fact["estimated_labor_cost"]).round(2)
new_fact["material_cost_variance"] = (new_fact["actual_material_cost"] - new_fact["estimated_material_cost"]).round(2)

new_fact["is_overrun"] = np.where(new_fact["actual_total_cost"] > new_fact["estimated_total_cost"], 1, 0)

# time columns
job_dt = pd.to_datetime(new_fact["job_date"])
new_fact["year"] = job_dt.dt.year
new_fact["month_num"] = job_dt.dt.month
new_fact["month"] = job_dt.dt.strftime("%B")
new_fact["quarter"] = "Q" + job_dt.dt.quarter.astype(str)
new_fact["season"] = new_fact["month_num"].apply(season_from_month)

# =====================
# ALIGN TO EXISTING COLUMNS + APPEND
# =====================
# Keep jobs.csv columns consistent
jobs_out = pd.concat([jobs, new_jobs[jobs.columns]], ignore_index=True)

# Keep fact table columns consistent
# NOTE: Fact table must include these columns already. We'll select only the existing columns.
missing_for_fact = [c for c in fact.columns if c not in new_fact.columns]
if missing_for_fact:
    # If your fact table has extra columns, fill them with blanks/zeros
    for c in missing_for_fact:
        new_fact[c] = 0

fact_out = pd.concat([fact, new_fact[fact.columns]], ignore_index=True)

# =====================
# SAVE
# =====================
jobs_out.to_csv(JOBS_PATH, index=False)
fact_out.to_csv(FACT_PATH, index=False)

print("Done!")
print(f"Appended {NEW_ROWS} rows (June–Dec).")
print(f"jobs.csv rows now: {len(jobs_out)}")
print(f"job_costing_fact.csv rows now: {len(fact_out)}")
