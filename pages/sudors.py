from dash import register_page

import sudors_dashboard as sudo

register_page(
    __name__,
    path="/sudors",
    name="SUDORS",
    title="SUDORS",
)

layout = sudo.layout
