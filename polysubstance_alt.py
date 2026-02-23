# polysubstance_alt.py — Alternative visualizations for substance co-occurrence patterns

from pathlib import Path
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from theme import register_template
from db_utils import execute_query

register_template()

# Configuration
QUERIES_PATH = "queries.sql"
PREFERRED_QUERY = "load_polysubstance_data"
FALLBACK_QUERY = "load_main_data"


# ---------- SQL loader ----------
def load_sql_query(name: str, path: str = QUERIES_PATH) -> str:
    """Load a named SQL query from queries.sql file."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
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
    raise KeyError(f"Named query '{name}' not found in {path}.")


# ---------- Load data ----------
def load_df():
    """Load the main dataset from database (SQLite or MSSQL)."""
    try:
        sql = load_sql_query(PREFERRED_QUERY, QUERIES_PATH)
        print(f"[polysubstance_alt] Using query: {PREFERRED_QUERY}")
    except KeyError:
        sql = load_sql_query(FALLBACK_QUERY, QUERIES_PATH)
        print(f"[polysubstance_alt] Using query: {FALLBACK_QUERY}")

    # Execute query using db_utils (automatically uses correct database)
    df = execute_query(sql)

    if df.empty:
        raise RuntimeError("Query returned 0 rows.")

    # Clean up categorical columns
    want_obj = ["county", "city", "hawaii_residency", "age_group", "sex", "substance"]
    for c in want_obj:
        if c in df.columns:
            df[c] = (
                df[c].astype(str).str.strip()
                .replace({"nan": np.nan, "None": np.nan})
                .fillna("Unknown")
            )

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    print(f"[polysubstance_alt] rows={len(df):,}  cols={list(df.columns)}")
    return df


df_raw = load_df()

# Filter data: 2018-2024, exclude unknown ages
if "year" in df_raw.columns:
    df_raw["year"] = pd.to_numeric(df_raw["year"], errors="coerce").astype("Int64")
    mask_year = df_raw["year"].between(2018, 2024, inclusive="both")
else:
    mask_year = True

def _is_unknown_age(val):
    s = (str(val) if val is not None else "").strip().lower()
    return s in {"", "unknown", "unk", "n/a", "na"}

mask_age = ~df_raw["age_group"].apply(_is_unknown_age) if "age_group" in df_raw.columns else True
df_raw = df_raw[mask_year & mask_age].copy()


# ---------- Helper functions ----------
def build_cooccurrence_matrix(df):
    """
    Build a co-occurrence matrix showing how often substances appear together.
    
    Returns a DataFrame where rows and columns are substances, and values are
    the count of records where both substances appear together.
    """
    # Create a pivot table: rows=record_id, columns=substance, values=1 if present
    substance_matrix = df.pivot_table(
        index='record_id',
        columns='substance',
        aggfunc='size',
        fill_value=0
    ).clip(upper=1)  # Convert to binary (0 or 1)
    
    # Calculate co-occurrence: matrix multiplication
    cooccurrence = substance_matrix.T.dot(substance_matrix)
    
    return cooccurrence


def build_correlation_matrix(df):
    """
    Build a correlation matrix showing the correlation between substance occurrences.
    """
    substance_matrix = df.pivot_table(
        index='record_id',
        columns='substance',
        aggfunc='size',
        fill_value=0
    ).clip(upper=1)
    
    return substance_matrix.corr()


def build_cooccurrence_data(df):
    """
    Build data for grouped bar chart showing co-occurrence percentages.
    
    For each substance, calculate what % of records also have other substances.
    """
    results = []
    
    for primary_substance in df['substance'].unique():
        # Get all records with this primary substance
        records = df[df['substance'] == primary_substance]['record_id'].unique()
        total = len(records)
        
        if total == 0:
            continue
        
        # For each other substance, count how many of these records also have it
        for other_substance in df['substance'].unique():
            if other_substance != primary_substance:
                count = df[
                    (df['record_id'].isin(records)) & 
                    (df['substance'] == other_substance)
                ]['record_id'].nunique()
                
                results.append({
                    'Primary': primary_substance,
                    'Also Found': other_substance,
                    'Percentage': (count / total) * 100,
                    'Count': count,
                    'Total': total
                })
    
    return pd.DataFrame(results)


# ---------- Layout ----------
def layout_for(is_mobile: bool = False):
    """Build the full page layout with co-occurrence visualizations."""
    
    return dbc.Container([
        # Store mobile state for callbacks
        dcc.Store(id="alt-is-mobile", data=is_mobile),
        
        html.H2(
            "Polysubstance Co-occurrence Analysis — Alternative Views",
            className="text-white bg-dark p-3 text-center mb-4"
        ),
        
        # Explanation section
        dbc.Alert([
            html.H5("About These Visualizations", className="alert-heading"),
            html.P([
                "These charts show relationships between different substances found in polysubstance cases. ",
                "Each visualization offers a different perspective on how substances co-occur."
            ]),
        ], color="info", className="mb-4"),
        
        # Visualization 1: Heatmap
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("1. Co-occurrence Heatmap", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.P([
                            "This heatmap shows how often substances appear together in the same record. ",
                            "Darker colors indicate stronger co-occurrence patterns.",
                            html.Br() if is_mobile else "",
                            html.Small("(Scroll horizontally to see full chart)", className="text-muted") if is_mobile else ""
                        ], className="text-muted mb-3"),
                        dcc.Loading(
                            html.Div(
                                dcc.Graph(
                                    id="alt-heatmap",
                                    config={"displayModeBar": True, "displaylogo": False},
                                    style={
                                        # Fixed height for both mobile and desktop
                                        "height": "600px",
                                        "minWidth": "1500px"
                                    }
                                ),
                                style={
                                    # handles horizontal scrolling on smaller screen sizes (mobile)
                                    "overflowX": "auto",
                                },
                                className="graph-inner" if is_mobile else ""
                            ),
                            className="heatmap-scroll" if is_mobile else ""
                        )
                    ])
                ])
            ], md=12, className="mb-4")
        ]),
        
        # Visualization 2: Grouped Bar Chart
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("2. Co-occurrence by Primary Substance", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.P([
                            "When a primary substance is present, this shows what percentage of those cases ",
                            "also contain each other substance. Use the filter below to focus on one substance.",
                            html.Br() if is_mobile else "",
                            html.Small("(Scroll horizontally to see all substances)", className="text-muted") if is_mobile else ""
                        ], className="text-muted mb-3"),
                        dcc.Loading(
                            html.Div(
                                html.Div(
                                    dcc.Graph(
                                        id="alt-bar-chart",
                                        config={"displayModeBar": True, "displaylogo": False},
                                        style={"height": "650px" if is_mobile else "500px"}
                                    ),
                                    className="graph-inner" if is_mobile else ""
                                ),
                                className="hscroll-graph" if is_mobile else ""
                            )
                        ),
                        html.Hr(className="my-3"),
                        html.Label("Filter by Primary Substance:", className="form-label fw-bold"),
                        dcc.Dropdown(
                            id="alt-primary-substance",
                            options=[{"label": "All substances (no filter)", "value": ""}] + 
                                    [{"label": s, "value": s} for s in sorted(df_raw['substance'].unique())],
                            value="",
                            clearable=False,
                            className="mb-2"
                        ),
                        html.Small("Select a specific substance to see what co-occurs with it, or choose 'All substances' to see the full overview.", 
                                   className="text-muted")
                    ])
                ])
            ], md=12, className="mb-4")
        ]),
        
        # Visualization 3: Network Graph
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("3. Substance Co-occurrence Network", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.P([
                            "This network shows substances as nodes connected by their co-occurrence frequency. ",
                            "Thicker lines indicate substances that appear together more often. ",
                            "Only connections with at least 50 co-occurrences are shown."
                        ], className="text-muted mb-3"),
                        dcc.Loading(
                            dcc.Graph(
                                id="alt-network",
                                config={"displayModeBar": True, "displaylogo": False},
                                style={"height": "600px"}
                            )
                        )
                    ])
                ])
            ], md=12, className="mb-4")
        ]),
        
        # Visualization 4: Sankey Diagram
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("4. Substance Flow Diagram (Sankey)", className="mb-0")
                    ]),
                    dbc.CardBody([
                        html.P([
                            "This flow diagram shows how substances connect to each other in polysubstance cases. ",
                            "The width of each flow represents the number of co-occurrences. ",
                            "Only the top 8 substances by frequency are shown for clarity."
                        ], className="text-muted mb-3"),
                        dcc.Loading(
                            dcc.Graph(
                                id="alt-sankey",
                                config={"displayModeBar": True, "displaylogo": False},
                                style={"height": "700px"}
                            )
                        )
                    ])
                ])
            ], md=12, className="mb-4")
        ]),
        
    ], fluid=True)


layout = layout_for(is_mobile=False)


# ---------- Callbacks ----------

@callback(
    Output("alt-heatmap", "figure"),
    Input("alt-primary-substance", "value"),  # Not used, but keeps callback structure
    Input("alt-is-mobile", "data"),
)
def update_heatmap(_, is_mobile):
    """Create a heatmap showing correlation between substances."""
    
    if df_raw.empty or 'substance' not in df_raw.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    # Build correlation matrix
    corr_matrix = build_correlation_matrix(df_raw)
    
    # Adjust parameters based on mobile state
    if is_mobile:
        text_size = 9
        height = 700  # Taller to accommodate all rows
        width = 800   # Wide enough to not compress
        margin_left = 120
        margin_right = 80  # Space for colorbar
        margin_top = 80
        margin_bottom = 120
        title_text = "Substance Correlations"
        title_size = 14
    else:
        text_size = 10
        height = 600
        width = None  # Auto width for desktop
        margin_left = 150
        margin_right = 50
        margin_top = 80
        margin_bottom = 150
        title_text = "Substance Co-occurrence Correlation Matrix"
        title_size = 16
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale='RdYlGn',
        zmid=0,
        text=corr_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": text_size},
        colorbar=dict(title="Correlation")
    ))
    
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=title_size)),
        xaxis=dict(side='bottom', tickangle=45, tickfont=dict(size=text_size)),
        yaxis=dict(autorange='reversed', tickfont=dict(size=text_size)),
        height=height,
        width=width,
        margin=dict(l=margin_left, r=margin_right, t=margin_top, b=margin_bottom),
        autosize=False if is_mobile else True
    )
    
    return fig


@callback(
    Output("alt-bar-chart", "figure"),
    Input("alt-primary-substance", "value"),
    Input("alt-is-mobile", "data"),
)
def update_bar_chart(primary_substance, is_mobile):
    """Create grouped bar chart showing co-occurrence percentages."""
    
    if df_raw.empty or 'substance' not in df_raw.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    # Build co-occurrence data
    co_data = build_cooccurrence_data(df_raw)
    
    if co_data.empty:
        return go.Figure().add_annotation(text="No co-occurrence data available", showarrow=False)
    
    # Mobile-specific adjustments
    if is_mobile:
        text_size = 8
        height = 650
        width = 900  # Fixed width for scrolling
        title_size = 13
        margin_left = 140
        margin_right = 40
        margin_top = 70
        margin_bottom = 100
    else:
        text_size = 10
        height = 500
        width = None  # Auto width
        title_size = 16
        margin_left = 150
        margin_right = 50  # Can reduce now that legend is on top
        margin_top = 120  # More room for horizontal legend
        margin_bottom = 120  # More room for x-axis labels
    
    # Filter by primary substance if selected (and not empty string)
    if primary_substance and primary_substance != "":
        co_data = co_data[co_data['Primary'] == primary_substance]
        if co_data.empty:
            return go.Figure().add_annotation(
                text=f"No co-occurrence data for {primary_substance}",
                showarrow=False
            )
        
        # Sort by percentage descending (highest to lowest) for both mobile and desktop
        co_data = co_data.sort_values('Percentage', ascending=False)
        
        # Create custom text with percentage and count
        co_data['label'] = co_data.apply(
            lambda row: f"{row['Percentage']:.1f}% (n={int(row['Count']):,})", 
            axis=1
        )
        
        # Create formatted hover text
        co_data['Count_formatted'] = co_data['Count'].apply(lambda x: f"{int(x):,}")
        co_data['Total_formatted'] = co_data['Total'].apply(lambda x: f"{int(x):,}")
        
        # Mobile: vertical bars (x=substance, y=percentage), Desktop: horizontal bars (x=percentage, y=substance)
        if is_mobile:
            fig = px.bar(
                co_data,
                x='Also Found',
                y='Percentage',
                orientation='v',
                title=f"When {primary_substance} is present, % with other substances",
                labels={'Percentage': 'Co-occurrence %', 'Also Found': 'Other Substance'},
                text='label',
                hover_data={
                    'Count': False, 
                    'Total': False, 
                    'label': False,
                    'Count_formatted': ':.0f',
                    'Total_formatted': ':.0f'
                },
                custom_data=['Count_formatted', 'Total_formatted']
            )
            
            fig.update_traces(
                textposition='outside',
                textangle=0,
                hovertemplate='<b>%{x}</b><br>' +
                             'Co-occurrence: %{y:.1f}%<br>' +
                             'Count: %{customdata[0]}<br>' +
                             'Total: %{customdata[1]}<extra></extra>',
                textfont=dict(size=text_size)
            )
        else:
            fig = px.bar(
                co_data,
                x='Percentage',
                y='Also Found',
                orientation='h',
                title=f"When {primary_substance} is present, % with other substances",
                labels={'Percentage': 'Co-occurrence %', 'Also Found': 'Other Substance'},
                text='label',
                hover_data={
                    'Count': False, 
                    'Total': False, 
                    'label': False,
                    'Count_formatted': ':.0f',
                    'Total_formatted': ':.0f'
                },
                custom_data=['Count_formatted', 'Total_formatted']
            )
            
            fig.update_traces(
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>' +
                             'Co-occurrence: %{x:.1f}%<br>' +
                             'Count: %{customdata[0]}<br>' +
                             'Total: %{customdata[1]}<extra></extra>',
                textfont=dict(size=text_size)
            )
        
    else:
        # Show all primary substances
        # Add custom text label with percentage and count
        co_data['label'] = co_data.apply(
            lambda row: f"{row['Percentage']:.1f}% (n={int(row['Count']):,})" if not is_mobile else f"{row['Percentage']:.0f}%", 
            axis=1
        )
        
        # Create formatted hover text
        co_data['Count_formatted'] = co_data['Count'].apply(lambda x: f"{int(x):,}")
        co_data['Total_formatted'] = co_data['Total'].apply(lambda x: f"{int(x):,}")
        
        fig = px.bar(
            co_data,
            x='Primary',
            y='Percentage',
            color='Also Found',
            barmode='group',
            title='Co-occurrence patterns: When [Primary] is present, % with other substances',
            labels={'Percentage': 'Co-occurrence %', 'Primary': 'Primary Substance'},
            text='label',
            hover_data={
                'Count': False, 
                'Total': False, 
                'label': False,
                'Count_formatted': ':.0f',
                'Total_formatted': ':.0f'
            },
            custom_data=['Count_formatted', 'Total_formatted', 'Also Found']
        )
        
        fig.update_traces(
            textposition='outside',
            textangle=0,
            hovertemplate='<b>%{customdata[2]}</b><br>' +
                         'Primary: %{x}<br>' +
                         'Co-occurrence: %{y:.1f}%<br>' +
                         'Count: %{customdata[0]}<br>' +
                         'Total: %{customdata[1]}<extra></extra>',
            textfont=dict(size=text_size)
        )
    
    # Apply mobile-responsive layout
    # X-axis angle: 45° for grouped view (substance names), 45° for mobile filtered (substance names), 0° for desktop filtered (percentages)
    x_angle = 45 if (not primary_substance or primary_substance == "") else (45 if is_mobile else 0)
    
    fig.update_layout(
        height=height,
        width=width,
        title=dict(font=dict(size=title_size)),
        xaxis=dict(
            tickangle=x_angle,
            tickfont=dict(size=text_size)
        ),
        yaxis=dict(tickfont=dict(size=text_size)),
        margin=dict(
            l=margin_left if primary_substance and primary_substance != "" else (margin_left - 10), 
            r=margin_right, 
            t=margin_top, 
            b=margin_bottom
        ),
        legend=dict(
            font=dict(size=text_size),
            orientation="h",  # Horizontal legend
            yanchor="bottom",
            y=1.02,  # Position above plot area
            xanchor="center",
            x=0.5  # Center horizontally
        ) if not primary_substance or primary_substance == "" else dict(font=dict(size=text_size)),
        autosize=False if is_mobile else True
    )
    
    return fig


@callback(
    Output("alt-network", "figure"),
    Input("alt-primary-substance", "value"),  # Not used, but keeps callback structure
)
def update_network(_):
    """Create a network graph showing substance co-occurrences."""
    
    if df_raw.empty or 'substance' not in df_raw.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    # Build co-occurrence matrix
    cooccurrence = build_cooccurrence_matrix(df_raw)
    
    # Create edge list (only show edges above a threshold)
    threshold = 50
    edges = []
    edge_weights = []
    
    substances = list(cooccurrence.index)
    
    for i, sub1 in enumerate(substances):
        for j, sub2 in enumerate(substances):
            if i < j:  # Only upper triangle to avoid duplicates
                weight = cooccurrence.loc[sub1, sub2]
                if weight > threshold:
                    edges.append((sub1, sub2))
                    edge_weights.append(weight)
    
    if not edges:
        return go.Figure().add_annotation(
            text=f"No co-occurrences above threshold ({threshold})",
            showarrow=False
        )
    
    # Simple circular layout
    n = len(substances)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pos = {sub: (np.cos(angle), np.sin(angle)) for sub, angle in zip(substances, angles)}
    
    # Create edge traces with labels
    edge_traces = []
    edge_label_traces = []
    
    for (sub1, sub2), weight in zip(edges, edge_weights):
        x0, y0 = pos[sub1]
        x1, y1 = pos[sub2]
        
        # Normalize weight for line width (1-10 range)
        max_weight = max(edge_weights)
        line_width = 1 + (weight / max_weight) * 9
        
        # Add edge line
        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=line_width, color='rgba(125,125,125,0.3)'),
            hoverinfo='skip',
            showlegend=False
        ))
        
        # Calculate position offset perpendicular to the line
        # This helps spread out labels to reduce overlap
        dx = x1 - x0
        dy = y1 - y0
        length = np.sqrt(dx**2 + dy**2)
        
        # Perpendicular offset (very small displacement to stay close to line)
        offset = 0.02
        perp_x = -dy / length * offset
        perp_y = dx / length * offset
        
        # Position label slightly offset from midpoint
        mid_x = (x0 + x1) / 2 + perp_x
        mid_y = (y0 + y1) / 2 + perp_y
        
        edge_label_traces.append(go.Scatter(
            x=[mid_x],
            y=[mid_y],
            mode='markers+text',
            text=[f"{int(weight):,}"],
            textfont=dict(size=10, color='#ffffff', family='Arial'),
            textposition='middle center',
            hovertext=f"{sub1} + {sub2}<br>Co-occurrences: {int(weight):,}",
            hoverinfo='text',
            showlegend=False,
            # Add background box to make text stand out
            marker=dict(
                size=20,
                color='#d32f2f',
                symbol='square',
                line=dict(width=0)
            )
        ))
    
    # Create node trace
    node_x = [pos[sub][0] for sub in substances]
    node_y = [pos[sub][1] for sub in substances]
    node_size = [cooccurrence.loc[sub, sub] / 50 for sub in substances]  # Size by frequency
    
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=substances,
        textposition='top center',
        marker=dict(
            size=node_size,
            color='lightblue',
            line=dict(width=2, color='darkblue'),
            sizemode='area',
            sizeref=2.*max(node_size)/(40.**2),
            sizemin=4
        ),
        hovertext=[f"{sub}<br>Frequency: {cooccurrence.loc[sub, sub]:,.0f}" for sub in substances],
        hoverinfo='text',
        showlegend=False
    )
    
    # Combine traces: edges, edge labels, then nodes (so nodes appear on top)
    fig = go.Figure(data=edge_traces + edge_label_traces + [node_trace])
    
    fig.update_layout(
        title=f"Substance Co-occurrence Network (threshold: {threshold}+ cases)",
        showlegend=False,
        hovermode='closest',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=600,
        plot_bgcolor='white'
    )
    
    return fig


@callback(
    Output("alt-sankey", "figure"),
    Input("alt-primary-substance", "value"),  # Not used, but keeps callback structure
)
def update_sankey(_):
    """Create a Sankey diagram showing substance flow patterns."""
    
    if df_raw.empty or 'substance' not in df_raw.columns:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    # Get top substances to keep diagram readable
    top_substances = (
        df_raw.groupby('substance')['record_id']
        .nunique()
        .nlargest(8)
        .index.tolist()
    )
    
    # Filter to top substances
    df_filtered = df_raw[df_raw['substance'].isin(top_substances)].copy()
    
    # Build co-occurrence edges
    edges = []
    for substance in top_substances:
        records = df_filtered[df_filtered['substance'] == substance]['record_id'].unique()
        
        for other_sub in top_substances:
            if other_sub != substance:
                count = df_filtered[
                    (df_filtered['record_id'].isin(records)) & 
                    (df_filtered['substance'] == other_sub)
                ]['record_id'].nunique()
                
                if count > 20:  # Only show significant connections
                    edges.append({
                        'source': substance,
                        'target': other_sub,
                        'value': count
                    })
    
    if not edges:
        return go.Figure().add_annotation(text="Insufficient data for Sankey diagram", showarrow=False)
    
    edge_df = pd.DataFrame(edges)
    
    # Create node list and mappings
    all_nodes = list(set(edge_df['source'].tolist() + edge_df['target'].tolist()))
    node_dict = {node: idx for idx, node in enumerate(all_nodes)}
    
    # Map to indices
    source_indices = [node_dict[s] for s in edge_df['source']]
    target_indices = [node_dict[t] for t in edge_df['target']]
    
    # Create Sankey
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            color="lightblue"
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=edge_df['value'].tolist(),
            label=[f"{edge_df.iloc[i]['value']:,.0f}" for i in range(len(edge_df))]
        )
    )])
    
    fig.update_layout(
        title="Substance Co-occurrence Flow (Top 8 Substances)",
        font=dict(size=12),
        height=700
    )
    
    return fig
