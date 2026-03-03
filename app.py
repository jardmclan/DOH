import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import sqlite3
import math

# Helper function to load SQL from file
def load_sql_query(name, path="queries.sql"):
    with open(path, "r") as file:
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
    return query_map[name]

# Load data
conn = sqlite3.connect("DOH_AMHD_NO_PII.db")

df_raw = pd.read_sql_query(load_sql_query("load_discharge_data_view_diag_su"), conn)
conn.close()

# Compute total
df = df_raw.drop_duplicates(subset='record_id')
raw_total = df['record_id'].nunique()
rounded_total = int(math.ceil(raw_total / 10.0) * 10)

# Dash App
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    html.H2("Discharges Related to Substance Use", className="text-center my-4 text-white bg-dark p-3"),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H2(f"{rounded_total:,}", className="card-title text-white"),
                    html.H6("Number of Emergency Discharges Related to Substance Use", className="card-subtitle text-white"),
                    html.Small("", className="text-white-50")
                ])
            ], className="bg-success text-center")
        )
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H5("Filters"),
            dcc.Dropdown(df['county'].unique(), id='county-filter', placeholder="Select County"),
            dcc.Dropdown(df['city'].unique(), id='city-filter', placeholder="Select City"),
            dcc.Dropdown(df['hawaii_residency'].unique(), id='hawaii-residency-filter', placeholder="Select Hawaii Resident"),
            dcc.Dropdown(df['age_group'].unique(), id='age-filter', placeholder="Select Age Group"),
            dcc.Dropdown(df['sex'].unique(), id='sex-filter', placeholder="Select Sex"),
        ], width=3),

        dbc.Col([
            dcc.Graph(id="substance-bar")
        ], width=9)
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(html.Div(id='table-county'), width=4),
        dbc.Col(html.Div(id='table-age'), width=4),
        dbc.Col(html.Div(id='table-sex'), width=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="year-bar", style={"height": "360px", "maxWidth": "480px"}), width={"size": 4, "offset": 8})
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
    Input("sex-filter", "value")
)
def update_dashboard(county, city, hawaii_residency, age, sex):
    dff = df_raw.drop_duplicates(subset='record_id')
    if county: dff = dff[dff['county'] == county]
    if city: dff = dff[dff['city'] == city]
    if hawaii_residency: dff = dff[dff['hawaii_residency'] == hawaii_residency]
    if age: dff = dff[dff['age_group'] == age]
    if sex: dff = dff[dff['sex'] == sex]

    # Substance Chart
    substance_counts = dff.groupby('substance')['record_id'].nunique().reset_index()
    substance_counts.columns = ['substance', 'count']
    substance_counts = substance_counts[substance_counts['count'] >= 10].sort_values('count')
    substance_fig = px.bar(
        substance_counts,
        x='count', y='substance', orientation='h',
        title="Number of Discharges by Substance",
        labels={'count': 'Number of Discharges', 'substance': 'Substance Type'}
    )
    substance_fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))

    # Year Chart (still rounded)
    year_data = dff.groupby('year')['record_id'].nunique().reset_index()
    year_data.columns = ['year', 'count']
    year_data['count'] = year_data['count'].apply(lambda x: int(math.ceil(x / 10.0) * 10))
    year_data = year_data.sort_values('year')
    year_fig = px.bar(
        year_data,
        x='count', y='year', orientation='h',
        labels={'count': 'Number of Discharges', 'year': 'Year'},
        title="Discharges by Year"
    )
    year_fig.update_layout(
        height=360,
        margin=dict(l=0, r=0, t=30, b=0)
    )

    # Table Generator (no rounding)
    def generate_table(column, categories=None):
        grouped = dff.groupby(column)['record_id'].nunique().reset_index()
        grouped.columns = [column, 'count']
        if categories:
            grouped[column] = pd.Categorical(grouped[column], categories=categories, ordered=True)
            grouped = grouped.sort_values(column)
        return dbc.Table.from_dataframe(grouped, striped=True, bordered=True, hover=True)

    # Extract age groups dynamically from the filtered data
    age_groups = sorted([v for v in dff["age_group"].unique() if v != "Unknown"]) + (["Unknown"] if "Unknown" in dff["age_group"].values else []) if "age_group" in dff.columns and not dff.empty else None

    return (
        substance_fig,
        year_fig,
        generate_table('county'),
        generate_table('age_group', age_groups),
        generate_table('sex')
    )


if __name__ == "__main__":
    app.run(debug=True)
