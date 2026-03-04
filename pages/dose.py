from dash import register_page

import app_alt as alt

register_page(
    __name__,
    path="/dose",
    name="Drug Overdose Surveillance and Epidemiology (DOSE)",
    title="Drug Overdose Surveillance and Epidemiology (DOSE)",
)

layout = alt.layout_for(is_mobile=False, show_discharges=False, show_dose=True)
