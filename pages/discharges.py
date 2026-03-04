from dash import register_page

import app_alt as alt

register_page(
    __name__,
    path="/discharges",
    name="Discharges related to substance use",
    title="Discharges related to substance use",
)

layout = alt.layout_for(is_mobile=False, show_discharges=True, show_dose=False)
