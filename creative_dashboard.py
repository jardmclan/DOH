import math
from db_utils import execute_query
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.io as pio
from theme import register_template

# Option A: use defaults from theme.py
register_template()  # registers "doh" and sets it as default

# Option B: override any setting (fonts, colors, backgrounds)
# register_template(cfg={
#     "font_family": "Segoe UI",
#     "font_size": 12,
#     "text_color": "#212121",
#     "title_color": "#363630",
#     "paper_bg": "#FFFFFF",
#     "plot_bg":  "#FFFFFF",
#     "colorway": ["#22767C", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA"]
# })



# ----------------------------
# Helper: load a named SQL block
# ----------------------------
def load_sql_query(name, path="queries.sql"):
    with open(path, "r", encoding="utf-8") as file:
        sql = file.read()
    blocks = sql.split("-- name:")
    query_map = {}
    for block in blocks:
        if block.strip() == "":
            continue
        lines = block.strip().split("\n")
        query_name = lines[0].strip()
        query_sql = "\n".join(lines[1:]).strip()
        query_map[query_name] = query_sql
    if name not in query_map:
        raise KeyError(f"Named query '{name}' not found in {path}.")
    return query_map[name]


# ----------------------------
# Load data from database via your named query
# ----------------------------
def load_discharge_dataframe_from_db():
    sql = load_sql_query("load_discharge_data_view_diag_su")
    
    # Execute query using db_utils (automatically uses correct database)
    df = execute_query(sql)

    if df.empty:
        raise RuntimeError(
            "Query returned 0 rows.\n"
            "Check that queries.sql has the updated -- name: load_discharge_data_view_diag_su block\n"
            "and that your 'diagnoses'/'demographics' table column names match."
        )

    # Types/cleaning for charts & filters
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
    for col in ["county", "city", "hawaii_residency", "age_group", "sex", "substance"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    return df


# ----------------------------
# Load data
# ----------------------------
df_raw = load_discharge_dataframe_from_db()

# KPI: exact total (no rounding)
total_unique = df_raw["record_id"].nunique()

# Precompute filter options (sorted; Unknown last)
def sort_opts(series):
    vals = pd.Series(series.unique()).astype(str)
    vals = sorted([v for v in vals if v != "Unknown"]) + (["Unknown"] if "Unknown" in vals.values else [])
    return vals

county_opts         = sort_opts(df_raw["county"])         if "county"         in df_raw.columns else []
city_opts           = sort_opts(df_raw["city"])           if "city"           in df_raw.columns else []
hawaii_residency_opts = sort_opts(df_raw["hawaii_residency"]) if "hawaii_residency" in df_raw.columns else []
age_opts            = sort_opts(df_raw["age_group"])      if "age_group"      in df_raw.columns else []
sex_opts            = sort_opts(df_raw["sex"])            if "sex"            in df_raw.columns else []


# ----------------------------
# Dash app
# ----------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2("Substance Use Emergency Discharges",
            className="text-white bg-dark p-3 text-center mb-4"),

    dbc.Row([
        # Left: Overview and Filters
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Discharges", className="card-title text-white"),
                    html.H2(f"{total_unique:,}", className="text-white"),
                    html.Small("Number of Emergency Discharges Related to Substance Use", className="text-white-50")
                ])
            ], className="bg-success text-center mb-4"),

            html.H5("Filter Data"),
            dcc.Dropdown(county_opts,         id="county-filter",         placeholder="County",         className="mb-2"),
            dcc.Dropdown(city_opts,           id="city-filter",           placeholder="City",           className="mb-2"),
            dcc.Dropdown(hawaii_residency_opts, id="hawaii-residency-filter", placeholder="Hawaii Resident", className="mb-2"),
            dcc.Dropdown(age_opts,            id="age-filter",            placeholder="Age Group",      className="mb-2"),
            dcc.Dropdown(sex_opts,            id="sex-filter",            placeholder="Sex",            className="mb-4"),
        ], width=3),

        # Middle: Graphs
        dbc.Col([
            dcc.Graph(id="substance-bar", className="mb-4", style={"height": "400px"}),
            dcc.Graph(id="year-bar", style={"height": "360px"})
        ], width=6),

        # Right: Tables
        dbc.Col([
            html.H5("By County"),
            html.Div(id="table-county", className="mb-3"),
            html.H5("By Age Group"),
            html.Div(id="table-age", className="mb-3"),
            html.H5("By Sex"),
            html.Div(id="table-sex"),
        ], width=3),
    ])
], fluid=True)


@app.callback(
    Output("substance-bar", "figure"),
    Output("year-bar", "figure"),
    Output("table-county", "children"),
    Output("table-age", "children"),
    Output("table-sex", "children"),
    Input("county-filter", "value"),
    Input("city-filter", "value"),
    Input("hawaii-residency-filter", "value"),
    Input("age-filter", "value"),
    Input("sex-filter", "value"),
)
def update_dashboard(county, city, hawaii_residency, age, sex):
    # 1) Filter FIRST on the full, per-substance dataset
    dff = df_raw.copy()
    if county:         dff = dff[dff["county"] == county]
    if city:           dff = dff[dff["city"] == city]
    if hawaii_residency: dff = dff[dff["hawaii_residency"] == hawaii_residency]
    if age:            dff = dff[dff["age_group"] == age]
    if sex:            dff = dff[dff["sex"] == sex]

    # 2) Two views:
    #    - dff_poly: keep polysubstance rows (use for substance chart)
    #    - dff_uniq: unique discharges (use for year + tables)
    dff_poly = dff
    dff_uniq = dff.drop_duplicates(subset="record_id")

    # -------- Substance chart (NO dedup → matches Power BI) --------
    if "substance" in dff_poly.columns:
        substance_counts = dff_poly.groupby("substance")["record_id"].nunique().reset_index()
        substance_counts.columns = ["substance", "count"]
        substance_counts = substance_counts.sort_values("count")
    else:
        substance_counts = pd.DataFrame(columns=["substance", "count"])

    substance_fig = px.bar(
        substance_counts,
        x="count", y="substance", orientation="h",
        title="Discharges by Substance",
        labels={"count": "Count", "substance": "Substance"},
        text="count",
    )
    max_sub = int(substance_counts["count"].max()) if not substance_counts.empty else 0
    substance_fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
    substance_fig.update_layout(
        margin=dict(l=0, r=20, t=40, b=0),
        yaxis=dict(automargin=True),
        xaxis=dict(range=[0, max_sub * 1.10 if max_sub else 1])
    )

    # -------- Year chart (unique records per year, NOT rounded) --------
    if "year" in dff_uniq.columns:
        year_data = dff_uniq.groupby("year")["record_id"].nunique().reset_index()
        year_data.columns = ["year", "count"]
        year_data = year_data.sort_values("year")
    else:
        year_data = pd.DataFrame(columns=["year", "count"])

    year_fig = px.bar(
        year_data,
        x="year", y="count",
        labels={"count": "Discharges", "year": "Year"},
        title="",
        text="count",
    )
    max_year = int(year_data["count"].max()) if not year_data.empty else 0
    year_fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
    year_fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(automargin=True),
        yaxis=dict(range=[0, max_year * 1.10 if max_year else 1])
    )

    # -------- Tables (unique records, like Power BI side tables) --------
    def generate_table(column, categories=None):
        if column not in dff_uniq.columns:
            return dbc.Alert(f"Column '{column}' not found in data.", color="warning", className="mb-0")
        grouped = dff_uniq.groupby(column)["record_id"].nunique().reset_index()
        grouped.columns = [column, "count"]
        if categories:
            grouped[column] = pd.Categorical(grouped[column], categories=categories, ordered=True)
            grouped = grouped.sort_values(column)
        # format counts with commas
        grouped["count"] = grouped["count"].map(lambda x: f"{int(x):,}")
        return dbc.Table.from_dataframe(grouped, striped=True, bordered=True, hover=True)

    # Extract age groups dynamically from the filtered data
    age_groups = sorted([v for v in dff_uniq["age_group"].unique() if v != "Unknown"]) + (["Unknown"] if "Unknown" in dff_uniq["age_group"].values else []) if "age_group" in dff_uniq.columns and not dff_uniq.empty else None

    return (
        substance_fig,
        year_fig,
        generate_table("county"),
        generate_table("age_group", age_groups),
        generate_table("sex"),
    )


if __name__ == "__main__":
    app.run(debug=True)
