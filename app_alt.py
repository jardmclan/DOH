# app_alt.py — Discharges (Alt Views) page

# These are the tools we use:
# - db_utils: to connect to database (SQLite or MSSQL based on config)
# - pandas: to shape and clean up the data
# - dash / dbc / plotly: to build the website layout and graphs
from db_utils import execute_query
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback
import plotly.express as px
from theme import register_template

# This applies our custom Plotly theme (colors, fonts, etc.)
# so all graphs match the rest of the dashboard.
register_template()

# ----------------------------
# Data helpers
# ----------------------------

def load_sql_query(name, path="queries.sql"):
    """
    This helper looks inside the queries.sql file and pulls out
    the specific SQL block we want by name.

    Why: this keeps all the SQL in one file instead of hard-coding
    long queries directly in the Python file.
    """
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    # The SQL file is split into blocks marked with "-- name:"
    blocks = sql.split("-- name:")
    m = {}
    for b in blocks:
        # Skip any empty chunks
        if not b.strip():
            continue
        # First line after "-- name:" is the name, the rest is the SQL text
        lines = b.strip().split("\n")
        m[lines[0].strip()] = "\n".join(lines[1:]).strip()
    # If we typed the wrong query name, complain loudly
    if name not in m:
        raise KeyError(f"Named query '{name}' not found in {path}.")
    return m[name]

def load_main_dataframe_from_db():
    """
    This helper:
      1. Loads the main SQL query by name.
      2. Connects to the database and runs the query.
      3. Cleans up some columns so the rest of the app is easier to write.

    Why: having this in one place avoids repeating the same database
    logic in multiple callbacks.
    
    Note: Uses either SQLite or MSSQL automatically based on config.
    """
    # Grab the SQL for our main data
    sql = load_sql_query("load_main_data")
    
    # Execute query using db_utils (automatically uses correct database)
    df = execute_query(sql)

    # If there is no data, we stop early instead of showing a broken page
    if df.empty:
        raise RuntimeError("Query returned 0 rows.")

    # Make the year column numeric when possible so graphs treat it as numbers
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    # For these columns, replace missing values with "Unknown"
    # so we don't get blank labels in filters and tables.
    for col in ["county", "city", "hawaii_residency", "age_group", "sex", "substance"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")
    return df

# Load the full dataset once at startup.
# The callbacks will reuse this instead of hitting the database every time.
df_raw = load_main_dataframe_from_db()


# Count how many unique records we have to show on the KPI card.
total_unique = df_raw["record_id"].nunique()

def sort_opts(series):
    """
    Turn a column into a sorted list of unique values.

    We also make sure "Unknown" always shows up at the end of the list
    so the drop-down menus look cleaner.
    """
    vals = pd.Series(series.unique()).astype(str)
    vals = sorted([v for v in vals if v != "Unknown"]) + (["Unknown"] if "Unknown" in vals.values else [])
    return vals

# Build the lists of choices for each filter only if the column exists.
# Why: this makes the code more flexible if the data shape changes later.
county_opts    = sort_opts(df_raw["county"])    if "county"    in df_raw.columns else []
city_opts      = sort_opts(df_raw["city"])      if "city"      in df_raw.columns else []
hawaii_residency_opts = sort_opts(df_raw["hawaii_residency"]) if "hawaii_residency" in df_raw.columns else []
age_opts       = sort_opts(df_raw["age_group"]) if "age_group" in df_raw.columns else []
sex_opts       = sort_opts(df_raw["sex"])       if "sex"       in df_raw.columns else []

def opts_list(values):
    """
    Turn a simple list of values into the format Dash expects for
    drop-down choices (label + value).
    """
    return [{"label": v, "value": v} for v in values]

# ----------------------------
# Reusable graph block (Tools toggle + title + graph)
# ----------------------------

def graph_block(base_id: str, title_text: str, height_px: str, tools_default=False):
    """
    Make a standard "card" that holds:
      - a hidden store that remembers if the tools are on/off
      - a small Tools button that the user clicks
      - a title for the plot
      - the actual graph area

    Why: we use this pattern for several plots, so this function keeps
    the layout consistent and avoids repeating the same code over and over.
    """
    return html.Div(
        [
            # This keeps track of whether the tools bar should show for this plot.
            dcc.Store(id=f"{base_id}-store", data=bool(tools_default)),

            # Header row with the Tools button and the plot title side-by-side.
            html.Div(
                [
                    dbc.Button(
                        "Tools",
                        id=f"{base_id}-btn",
                        n_clicks=0,
                        color="primary",
                        size="sm",
                        className="me-2"
                    ),
                    html.H5(title_text, id=f"{base_id}-title", className="m-0"),
                ],
                # This class keeps things laid out in one row and avoids overlap.
                className="plot-card-header mb-2"
            ),

            # The actual graph. Modebar (tools) is always on now.
            dcc.Graph(
                id=base_id,
                style={"height": height_px, "width": "100%"},
                config={"displayModeBar": True, "displaylogo": False},
            ),
        ],
        className="mb-4",
        # This makes sure the tools bar is never cut off visually.
        style={"overflow": "visible"}
    )

# ----------------------------
# UI
# ----------------------------

# This link helps keyboard and screen reader users jump straight to the filters.
skip_link = html.A(
    "Skip to filters",
    href="#alt-filters",
    className="visually-hidden-focusable",
    tabIndex=0
)

# Big green card that shows the total number of discharges.
# Why: gives users a quick "at a glance" number when they open the page.
kpi_card = dbc.Card(
    dbc.CardBody([
        html.H4("Total Discharges", className="card-title text-white"),
        html.H2(f"{total_unique:,}", className="text-white"),
        html.Small("Count of unique records from 2018 to 2024", className="text-white-50")
    ]),
    className="bg-success text-center mb-4"
)

# Card holding all the filter controls down the left side.
# Each filter uses the options we built from the data above.
filters_card = dbc.Card(
    dbc.CardBody([
        html.H5("Filter Data", tabIndex=1),

        html.Label("County", htmlFor="county-filter", tabIndex=2, className="form-label"),
        dcc.Dropdown(
            id="county-filter", options=opts_list(county_opts), multi=True,
            placeholder="County", className="mb-2",
            persistence=True, persistence_type="session"
        ),

        html.Label("City", htmlFor="city-filter", tabIndex=3, className="form-label"),
        dcc.Dropdown(
            id="city-filter", options=opts_list(city_opts), multi=True,
            placeholder="City", className="mb-2",
            persistence=True, persistence_type="session"
        ),

        html.Label("Hawaii Resident", htmlFor="hawaii-residency-filter", tabIndex=4, className="form-label"),
        dcc.Dropdown(
            id="hawaii-residency-filter", options=opts_list(hawaii_residency_opts), multi=True,
            placeholder="Hawaii Resident", className="mb-2",
            persistence=True, persistence_type="session"
        ),

        html.Label("Age Group", htmlFor="age-filter", tabIndex=5, className="form-label"),
        dcc.Dropdown(
            id="age-filter", options=opts_list(age_opts), multi=True,
            placeholder="Age Group", className="mb-2",
            persistence=True, persistence_type="session"
        ),

        html.Label("Sex", htmlFor="sex-filter", tabIndex=6, className="form-label"),
        dcc.Dropdown(
            id="sex-filter", options=opts_list(sex_opts), multi=True,
            placeholder="Sex", className="mb-0",
            persistence=True, persistence_type="session"
        ),
    ]),
    id="alt-filters",
    className="mb-4"
)

def layout_for(is_mobile: bool = False):
    """
    Build the full page layout, with slightly different heights if we
    are on a phone vs a larger screen.

    Why: on small screens we want taller plots so they are easier to read,
    but on desktops shorter plots look better side-by-side.
    """
    # Adjust plot heights depending on screen size.
    line_h = "60vh" if is_mobile else "400px"
    bar_h  = "55vh" if is_mobile else "360px"
    pie_h  = "46vh" if is_mobile else "260px"

    # Left column: KPI and filters.
    left_col = dbc.Col([kpi_card, filters_card], xs=12, md=3)

    # Center column: the main line and bar charts.
    center_col = dbc.Col(
        [
            graph_block("county-year-lines", "Discharges by County and Year", line_h),
            # Screen-reader description only; not visible on screen.
            html.P(
                "Line chart of discharges by county over time. Use the legend to toggle counties.",
                className="sr-only"
            ),
            graph_block("sex-year-stacked", "Yearly Discharges by Gender", bar_h),
            html.P(
                "Stacked bar chart of yearly discharges by gender. Use the legend to toggle categories.",
                className="sr-only"
            ),
        ],
        xs=12, md=6
    )

    # Right column:
    # - Two small summary tables (by county and by age group)
    # - A pie chart for gender
    #
    # On phones, the two small tables sit side-by-side.
    # On bigger screens, they stack vertically.
    right_col = dbc.Col(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H6("By County", className="mb-2"),
                            html.Div(
                                id="table-county",
                                className="mobile-side-table",
                                style={"overflowX": "auto"}
                            ),
                        ],
                        xs=6, md=12, className="pe-1 mb-3",
                    ),
                    dbc.Col(
                        [
                            html.H6("By Age Group", className="mb-2"),
                            html.Div(
                                id="table-age",
                                className="mobile-side-table",
                                style={"overflowX": "auto"}
                            ),
                        ],
                        xs=6, md=12, className="ps-1 mb-3",
                    ),
                ],
                className="g-2"
            ),
            graph_block("sex-pie", "Discharges by Gender", pie_h),
            html.P("Pie chart of discharges by gender.", className="sr-only"),
        ],
        xs=12, md=3
    )

    # Wrap everything in a fluid container so it stretches with the screen.
    return dbc.Container(
        [
            skip_link,
            dbc.Row([left_col, center_col, right_col], className="g-3")
        ],
        fluid=True,
        className="p-2"
    )

# This is the default layout used when the app imports this file.
# We pass False here since desktop is the standard case.
layout = layout_for(is_mobile=False)

# ----------------------------
# Figures + tables (no plotly titles)
# ----------------------------

@callback(
    Output("county-year-lines", "figure"),
    Output("sex-year-stacked", "figure"),
    Output("table-county", "children"),
    Output("table-age", "children"),
    Output("sex-pie", "figure"),
    Input("county-filter", "value"),
    Input("city-filter", "value"),
    Input("hawaii-residency-filter", "value"),
    Input("age-filter", "value"),
    Input("sex-filter", "value"),
)
def update_dashboard(county, city, hawaii_residency, age, sex):
    """
    This function runs every time the user changes a filter.

    It:
      - Applies all the filters to the data,
      - Builds two graphs (line + stacked bar),
      - Builds two tables,
      - Builds the pie chart.
    """

    def apply_filter(frame, col, val):
        """
        Small helper so we don't repeat the same filter logic.

        If the user did not pick anything, we leave the data alone.
        If they picked one or more values, we only keep matching rows.
        """
        if val is None or (isinstance(val, (list, tuple)) and len(val) == 0):
            return frame
        if isinstance(val, (list, tuple)):
            return frame[frame[col].isin(val)]
        return frame[frame[col] == val]

    # Start from the full dataset each time.
    dff = df_raw.copy()

    # Only apply filters for columns that actually exist.
    if "county" in dff.columns:          dff = apply_filter(dff, "county", county)
    if "city" in dff.columns:            dff = apply_filter(dff, "city", city)
    if "hawaii_residency" in dff.columns: dff = apply_filter(dff, "hawaii_residency", hawaii_residency)
    if "age_group" in dff.columns:       dff = apply_filter(dff, "age_group", age)
    if "sex" in dff.columns:             dff = apply_filter(dff, "sex", sex)

    # Drop duplicate record_ids so each record is only counted once.
    dff_uniq = dff.drop_duplicates(subset="record_id")

    # ---------- Line chart: Discharges by County and Year ----------
    if {"county", "year"}.issubset(dff_uniq.columns):
        # Count how many unique records per year + county
        by_cy = (
            dff_uniq.groupby(["year", "county"])["record_id"]
            .nunique()
            .reset_index(name="count")
        )
        # Order counties in a consistent way for the legend
        counties = sort_opts(dff_uniq["county"]) if "county" in dff_uniq.columns else []
        if counties:
            by_cy["county"] = pd.Categorical(by_cy["county"], categories=counties, ordered=True)

        # Build the line graph
        line_fig = px.line(
            by_cy,
            x="year",
            y="count",
            color="county",
            markers=True,
            labels={"year": "Year", "count": "Discharges", "county": "County"},
        )
        # Customize hover text and margins for a cleaner look
        line_fig.update_traces(
            hovertemplate="Year %{x}<br>%{y:,} discharges<extra></extra>"
        )
        line_fig.update_layout(
            margin=dict(l=0, r=20, t=10, b=0),
            xaxis=dict(dtick=1)
        )
    else:
        # If we don't have the needed columns, return an empty figure
        line_fig = px.line()

    # ---------- Stacked bar chart: Yearly Discharges by Gender ----------
    if {"year", "sex"}.issubset(dff_uniq.columns):
        # Count how many unique records per year + gender
        by_ys = (
            dff_uniq.groupby(["year", "sex"])["record_id"]
            .nunique()
            .reset_index(name="count")
            .sort_values(["year", "sex"])
        )
        sex_bar = px.bar(
            by_ys,
            x="year",
            y="count",
            color="sex",
            barmode="stack",
            labels={"year": "Year", "count": "Discharges", "sex": "Gender"},
            # Show the counts inside each bar segment
            text=by_ys["count"].map(lambda x: f"{int(x):,}")
        )
        sex_bar.update_traces(
            textposition="inside",
            insidetextanchor="middle",
            cliponaxis=False
        )

        # Calculate total discharges per year to show on top of each stacked bar
        totals = by_ys.groupby("year")["count"].sum().reset_index()
        for _, row in totals.iterrows():
            sex_bar.add_annotation(
                x=row["year"],
                y=row["count"],
                text=f"{int(row['count']):,}",
                showarrow=False,
                yshift=10,
                font=dict(size=12)
            )

        # Give a bit of headroom above the tallest bar
        max_y = int(totals["count"].max()) if not totals.empty else 0
        sex_bar.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(automargin=True),
            yaxis=dict(range=[0, max_y * 1.15 if max_y else 1])
        )
    else:
        sex_bar = px.bar()

    # ---------- Helper for the summary tables ----------
    def tbl(column, categories=None):
        """
        Build a small table that shows the count of unique records
        for each value in the chosen column.

        If we pass in a list of categories, we use that order in the table.
        """
        if column not in dff_uniq.columns:
            return dbc.Alert(
                f"Column '{column}' not found.",
                color="warning",
                className="mb-0"
            )

        # Count records per category
        g = dff_uniq.groupby(column)["record_id"].nunique().reset_index()
        g.columns = [column, "count"]

        # Use the given category order if provided
        if categories:
            g[column] = pd.Categorical(g[column], categories=categories, ordered=True)
            g = g.sort_values(column)

        # Make the counts look nicer with commas
        g["count"] = g["count"].map(lambda x: f"{int(x):,}")

        # Build a styled table for the dashboard
        return dbc.Table.from_dataframe(g, striped=True, bordered=True, hover=True)

    # ---------- Pie chart: Discharges by Gender ----------
    if "sex" in dff_uniq.columns:
        pie_df = (
            dff_uniq.groupby("sex")["record_id"]
            .nunique()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        sex_pie = px.pie(
            pie_df,
            names="sex",
            values="count",
            hole=0.35
        )
        sex_pie.update_traces(
            textposition="inside",
            texttemplate="%{label}<br>%{percent:.1%} (%{value:,})",
            hovertemplate="%{label}: %{value:,} (%{percent:.1%})"
        )
        sex_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    else:
        sex_pie = px.pie()

    # Return all the updated visuals and tables to Dash
    return (
        line_fig,
        sex_bar,
        tbl("county"),
        tbl("age_group", ["<18", "18-44", "45-64", "65-74", "75+", "Unknown"]),
        sex_pie
    )

# ----------------------------
# Tool toggles — now only hide/show the title
# ----------------------------

@callback(
    Output("county-year-lines-title", "style"),
    Input("county-year-lines-store", "data"),
)
def _toggle_lines_cfg(show):
    """
    When the Tools button is used for the line chart,
    just hide or show the title text. The modebar is always on.
    """
    return {"display": "none"} if show else {}

@callback(
    Output("sex-year-stacked-title", "style"),
    Input("sex-year-stacked-store", "data"),
)
def _toggle_bars_cfg(show):
    """
    Same idea for the stacked bar chart title.
    """
    return {"display": "none"} if show else {}

@callback(
    Output("sex-pie-title", "style"),
    Input("sex-pie-store", "data"),
)
def _toggle_pie_cfg(show):
    """
    Same idea for the pie chart title.
    """
    return {"display": "none"} if show else {}

# ----------------------------
# Buttons flip their stores (toggle on/off)
# ----------------------------

@callback(
    Output("county-year-lines-store", "data"),
    Input("county-year-lines-btn", "n_clicks"),
    State("county-year-lines-store", "data"),
    prevent_initial_call=True
)
def _btn_lines(n, cur):
    """
    When the user clicks the Tools button on the line chart,
    flip the stored value (on -> off, off -> on).
    """
    return not bool(cur)

@callback(
    Output("sex-year-stacked-store", "data"),
    Input("sex-year-stacked-btn", "n_clicks"),
    State("sex-year-stacked-store", "data"),
    prevent_initial_call=True
)
def _btn_bars(n, cur):
    """
    Same toggle behavior for the stacked bar chart.
    """
    return not bool(cur)

@callback(
    Output("sex-pie-store", "data"),
    Input("sex-pie-btn", "n_clicks"),
    State("sex-pie-store", "data"),
    prevent_initial_call=True
)
def _btn_pie(n, cur):
    """
    Same toggle behavior for the pie chart.
    """
    return not bool(cur)
