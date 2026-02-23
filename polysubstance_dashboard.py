# polysubstance_dashboard_db.py — pure layout + callbacks (desktop-safe, mobile-aware)

# - db_utils: to connect to database (SQLite or MSSQL based on config)
# - pandas / numpy: to clean and shape the data
# - dash + dash_bootstrap_components: to build the web page and styles
# - plotly: to draw the charts
from pathlib import Path

import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback
import plotly.express as px
import plotly.io as pio

from theme import register_template
from db_utils import execute_query

# This applies our custom Plotly look (colors, fonts, etc.) everywhere in this app.
register_template()  # set your Plotly template globally

# Simple shortcuts so we can change these in one place if paths ever move
QUERIES_PATH = "queries.sql"
PREFERRED_QUERY = "load_polysubstance_data"
FALLBACK_QUERY  = "load_main_data"


# ---------- SQL loader ----------
def load_sql_query(name: str, path: str = QUERIES_PATH) -> str:
    """
    Look inside queries.sql and pull out the SQL text that matches `name`.

    Why:
    - Keeps long SQL out of this Python file.
    - Makes it easier to update queries without touching code.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # queries.sql is broken up into blocks that start with "-- name:"
    blocks = text.split("-- name:")
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        lines = b.split("\n")
        block_name = lines[0].strip()
        sql = "\n".join(lines[1:]).strip()
        if block_name == name:
            return sql

    # If we get here, we didn't find a block with that name
    raise KeyError(f"Named query '{name}' not found in {path}.")


# ---------- DB → DataFrame ----------
def load_df():
    """
    Load the main dataset from the SQLite database.

    Steps:
      1. Try to use the polysubstance-only query.
      2. If it doesn't exist, fall back to the main data query.
      3. Read the result into a table (DataFrame).
      4. Clean up some columns so they behave nicely in filters and charts.
    """
    try:
        # First choice: use the specific polysubstance query
        sql = load_sql_query(PREFERRED_QUERY, QUERIES_PATH)
        print(f"[load_df] Using query: {PREFERRED_QUERY}")
    except KeyError:
        # If that fails, fall back to the more general query
        sql = load_sql_query(FALLBACK_QUERY, QUERIES_PATH)
        print(f"[load_df] Using query: {FALLBACK_QUERY}")

    # Execute query using db_utils (automatically uses correct database)
    df = execute_query(sql)

    # If nothing comes back, it’s better to crash early than show an empty dashboard.
    if df.empty:
        raise RuntimeError("Query returned 0 rows. Check DB and queries.sql.")

    # These columns are treated as category-like text fields.
    # Here we clean them up to avoid weird blanks or "nan" strings.
    want_obj = ["county", "city", "hawaii_residency", "age_group", "sex", "substance"]
    for c in want_obj:
        if c in df.columns:
            df[c] = (
                df[c].astype(str).str.strip()
                .replace({"nan": np.nan, "None": np.nan})
                .fillna("Unknown")
            )

    # Make sure the year column is a proper integer type so graphs order it correctly.
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    # Print some quick info in the console for debugging.
    print(f"[load_df] rows={len(df):,}  cols={list(df.columns)}")
    print("Plotly default template:", pio.templates.default)
    return df


# Load the cleaned dataset once when the module is imported.
# All callbacks reuse this instead of hitting the DB over and over.
df_raw = load_df()
print("[debug] queries.sql path:", Path(QUERIES_PATH).resolve())

# Guard rails: limit years to our window and drop "unknown" ages
if "year" in df_raw.columns:
    # Make sure year is numeric and in our chosen range (2018–2024)
    df_raw["year"] = pd.to_numeric(df_raw["year"], errors="coerce").astype("Int64")
    mask_year = df_raw["year"].between(2018, 2024, inclusive="both")
else:
    mask_year = True  # If we don't have a year, don't filter by year

def _is_unknown_age(val):
    """
    Decide if an age group value is basically "unknown".

    We treat blanks or common shortcuts (unknown, unk, n/a, etc.) as unknown.
    """
    s = (str(val) if val is not None else "").strip().lower()
    return s in {"", "unknown", "unk", "n/a", "na"}

# Remove rows with unknown age groups (only if that column exists)
mask_age = ~df_raw["age_group"].apply(_is_unknown_age) if "age_group" in df_raw.columns else True

# Keep only rows that pass both filters
df_raw = df_raw[mask_year & mask_age].copy()


# ---------- filter options ----------
def sort_opts(series):
    """
    Turn a column into a sorted list of unique values.

    We also push "Unknown" to the end of the list so the filter menus
    look cleaner and more natural to read.
    """
    vals = pd.Series(series.unique()).astype(str)
    return sorted([v for v in vals if v != "Unknown"]) + (["Unknown"] if "Unknown" in vals.values else [])

def opts(values):
    """
    Wrap a raw list of values into the format Dash expects for dropdown options:
    each one needs a label and value.
    """
    return [{"label": v, "value": v} for v in values]

# Build the dropdown choices for each filter, only if those columns exist.
substance_opts = sort_opts(df_raw["substance"]) if "substance" in df_raw.columns else []
county_opts    = sort_opts(df_raw["county"])    if "county"    in df_raw.columns else []
age_opts       = sort_opts(df_raw["age_group"]) if "age_group" in df_raw.columns else []
sex_opts       = sort_opts(df_raw["sex"])       if "sex"       in df_raw.columns else []
year_opts      = sorted(df_raw["year"].dropna().unique().tolist()) if "year" in df_raw.columns else []

# Total number of unique records, used for the big KPI card.
kpi_total = df_raw["record_id"].nunique() if "record_id" in df_raw.columns else 0


# ---------- small helpers ----------
def _apply_filter(frame, col, val):
    """
    Helper to apply a filter to a column.

    - If val is empty or None, we leave the data alone.
    - If val is a list, we keep any rows that match any of those values.
    - If val is a single value, we match exactly that.

    Why: we use the same pattern for all filters, so this keeps the code
    short and consistent.
    """
    if val is None or (isinstance(val, (list, tuple)) and len(val) == 0):
        return frame
    if isinstance(val, (list, tuple)):
        return frame[frame[col].isin(val)]
    return frame[frame[col] == val]


def _wrap_label(label: str, max_len: int = 22):
    """
    Break long labels into two lines so they don't stretch the chart.

    We look for the last space before `max_len` and insert a line break there.
    """
    s = str(label)
    if len(s) <= max_len:
        return s
    cut = s.rfind(" ", 0, max_len)
    if cut == -1:
        return s
    return s[:cut] + "<br>" + s[cut+1:]


def graph_block(base_id: str, title_text: str, height: str):
    """
    Build a reusable chart "card" with:

      Store:  f"{base_id}-store"  (remembers if title is hidden or not)
      Button: f"{base_id}-btn"    (user clicks to toggle that store)
      Title:  f"{base_id}-title"  (hidden when Tools is “on”)
      Graph:  f"{base_id}"        (the actual plot, tools bar always visible)

    Why: this keeps plot sections consistent across the page and helps
    avoid repeating the same layout code every time we add a graph.
    """
    return html.Div(
        [
            # This hidden store holds a simple True/False flag.
            dcc.Store(id=f"{base_id}-store", data=False),

            # Header row: Tools button + title text
            html.Div(
                [
                    dbc.Button(
                        "Tools", id=f"{base_id}-btn", n_clicks=0,
                        color="primary", size="sm", className="me-2"
                    ),
                    html.H5(title_text, id=f"{base_id}-title", className="m-0"),
                ],
                className="d-flex align-items-center mb-2"
            ),

            # The graph itself; Plotly tools bar (modebar) is always ON.
            dcc.Graph(
                id=base_id,
                style={"height": height, "width": "100%"},
                config={"displayModeBar": True, "displaylogo": False},
            ),
        ],
        className="mb-4",
        # Let the tools bar hang outside the card if needed so it’s not cut off.
        style={"overflow": "visible"},
    )


# ---------- layout factory (mobile-aware) ----------
def layout_for(is_mobile: bool = False):
    """
    Build the full page layout.

    We accept a flag `is_mobile` so we can adjust chart heights
    for smaller screens.

    The page is split into three columns:
      LEFT:  KPI + filters
      CENTER: main bar/stacked charts
      RIGHT: treemap + small summary tables
    """
    # Make charts taller on phones so they are easier to read.
    h_bar = "60vh" if is_mobile else "400px"
    h_stack = "55vh" if is_mobile else "360px"
    h_tree = "46vh" if is_mobile else "280px"

    # LEFT: KPI + filters
    left = dbc.Col([
        # Big green card showing total polysubstance discharges.
        dbc.Card(dbc.CardBody([
            html.H1(f"{kpi_total:,}", className="m-0"),
            html.Div(
                "2018–2024: Number of Discharges Related to Polysubstance Use",
                className="text-white-50"
            ),
        ]), className="bg-success text-center mb-3"),

        # Quick button to clear all filter selections in one click.
        dbc.Button(
            "Reset All Filters", id="reset-btn",
            className="mb-3", color="secondary", n_clicks=0
        ),

        # Filter controls grouped inside a card.
        dbc.Card(dbc.CardBody([
            html.H5("Filter Data", tabIndex=2),

            html.Label("Substance Type", htmlFor="f-substance", tabIndex=3, className="form-label"),
            dcc.Dropdown(
                id="f-substance", options=opts(substance_opts), multi=True,
                placeholder="All", className="mb-3",
                persistence=True, persistence_type="session"
            ),

            html.Label("Age Group", htmlFor="f-age", tabIndex=4, className="form-label"),
            dcc.Dropdown(
                id="f-age", options=opts(age_opts), multi=True,
                placeholder="All", className="mb-3",
                persistence=True, persistence_type="session"
            ),

            html.Label("Sex", htmlFor="f-sex", tabIndex=5, className="form-label"),
            dcc.Dropdown(
                id="f-sex", options=opts(sex_opts), multi=True,
                placeholder="All", className="mb-3",
                persistence=True, persistence_type="session"
            ),

            html.Label("County", htmlFor="f-county", tabIndex=6, className="form-label"),
            dcc.Dropdown(
                id="f-county", options=opts(county_opts), multi=True,
                placeholder="All", className="mb-3",
                persistence=True, persistence_type="session"
            ),

            html.Label("Calendar Year", htmlFor="f-year", tabIndex=7, className="form-label"),
            dcc.Dropdown(
                id="f-year", options=opts(year_opts), multi=True,
                placeholder="All", className="mb-0",
                persistence=True, persistence_type="session"
            ),
        ]), id="ps-filters"),
    ], xs=12, md=3)

    # CENTER: main charts focused on substance and county over time
    center = dbc.Col([
        graph_block("bar-top-substances", "Top Substances (Polysubstance Records)", h_bar),
        # Hidden description for screen readers.
        html.P(
            "Horizontal bar chart of top substances among polysubstance records.",
            className="sr-only"
        ),

        graph_block("stack-year-county", "Discharges by Year and County", h_stack),
        html.P(
            "Stacked bar chart of discharges by year and county. Use the legend to toggle counties.",
            className="sr-only"
        ),
    ], xs=12, md=6)

    # RIGHT: treemap + two small summary tables
    right = dbc.Col([
        graph_block("treemap-county", "County Share (Unique Discharges)", h_tree),
        html.P(
            "Treemap showing share of unique discharges by county.",
            className="sr-only"
        ),

        # Two tables side-by-side (Age + Sex)
        # On phones they still show 2-up (xs=6 each).
        dbc.Row([
            dbc.Col([
                html.H5("Age Group", className="mb-2"),
                html.Div(id="tbl-age", className="sidebar-table"),
            ], xs=6),
            dbc.Col([
                html.H5("Sex", className="mb-2"),
                html.Div(id="tbl-sex", className="sidebar-table"),
            ], xs=6),
        ], className="g-3"),
    ], xs=12, md=3)

    # Wrap everything up in one fluid container.
    return dbc.Container([
        # Accessibility: a "skip" link so keyboard users can jump right to filters.
        html.A(
            "Skip to filters", href="#ps-filters",
            className="visually-hidden-focusable", tabIndex=0
        ),

        html.H2(
            "Polysubstance Discharges — Exploratory View (2018–2024)",
            className="text-white bg-dark p-3 text-center mb-4",
            tabIndex=0
        ),

        dbc.Row([left, center, right], className="g-3"),
    ], fluid=True)




# Keep desktop default layout for older code that imports `layout` directly.
layout = layout_for(is_mobile=False)


# ---------- callbacks (figures + tables) ----------
@callback(
    Output("bar-top-substances", "figure"),
    Output("stack-year-county", "figure"),
    Output("treemap-county", "figure"),
    Output("tbl-age", "children"),
    Output("tbl-sex", "children"),
    Input("f-substance", "value"),
    Input("f-age", "value"),
    Input("f-sex", "value"),
    Input("f-county", "value"),
    Input("f-year", "value"),
)
def update(substance, age, sex, county, year):
    dff = df_raw.copy()

    if "substance" in dff.columns:     dff = _apply_filter(dff, "substance", substance)
    if "age_group" in dff.columns:     dff = _apply_filter(dff, "age_group", age)
    if "sex" in dff.columns:           dff = _apply_filter(dff, "sex", sex)
    if "county" in dff.columns:        dff = _apply_filter(dff, "county", county)
    if "year" in dff.columns: dff = _apply_filter(dff, "year", year)

    # ---------- Bar: Top substances ----------
    if {"substance", "record_id"}.issubset(dff.columns) and not dff.empty:
        sub_counts = (
            dff.groupby("substance")["record_id"]
               .nunique().reset_index(name="discharges")
               .sort_values("discharges", ascending=True)
               .tail(10)
        )

        sub_counts["substance_wrapped"] = sub_counts["substance"].apply(_wrap_label)

        fig_sub = px.bar(
            sub_counts,
            x="discharges",
            y="substance_wrapped",
            orientation="h",
            labels={
                "discharges": "Number of Discharges",
                "substance_wrapped": "Substance Type",
            },
            text="discharges",
        )
        fig_sub.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
            cliponaxis=False
        )
        max_x = int(sub_counts["discharges"].max()) if not sub_counts.empty else 0
        fig_sub.update_layout(
            margin=dict(l=0, r=12, t=50, b=0),   # <-- extra top space for tools
            xaxis=dict(
                range=[0, max_x * 1.15 if max_x else 1],
                automargin=True
            ),
            yaxis=dict(automargin=True),
        )
    else:
        fig_sub = px.bar()

    # ---------- Stacked Bar: Year × County ----------
    if {"year", "county", "record_id"}.issubset(dff.columns) and not dff.empty:
        yearly_counts = (
            dff.drop_duplicates("record_id")
               .groupby(["year", "county"])["record_id"]
               .nunique().reset_index(name="discharges")
        )
        yearly_counts["label"] = yearly_counts["discharges"].map(lambda x: f"{int(x):,}")

        fig_year_county = px.bar(
            yearly_counts,
            x="year", y="discharges",
            color="county",
            barmode="stack",
            labels={"year": "Year", "discharges": "Discharges"},
            text="label",
        )
        fig_year_county.update_layout(
            margin=dict(l=0, r=12, t=50, b=0),   # <-- extra top space
            xaxis=dict(dtick=1, automargin=True),
            uniformtext_minsize=12,
            uniformtext_mode="show",
        )
        fig_year_county.update_traces(
            textposition="inside",
            insidetextanchor="middle",
            cliponaxis=False,
            textfont_size=12
        )
    else:
        fig_year_county = px.bar()

    # ---------- Treemap: county share ----------
    uniq = dff.drop_duplicates("record_id")
    if {"county", "record_id"}.issubset(uniq.columns) and not uniq.empty:
        county_counts = uniq.groupby("county")["record_id"].nunique().reset_index(name="discharges")
        fig_tree = px.treemap(county_counts, path=["county"], values="discharges")
        fig_tree.update_traces(
            texttemplate="%{label}<br>%{value:,}",
            hovertemplate="%{label}: %{value:,} (%{percentRoot:.1%})<extra></extra>"
        )
        fig_tree.update_layout(
            margin=dict(l=0, r=0, t=50, b=0)   # <-- extra top space
        )
    else:
        fig_tree = px.treemap()

    # ---------- Small tables ----------
    def simple_table(df, col, ordered=None):
        if col not in df.columns or df.empty:
            return dbc.Alert(f"No data for '{col}'.", color="warning", className="mb-0")

        g = df.groupby(col)["record_id"].nunique().reset_index(name="discharges")

        if ordered:
            g[col] = pd.Categorical(g[col], categories=ordered, ordered=True)
            g = g.sort_values(col)

        g["discharges"] = g["discharges"].map(lambda x: f"{int(x):,}")

        return dbc.Table.from_dataframe(
            g,
            striped=True,
            bordered=True,
            hover=True,
            size="sm"
        )

    tbl_age = simple_table(uniq, "age_group", ["<18", "18-44", "45-64", "65-74", "75+"])
    tbl_sex = simple_table(uniq, "sex")

    return fig_sub, fig_year_county, fig_tree, tbl_age, tbl_sex



# ---------- Reset filters ----------
@callback(
    Output("f-substance", "value"),
    Output("f-age", "value"),
    Output("f-sex", "value"),
    Output("f-county", "value"),
    Output("f-year", "value"),
    Input("reset-btn", "n_clicks"),
    prevent_initial_call=True
)
def _reset_filters(n):
    """
    When the user clicks the Reset button, clear every filter.

    We return empty lists so Dash treats them as "no selection".
    """
    return [], [], [], [], []


# ---------- Tool toggles (now only hide/show the title) ----------
@callback(
    Output("bar-top-substances-title", "style"),
    Input("bar-top-substances-store", "data"),
)
def _cfg_sub(show):
    """
    When the Tools button is used for the Top Substances chart,
    just hide or show the title text. The tools bar stays on.
    """
    return {"display": "none"} if show else {}

@callback(
    Output("stack-year-county-title", "style"),
    Input("stack-year-county-store", "data"),
)
def _cfg_stack(show):
    """
    Same idea for the Year × County stacked bar chart title.
    """
    return {"display": "none"} if show else {}

@callback(
    Output("treemap-county-title", "style"),
    Input("treemap-county-store", "data"),
)
def _cfg_tree(show):
    """
    Same idea for the county treemap title.
    """
    return {"display": "none"} if show else {}


# Buttons toggle their stores (so you can click tools on/off repeatedly)
@callback(
    Output("bar-top-substances-store", "data"),
    Input("bar-top-substances-btn", "n_clicks"),
    State("bar-top-substances-store", "data"),
    prevent_initial_call=True
)
def _btn_sub(n, cur):
    """
    Flip the tools flag for the Top Substances chart each time the
    Tools button is clicked.
    """
    return not bool(cur)

@callback(
    Output("stack-year-county-store", "data"),
    Input("stack-year-county-btn", "n_clicks"),
    State("stack-year-county-store", "data"),
    prevent_initial_call=True
)
def _btn_stack(n, cur):
    """
    Flip the tools flag for the Year × County chart.
    """
    return not bool(cur)

@callback(
    Output("treemap-county-store", "data"),
    Input("treemap-county-btn", "n_clicks"),
    State("treemap-county-store", "data"),
    prevent_initial_call=True
)
def _btn_tree(n, cur):
    """
    Flip the tools flag for the county treemap.
    """
    return not bool(cur)
