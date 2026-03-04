from dash import register_page
import sys
sys.path.insert(0, "/Users/jgeis/Work/DOH/plotly")

import polysubstance_alt as poly_alt

register_page(
    __name__,
    path="/polysubstance-alt",
    name="Polysubstance Alternates",
    title="Polysubstance Alternates",
)

layout = poly_alt.layout
