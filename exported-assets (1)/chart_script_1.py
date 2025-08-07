import plotly.express as px
import pandas as pd

# Create the data with correct column naming
data = [
    {"kategoria": "Mocne strony", "liczba_wspomnieć": 15},
    {"kategoria": "Słabe strony", "liczba_wspomnieć": 12},
    {"kategoria": "Wyzwania tech", "liczba_wspomnieć": 8},
    {"kategoria": "Problemy reg", "liczba_wspomnieć": 5}
]

df = pd.DataFrame(data)

# Define brand colors
colors = ['#1FB8CD', '#DB4545', '#2E8B57', '#5D878F']

# Create bar chart
fig = px.bar(df, 
             x='kategoria', 
             y='liczba_wspomnieć',
             title='Analiza SMC według źródeł',
             color='kategoria',
             color_discrete_sequence=colors)

# Update layout following instructions
fig.update_layout(
    xaxis_title='Kategoria',
    yaxis_title='Liczba wsp.',
    showlegend=False
)

# Save the chart
fig.write_image('smc_analysis_chart.png')