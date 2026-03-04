from dash import register_page

import polysubstance_dashboard as poly

register_page(
    __name__,
    path="/polysubstance",
    name="Related to polysubstance use",
    title="Related to polysubstance use",
)

layout = poly.layout
