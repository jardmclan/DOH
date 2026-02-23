import pandas as pd
import sqlite3

# Database name
DB_NAME = "DOH_AMHD_NO_PII.db"

# Load CSVs
print("Loading CSV files...")
df_diag_su = pd.read_csv("discharge_data_view_diag_su.csv")
df_diag_mh = pd.read_csv("discharge_data_view_diag_mh.csv")
df_demo = pd.read_csv("discharge_data_view_demographics.csv")
df_dose = pd.read_csv("dose_data.csv")

# Clean column names (lowercase and strip whitespace)
df_diag_su.columns = df_diag_su.columns.str.lower().str.strip()
df_diag_mh.columns = df_diag_mh.columns.str.lower().str.strip()
df_demo.columns = df_demo.columns.str.lower().str.strip()
df_dose.columns = df_dose.columns.str.lower().str.strip()


print(f"Loaded {len(df_diag_su):,} diag_su records, {len(df_diag_mh):,} diag_mh records, {len(df_demo):,} demographics records, and {len(df_dose)} overdose poisoning records")
print(f"diag_su columns: {df_diag_su.columns.tolist()}")
print(f"diag_mh columns: {df_diag_mh.columns.tolist()}")
print(f"demographics columns: {df_demo.columns.tolist()}")
print(f"overdose poisonings columns: {df_dose.columns.tolist()}")

# Connect to SQLite (local development database)
print(f"\nConnecting to SQLite database ({DB_NAME})...")
conn = sqlite3.connect(DB_NAME)

try:
    # Save as tables - table names match CSV filenames (without .csv extension)
    print("Creating 'discharge_data_view_diag_su' table...")
    df_diag_su.to_sql("discharge_data_view_diag_su", conn, if_exists="replace", index=False)
    
    print("Creating 'discharge_data_view_diag_mh' table...")
    df_diag_mh.to_sql("discharge_data_view_diag_mh", conn, if_exists="replace", index=False)

    print("Creating 'discharge_data_view_demographics' table...")
    df_demo.to_sql("discharge_data_view_demographics", conn, if_exists="replace", index=False)
    
    print("Creating 'nonfatal_overdose_poisonings' table...")
    df_dose.to_sql("nonfatal_overdose_poisonings", conn, if_exists="replace", index=False)

    print(f"\n✅ Database tables created successfully in {DB_NAME}")
    print(f"  - discharge_data_view_diag_su: {len(df_diag_su):,} rows")
    print(f"  - discharge_data_view_diag_mh: {len(df_diag_mh):,} rows")
    print(f"  - discharge_data_view_demographics: {len(df_demo):,} rows")
    print(f"  - nonfatal_overdose_poisonings: {len(df_dose):,} rows")

finally:
    conn.close()

# Verify table structure
print("\nVerifying table structure...")
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

for table in ['discharge_data_view_diag_su', 'discharge_data_view_diag_mh', 'discharge_data_view_demographics', 'nonfatal_overdose_poisonings']:
    cursor.execute(f"PRAGMA table_info({table})")
    print(f"\n{table} columns:")
    for row in cursor.fetchall():
        print(f"  - {row[1]}")

conn.close()

# python -c "import sqlite3; conn = sqlite3.connect('DOH_AMHD_NO_PII.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(discharge_data_view_demographics)'); print('discharge_data_view_demographics columns:'); [print(f\"  {row[1]}\") for row in cursor.fetchall()]; conn.close()"