from dash import register_page, html
import dash_bootstrap_components as dbc

register_page(
    __name__,
    path="/",
    name="Home",
    title="Substance Use Dashboards",
)

layout = dbc.Container(
    [
        html.H4("Dashboard Pages", className="mb-3"),
        html.P("Choose a page:"),
        dbc.ListGroup(
            [
                dbc.ListGroupItem(html.A("Discharges related to substance use", href="/discharges")),
                dbc.ListGroupItem(html.A("SUDORS", href="/sudors")),
                dbc.ListGroupItem(html.A("Drug Overdose Surveillance and Epidemiology (DOSE)", href="/dose")),
                dbc.ListGroupItem(html.A("Related to polysubstance use", href="/polysubstance")),
                dbc.ListGroupItem(html.A("Polysubstance Alternates", href="/polysubstance-alt")),
            ]
        ),
    ],
    fluid=True,
    className="p-2",
)
