import pandas as pd

# Load CSV files
try:
    df_diag = pd.read_csv("discharge_data_view_diag_su.csv")
    print("✅ Loaded: discharge_data_view_diag_su.csv")
except FileNotFoundError:
    print("❌ File not found: discharge_data_view_diag_su.csv")
    df_diag = pd.DataFrame()

try:
    df_demo = pd.read_csv("discharge_data_view_demographics.csv")
    print("✅ Loaded: discharge_data_view_demographics.csv")
except FileNotFoundError:
    print("❌ File not found: discharge_data_view_demographics.csv")
    df_demo = pd.DataFrame()

try:
    df_dose = pd.read_csv("dose_data.csv")
    print("✅ Loaded: dose_date.csv")
except FileNotFoundError:
    print("❌ File not found: dose_data.csv")
    df_dose = pd.DataFrame()

# Clean column names
df_diag.columns = df_diag.columns.str.lower().str.strip()
df_demo.columns = df_demo.columns.str.lower().str.strip()
df_dose.columns = df_dose.columns.str.lower().str.strip()

# Show cleaned column names
print("\n📄 Columns in 'discharge_data_view_diag_su.csv':")
print(df_diag.columns.tolist())

print("\n📄 Columns in 'discharge_data_view_demographics.csv':")
print(df_demo.columns.tolist())

print("\n📄 Columns in 'dose_data.csv':")
print(df_dose.columns.tolist())

# Optional: print first 2 rows of each to inspect
print("\n🔍 Sample rows from diagnoses file:")
print(df_diag.head(2))

print("\n🔍 Sample rows from demographics file:")
print(df_demo.head(2))

print("\n🔍 Sample rows from dose file:")
print(df_dose.head(2))
