import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Create DataFrame from the provided data
data = [
    {"nazwa": "joshyattridge/smc", "framework": "Python", "przydatnosc": 5},
    {"nazwa": "stefan-jansen/ml-trading", "framework": "Python", "przydatnosc": 5},
    {"nazwa": "vlex05/SMC-Algo", "framework": "Python", "przydatnosc": 4},
    {"nazwa": "smtlab/smc", "framework": "Python", "przydatnosc": 4},
    {"nazwa": "Open-Trader/opentrader", "framework": "JavaScript", "przydatnosc": 4},
    {"nazwa": "Gifted87/TradingBot", "framework": "Python", "przydatnosc": 4},
    {"nazwa": "tsunafire/PineScript", "framework": "PineScript", "przydatnosc": 3},
    {"nazwa": "trentstauff/FXBot", "framework": "Mixed", "przydatnosc": 3},
    {"nazwa": "enarjord/passivbot", "framework": "Mixed", "przydatnosc": 3},
    {"nazwa": "mariaoxulz/smc-comparison", "framework": "Web", "przydatnosc": 2}
]

df = pd.DataFrame(data)

# Shorten repository names to fit 15 character limit
def shorten_name(name):
    if len(name) <= 15:
        return name
    if '/' in name:
        parts = name.split('/')
        if len(parts[1]) <= 15:
            return parts[1]  # Use second part (repo name) instead of username
        else:
            return parts[1][:15]
    return name[:15]

df['nazwa_short'] = df['nazwa'].apply(shorten_name)

# Define colors for frameworks following the brand colors
color_map = {
    'Python': '#1FB8CD',    # Strong cyan 
    'JavaScript': '#2E8B57', # Sea green
    'PineScript': '#DB4545', # Bright red
    'Mixed': '#5D878F',     # Cyan
    'Web': '#D2BA4C'        # Moderate yellow
}

# Create bar chart
fig = px.bar(df, 
             x='nazwa_short', 
             y='przydatnosc',
             color='framework',
             color_discrete_map=color_map,
             title="GitHub Repos dla SMC Trading")

# Update layout with shortened axis titles
fig.update_layout(
    xaxis_title="Repo",
    yaxis_title="Ocena (1-5)",
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5)
)

# Update y-axis range
fig.update_yaxes(range=[0, 5.5])

# Save the chart
fig.write_image("github_repos_usefulness.png")