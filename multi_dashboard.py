# multi_dashboard.py
from dash import Dash, html, dcc, page_container, callback, Input, Output
import dash_bootstrap_components as dbc

TAB_PATHS = {
    "/": "Substance Use Dashboards",
    "/discharges": "Discharges related to substance use",
    "/dose": "Drug Overdose Surveillance and Epidemiology (DOSE)",
    "/polysubstance": "Related to polysubstance use",
    "/polysubstance-alt": "Polysubstance Alternates",
}

DEFAULT_PATH = "/discharges"

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
)
server = app.server
app.title = "Substance Use Dashboards"

app.layout = dbc.Container(
    [
        html.A(
            "Skip to navigation",
            href="#top-nav",
            className="visually-hidden-focusable",
            tabIndex=0,
        ),

        dcc.Location(id="url", refresh=False),

        html.Div(
            html.Div(
                [
                    html.A(
                        TAB_PATHS["/discharges"],
                        href="/discharges",
                        className="tab",
                        id="tab-discharges"
                    ),
                    html.A(
                        TAB_PATHS["/polysubstance"],
                        href="/polysubstance",
                        className="tab",
                        id="tab-polysubstance"
                    ),
                    html.A(
                        TAB_PATHS["/polysubstance-alt"],
                        href="/polysubstance-alt",
                        className="tab",
                        id="tab-polysubstance-alt"
                    ),
                ],
                className="tabs",
                id="top-nav"
            ),
            id="top-nav-wrapper",
            className="mb-2",
        ),

        html.H2(id="page-title", className="text-center mb-2"),

        html.Div(page_container, style={"marginTop": "12px"}),
    ],
    fluid=True,
)


@callback(
    Output("tab-discharges", "className"),
    Output("tab-polysubstance", "className"),
    Output("tab-polysubstance-alt", "className"),
    Output("top-nav-wrapper", "style"),
    Output("page-title", "children"),
    Input("url", "pathname"),
)
def update_active_tab(pathname):
    """Update which tab appears active and set the page title."""
    if not pathname:
        pathname = "/"
    
    # Determine which tab should be active
    discharges_class = "tab tab--selected" if pathname == "/discharges" else "tab"
    polysubstance_class = "tab tab--selected" if pathname == "/polysubstance" else "tab"
    polysubstance_alt_class = "tab tab--selected" if pathname == "/polysubstance-alt" else "tab"

    tab_visible_paths = {"/discharges", "/polysubstance", "/polysubstance-alt"}
    nav_style = {} if pathname in tab_visible_paths else {"display": "none"}
    
    # Get the page title
    title = TAB_PATHS.get(pathname, "Substance Use Dashboards")

    return discharges_class, polysubstance_class, polysubstance_alt_class, nav_style, title


if __name__ == "__main__":
    app.run(debug=True)
