import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Create data for phases
phases_data = [
    {"Phase": "Research", "Start": 1, "End": 6},
    {"Phase": "Prototyp", "Start": 7, "End": 14}, 
    {"Phase": "Testy", "Start": 15, "End": 24},
    {"Phase": "Production", "Start": 25, "End": 36}
]

# Brand colors in order
colors = ["#1FB8CD", "#DB4545", "#2E8B57", "#5D878F"]

# Create the figure
fig = go.Figure()

# Add each phase as a horizontal bar
for i, phase in enumerate(phases_data):
    duration = phase["End"] - phase["Start"] + 1
    fig.add_trace(go.Bar(
        name=phase["Phase"],
        y=[phase["Phase"]], 
        x=[duration],
        base=[phase["Start"]],
        orientation='h',
        marker_color=colors[i],
        cliponaxis=False
    ))

# Add milestone lines at specified weeks
milestone_weeks = [6, 14, 24, 30, 36]
milestone_names = ["SMC Lib Done", "MVP Ready", "Paper Trade", "Infra Live", "System Live"]

for week in milestone_weeks:
    fig.add_vline(
        x=week, 
        line_width=2, 
        line_dash="dash", 
        line_color="gray",
        opacity=0.7
    )

# Update layout
fig.update_layout(
    title="Harmonogram Projektu SMC Trading Agent",
    xaxis_title="Tygodnie",
    yaxis_title="Fazy",
    barmode='overlay',
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5)
)

# Update axes to show weeks 1-36 properly
fig.update_xaxes(range=[1, 37], dtick=2)
fig.update_yaxes()

# Save the chart
fig.write_image("gantt_chart.png")