import dash
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import folium
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter
from flask_caching import Cache
from pandas.api.types import CategoricalDtype
from dash import ctx  # Dash >= 2.7


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
# Set up cache configuration
cache = Cache(app.server, config={
    'CACHE_TYPE': 'SimpleCache',  # For production, switch to Redis or other types
    'CACHE_DEFAULT_TIMEOUT': 300  # Cache timeout (in seconds)
})

import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False is deprecated.*")

# ---- Paths & data bootstrap for sample repo ----
from pathlib import Path
BASE = Path(__file__).resolve().parent # → preprocessing_mini_sample/app
ROOT = BASE.parent # → preprocessing_mini_sample
DATA_DIR = ROOT / "sample_data"
CSV_PATH = DATA_DIR / "country-year_mean.csv"
# Canonical category order your app expects
CATEGORY_ORDER = [
    "Deflation",
    "Very Low Inflation",
    "Target Inflation",
    "Low Inflation",
    "Moderate Inflation",
    "High Inflation",
    "Very High Inflation",
    "Hyperinflation",
]
# Map common variants → canonical labels (extend as needed)
CATEGORY_ALIASES = {
    "very low": "Very Low Inflation",
    "very-low": "Very Low Inflation",
    "target": "Target Inflation",
    "low": "Low Inflation",
    "moderate": "Moderate Inflation",
    "high": "High Inflation",
    "very high": "Very High Inflation",
    "very-high": "Very High Inflation",
    "hyper": "Hyperinflation",
    "hyper inflation": "Hyperinflation",
    "hyper-inflation": "Hyperinflation",
    "deflation": "Deflation",
}

def normalize_category(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    # try exact matches first
    s2 = s.replace({k: v for k, v in CATEGORY_ALIASES.items() if k in CATEGORY_ORDER})
    # fallback: fuzzy-ish lower() contains checks
    def _norm(x):
        lx = x.lower()
        for k, v in CATEGORY_ALIASES.items():
            if k in lx:
                return v
        # if already canonical, keep it; else leave as-is
        return x
    s2 = s2.apply(_norm)
    # cast to categorical with full order (helps ensure consistent plotting)
    cat_type = CategoricalDtype(categories=CATEGORY_ORDER, ordered=True)
    return s2.astype(cat_type)


# Load the data into the country_year_mean DataFrame
country_year_mean = pd.read_csv(CSV_PATH)
if "Category" in country_year_mean.columns:
    country_year_mean["Category"] = normalize_category(country_year_mean["Category"])
# Ensure we have Inflation_Category, normalized
if "Inflation_Category" not in country_year_mean.columns and "Category" in country_year_mean.columns:
    country_year_mean["Inflation_Category"] = country_year_mean["Category"]

if "Inflation_Category" in country_year_mean.columns:
    country_year_mean["Inflation_Category"] = normalize_category(country_year_mean["Inflation_Category"])


# Discover available years from GeoJSONs
_geo_paths = sorted(DATA_DIR.glob("Inflation_*.geojson"))
YEARS = sorted({int(p.stem.split("_")[1]) for p in _geo_paths}) or [2001, 2002]
DEFAULT_YEAR = max(YEARS)
# ---- end bootstrap ----

# Helper function to create the category bar plot
def create_category_bar_plot():
    custom_order = CATEGORY_ORDER

    # Counts by category (ensure full set + integers)
    category_counts = (
        country_year_mean['Inflation_Category']
        .value_counts(dropna=False)
        .reindex(custom_order)
        .fillna(0)
        .astype(int)
    )

    # Min/Max per category (explicit observed=False to keep current behavior)
    inflation_ranges = (
        country_year_mean
        .groupby('Inflation_Category', observed=False)['Value']
        .agg(['min', 'max'])
        .reindex(custom_order)
    )

    # Format labels safely
    def _fmt(v):
        try:
            return f"{float(v):.1f}%"
        except Exception:
            return "N/A"

    category_labels = [
        f"{cat}\n({_fmt(inflation_ranges.loc[cat, 'min'])} - {_fmt(inflation_ranges.loc[cat, 'max'])})"
        for cat in custom_order
    ]

    fig = px.bar(
        x=category_labels,
        y=category_counts.values,
        labels={'x': '', 'y': 'Number of Instances'},
        title='Total Frequency of Inflation Categories (2001–2024)',
        text=category_counts.values
    )
    fig.update_layout(
        yaxis_title='Number of Instances',
        title={'x': 0.5, 'y': 0.95},
        margin=dict(l=50, r=50, t=40, b=80),
        yaxis_title_standoff=10,
    )
    fig.update_xaxes(tickangle=45, automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


'''    
def create_category_bar_plot():
    # Define the custom order for the inflation categories
    custom_order = [
        'Deflation',
        'Very Low Inflation', 
        'Target Inflation', 
        'Low Inflation', 
        'Moderate Inflation', 
        'High Inflation', 
        'Very High Inflation', 
        'Hyperinflation'
    ]

    # Calculate category counts and ensure they are in the correct order
    category_counts = country_year_mean['Inflation_Category'].value_counts().reindex(custom_order)

    # Calculate inflation range for each category
    inflation_ranges = country_year_mean.groupby('Inflation_Category')['Value'].agg(['min', 'max']).reindex(custom_order)

    # Fill missing values (NaN) with 'N/A' or a default value
    inflation_ranges = inflation_ranges.fillna({'min': 'N/A', 'max': 'N/A'})

    # Create new labels with inflation range, handle cases where 'N/A' is present
    category_labels = [
        f"{category}\n({inflation_ranges.loc[category, 'min']:.1f}% - {inflation_ranges.loc[category, 'max']:.1f}%)"
        if inflation_ranges.loc[category, 'min'] != 'N/A'
        else f"{category}\n(N/A)"
        for category in custom_order
    ]

    # Create a bar plot using Plotly
    fig = px.bar(
        x=category_labels,
        y=category_counts.values,
        labels={'x': '', 'y': 'Number of Instances'},
        title='Total Frequency of Inflation Categories (2001-2024)',
        text=category_counts.values  # Show frequency values on bars
    )
    
    fig.update_layout(
        #xaxis_title='Inflation Category (with Range)',
        yaxis_title='Number of Instances',
        title={'x': 0.5, 'y': 0.95},  # Center the title
        margin=dict(l=50, r=50, t=40, b=80),
        yaxis_title_standoff=10,  # Add space between y-axis label and axis
    )
    fig.update_xaxes(tickangle=45, automargin=True)  # Rotate the x-axis labels for better readability
    fig.update_yaxes(automargin=True)  # Ensure enough space for the y-axis label
    return fig
'''

# helper function for continent plot
# helper table for continent plot (global, not year-dependent)
continent_inflation_periods_counts = (
    country_year_mean
        .groupby(['Region', 'Inflation_Category'], observed=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=CATEGORY_ORDER, fill_value=0)
)

inflation_categories = CATEGORY_ORDER  # reuse same order
colors = ['#1f77b4', '#53b5a3', '#2ca02c', '#98df8a', '#ffcc00', '#ff7f0e', '#d62728', '#7F00FF']
def update_stacked_barplot():
    df = continent_inflation_periods_counts.reset_index().copy()
    print(continent_inflation_periods_counts.head()) #for debug

    # Only include columns that exist; coerce to numeric just in case
    y_cols = [c for c in inflation_categories if c in df.columns]
    for c in y_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    if not y_cols or df[y_cols].to_numpy().sum() == 0:
        return px.bar(title="No continent counts to display.")

    # Optional consistent Region order if your data matches these names
    region_order = ["Africa", "Americas", "Asia", "Europe", "Oceania", "Unknown"]
    if set(df["Region"].unique()).issubset(set(region_order)):
        df["Region"] = pd.Categorical(df["Region"], region_order, ordered=True)
        df = df.sort_values("Region")

    fig = px.bar(
        df,
        x='Region',
        y=y_cols,
        title='Total Distribution of Inflation Types',
        labels={'value': 'Number of Countries', 'Region': 'Continent'},
        color_discrete_sequence=colors[:len(y_cols)]
    )
    fig.update_layout(
        barmode='stack',
        legend_title_text='Inflation Type',
        xaxis_title='Continent',
        yaxis_title='Number of Countries'
    )
    return fig
'''
continent_inflation_periods_counts = country_year_mean.groupby(['Region', 'Inflation_Category']).size().unstack(fill_value=0)
#continent_inflation_periods_counts = continent_inflation_periods_counts[['Deflation', 'Very Low Inflation', 'Target Inflation', 'Low Inflation', 'Moderate Inflation', 'High Inflation', 'Very High Inflation', 'Hyperinflation']]
continent_inflation_periods_counts = continent_inflation_periods_counts.reindex(
    columns=CATEGORY_ORDER, fill_value=0
)
inflation_categories = ['Deflation', 'Very Low Inflation','Target Inflation', 'Low Inflation', 'Moderate Inflation', 'High Inflation', 'Very High Inflation', 'Hyperinflation']
colors = ['#1f77b4', '#53b5a3', '#2ca02c', '#98df8a', '#ffcc00', '#ff7f0e', '#d62728', '#7F00FF']   
    
def update_stacked_barplot():  # Add parameters as needed
    # Create a DataFrame to plot using Plotly
    df = continent_inflation_periods_counts.reset_index()

    # Use plotly.express for stacked bar plot
    fig = px.bar(df, 
                 x='Region', 
                 y=inflation_categories, 
                 title='Total Distribution of Inflation Types',
                 labels={'value': 'Number of Countries', 'Region': 'Continent'},
                 color_discrete_sequence=colors)

    fig.update_layout(barmode='stack',  # Stacked bar chart
                      legend_title_text='Inflation Type',
                      xaxis_title='Continent',
                      yaxis_title='Number of Countries')

    return fig
'''    
# Helper function to generate word cloud from frequencies
def generate_word_cloud(frequencies):
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(frequencies)
    image = io.BytesIO()
    wordcloud.to_image().save(image, format='PNG')
    image.seek(0)
    return base64.b64encode(image.read()).decode('utf-8')
    
    
# Color mapping for inflation categories
category_colors = {
    'Deflation': '#1f77b4',  # Blue
    'Very Low Inflation': '#53b5a3', # light bluegreen
    'Target Inflation': '#2ca02c',  # Green
    'Low Inflation': '#98df8a',            # Light Green
    'Moderate Inflation': '#ffcc00',       # Yellow
    'High Inflation': '#ff7f0e',           # Orange
    'Very High Inflation': '#d62728',      # Red
    'Hyperinflation': '#7F00FF'            # Violet
}

# Corresponding inflation value ranges for each category
inflation_ranges = {
    'Deflation': 'Below 0%',
    'Very Low Inflation': '0% - 2%',
    'Target Inflation': '2% - 3%',
    'Low Inflation': '3% - 4%',
    'Moderate Inflation': '4% - 10%',
    'High Inflation': '10% - 50%',
    'Very High Inflation': '50% - 100%',
    'Hyperinflation': 'Above 100%'
}

# Function to generate a separate HTML-based legend next to the map with inflation ranges
def create_custom_legend():
    legend_items = [
        html.Div([
            html.I(style={
                'background': color, 
                'width': '10px',  # Narrower color block
                'height': '10px', 
                'display': 'inline-block', 
                'margin-right': '5px'  # Less margin for tighter spacing
            }),
            html.Span(f"{category} ({inflation_ranges[category]})", style={'font-size': '10px'})  # Smaller text
        ], style={
            'line-height': '15px',  # Adjust line spacing for tighter grouping
            'margin-bottom': '3px',  # Reduce space between legend items
            'word-wrap': 'break-word',  # Enable text wrapping
            'max-width': '150px'  # Limit the maximum width to force text to wrap
        })
        for category, color in category_colors.items()
    ]
    
    return html.Div([
        html.Strong("Inflation Categories:", style={'font-size': '12px', 'margin-bottom': '5px'}),
        html.Div(legend_items, style={'max-width': '150px'})  # Ensure the legend does not exceed a narrow width
    ], style={
        'padding': '8px', 
        'border': '1px #ccc', 
        'box-shadow': '2px 2px 5px rgba(0,0,0,0.3)', 
        'width': '160px',  # Narrower width for the entire legend container
        'font-size': '10px',  # Smaller font size for the legend
        'background-color': 'white',
        'word-wrap': 'break-word'
    })




# Create app layout
app.layout = html.Div([
	 html.Div([
	 html.Div([
        html.H4("Food Price Inflation Data Dashboard", style={'text-align': 'center', 'padding': '5px 0', 'color': '#274c77'})
    ]),
    html.P("Explore global food price inflation trends and analyze country-level inflation across different years and categories.", style={'text-align': 'center', 'padding': '0px 0', 'background-color': '#e7ecef', 'color': '#274c77'}),
    # info accordion
    html.Div(style={'width': '100%', 'padding-right': '10px', 'margin-left': '5px'}, children=[
    dbc.Accordion(
				[
				dbc.AccordionItem(
				[
					html.Div(style={'width': '100%', 'padding-right': '60px', 'margin-left': '10px', 'text-align': 'left'}, children=[
					dbc.Accordion(
					[
						dbc.AccordionItem(
							[
								html.P("This dashboard was created as a portfolio project to demonstrate skills in data visualization and analysis using global food price inflation data. It allows users to explore food price inflation trends by country and inflation category over the years 2001 to 2024."),
                    
								html.P("The primary focus of this dashboard is to provide insights into how food price inflation rates vary across countries, continents and years, and which inflation categories were most common. The use of interactive visualizations like scatter plots, word clouds, and bar plots allows users to dive deep into the data to find specific trends and patterns."),
                    
								html.P("Key features of the dashboard include:"),
								html.Ul([
									html.Li("A map for visualizing food price inflation rates by year and inflation category."),
									html.Li("Interactive country-wise inflation trend plots for detailed exploration."),
									html.Li("A word cloud for identifying countries that frequently experience certain types of inflation."),
									html.Li("Insights on the frequency and range of inflation categories, with the ability to explore specific inflation types."),
								]),

								html.P("This project showcases the ability to combine different data sources, process data efficiently, and build an engaging, user-friendly dashboard to explore complex datasets."),
                    
								html.Hr(),
                    
								html.H5("Technology Used:"),
								html.Ul([
									html.Li("Dash & Plotly: For building the interactive web-based dashboard and data visualizations."),
									html.Li("Pandas: For data manipulation, cleaning, and aggregation."),
									html.Li("Folium: For interactive map visualizations."),
									html.Li("WordCloud: For generating word cloud visualizations based on data frequencies."),
									html.Li("Python: General scripting and data processing."),
								]),
							],
							title="About this Dashboard"
						),
						dbc.AccordionItem(
							[
								html.P([
									"The inflation data used in this dashboard is based on food price inflation statistics for countries worldwide, covering periods available as of August 2024. This data was downloaded in CSV format from the ",
									html.A("FAO (Food and Agriculture Organization) FAOSTAT website", href="https://www.fao.org/faostat/en/#data/CP", target="_blank"),
									"."
								]),
								html.P([
									"To visualize the inflation data on the map, GeoJSON files were created using country boundaries obtained from the ",
									html.A("GeoJSON Maps website", href="https://geojson-maps.kyd.au/", target="_blank"),
									". The map data was downloaded with the 'All Countries' and 'Medium Resolution' options selected. The GeoJSON files were later processed to include inflation data, enabling interactive mapping and analysis."
								]),
							],
							title="Where Data Was Obtained"
						),
						dbc.AccordionItem(
							[
								html.P("Data Processing: After downloading the monthly food price inflation data for the years 2001–2024 from the FAOSTAT website, the data underwent several cleaning and preparation steps. Missing values were handled by either filling them with relevant estimates or removing incomplete records where necessary. The annual mean inflation was calculated for each country; then, countries were categorized based on their inflation rates into various types, such as Deflation, Low Inflation, Moderate Inflation, and Hyperinflation."),
								html.P("Pandas libraries were used for data cleaning and analysis, while Plotly and Folium were utilized for dynamic visualization and interactive mapping."),
							],
							title="How Data Was Processed"
						),
						dbc.AccordionItem(
							[
								html.P("Dashboard Layout: The dashboard offers a variety of interactive visualizations to explore global inflation data:"),
								html.Ul([
									html.Li([
										html.Strong("Map of Yearly Inflation:"),
										" Users can visualize inflation differences across countries by selecting a specific year from the dropdown. The map automatically updates to show inflation rates relative to that year."
									]),
									html.Li([
										html.Strong("Country-wise Inflation Trends:"),
										" Users can select a country from the dropdown to explore its inflation trend over time in an interactive line plot."
									]),
									html.Li([
										html.Strong("Inflation Categories:"),
										" By selecting an inflation category, users can visualize which countries experienced that type of inflation. The map updates automatically."
									]),
									html.Li([
										html.Strong("Word Cloud of Countries:"),
										" The word cloud provides a quick sense of which countries have most frequently experienced a selected type of inflation."
									]),
									html.Li([
										html.Strong("Interactive Bar Plot of Continents:"),
										" This plot shows the the frequency of inflation types for all continents over the years."
									]),
								]),
							],
							title="Dashboard Layout"
						),
                    
					],
					start_collapsed=True
				),
		]),
	],
	title=html.Div("Expand for information about the dashboard", style={'width': '100%', 'display': 'flex', 'justify-content': 'center', 'text-align': 'center'}),
	style={'background-color': '#e7ecef', 'text-align': 'center'},
	),#top accordion
	],
	start_collapsed = True,
	className="collapsed-accordion-header"
	),
	]),
	], style={'background-color': '#e7ecef', 'margin-left': '10PX'}),
	# Store to keep track of the currently active plot
    dcc.Store(id='active-plot', data='map'),  # Default to 'map'

    # Left section for information in an accordion
    html.Div([
        #html.H2("Info"),
        dbc.Accordion([
			dbc.Accordion(
					[
						dbc.AccordionItem(
							[
								html.Img(id='wordcloud-graph', style={'height': '50%', 'width': '100%'}),
								html.Div(id='inflation-range', style={'padding': '10px'}),
							],
							title="Inflation representation",
							item_id="accordion-item-wordcloud",
						),
					], 
					start_collapsed=False,
					className="collapsed-accordion-header2"
				),
			dbc.Accordion(
					[
						dbc.AccordionItem(
							[
								dcc.Graph(id='frequency-bar-graph', figure=create_category_bar_plot(), style={'height': '50%', 'width': '100%'}),
							],
							title="Expand to see how frequently each inflation category occurred— Moderate Inflation occured most frequently.",
							item_id="accordion-item-barplot",
						),
					], 
					start_collapsed=True,
					className="collapsed-accordion-header3"
					),
            dbc.AccordionItem(
                html.Div(id='info-text', children="Information about the selected plot will appear here."),
                title="Global Inflation insights (2001 - 20024)",
                className="collapsed-accordion-header2"
            ),
            dbc.AccordionItem(
                html.Div(id='insight-text', children="Insight about the selected plot will appear here."),
                title="Inflation Category insights",
                className="collapsed-accordion-header2"
            ),
			
        ], start_collapsed=True,id='info-accordion')
    ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),

    # Right section for plots
    html.Div([
    # Buttons to toggle between plots
    html.Div([
        html.Button('Map', id='btn-map', n_clicks=0, className='inactive'),
        html.Button('Continents - Bar Plot', id='btn-bar', n_clicks=0, className='inactive'),
    ], style={'display': 'flex', 'justify-content': 'space-around', 'padding': '10px'}),

    # Placeholder for the plots
    html.Div(style={'display': 'flex', 'justify-content': 'space-between', 'margin-left': '10px'}, children=[
        # Plot area
        html.Div(id='plot-area', children="Map will appear here",  
                 style={'height': '300px', 'padding': '0px', 'width': '90%'}),
        
    # Legend placed outside the plot area on the right
    html.Div(create_custom_legend(), style={'width': '10%', 'margin-left': '10px', 'margin-right': '30px', 'margin-top': '10px'})  # Legend container
    ]),

    # Container for side-by-side dropdowns
    html.Div(style={'display': 'flex', 'justify-content': 'space-between', 'align-items': 'center', 'margin-top': '10px'}, children=[
        # Year Dropdown
        html.Div([
            html.H5("Years:", style={'text-align': 'left', 'font-size': '12px','margin-top': '10px', 'margin-left':'10px'}),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(y), 'value': y} for y in YEARS],
                placeholder="Select the year", 
                value=DEFAULT_YEAR,  # Automatically select 2024 as the default year
                style={'width': '100%', 'margin-top': '10px'}
            ),
        ], style={'width': '40%'}),  # Set width for each dropdown and title container
        
        # Category Dropdown with its title underneath
        html.Div([
            html.H5("Inflation Categories:", style={'text-align': 'left', 'font-size': '12px', 'margin-top': '10px', 'margin-left':'10px'}),
            dcc.Dropdown(id='category-dropdown', options=[
                {'label': 'Deflation', 'value': 'Deflation'},
                {'label': 'Very Low Inflation', 'value': 'Very Low Inflation'},
                {'label': 'Low Inflation', 'value': 'Low Inflation'},
                {'label': 'Target Inflation', 'value': 'Target Inflation'},
                {'label': 'Moderate Inflation', 'value': 'Moderate Inflation'},
                {'label': 'High Inflation', 'value': 'High Inflation'},
                {'label': 'Very High Inflation', 'value': 'Very High Inflation'},
                {'label': 'Hyperinflation', 'value': 'Hyperinflation'},
            ], 
            placeholder="Select an inflation category", 
            value=None,  # Automatically select None as default
            style={'width': '50%', 'margin-bottom': '10px', 'margin-left': '0px'}),
        ], style={'width': '40%'}),
    ]),  # Closing container for side-by-side dropdowns
], style={'width': '55%', 'display': 'inline-block', 'padding': '10px'}),

        # Footer with copyright
    html.Div(
        "© 2024 Sophia Brauning",
        style={
            'position': 'fixed',  # Keeps it at the bottom
            'bottom': '0',  # Aligns at the bottom of the page
            'right': '0', # Aligns at the right side of the page
            'width': '60%',
            'align-items': 'center',
            'text-align': 'center',  # Centers the text
            'background-color': '#f8f9fa',  # Optional: Light background for visibility
            'padding': '10px',  # Padding for space
            'font-size': '12px',  # Smaller font size for the footer
            'color': '#6c757d'  # Muted text color
        }
    )

], style={'margin-left': '10px','margin-right': '10px'}),




# control the display of dropdowns
@app.callback(
    [Output('year-dropdown', 'style'), 
     Output('category-dropdown', 'style')],
    [Input('btn-map', 'n_clicks'), 
     Input('btn-bar', 'n_clicks')]
)
def toggle_dropdown_visibility(map_clicks, bar_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Default: Show map-related dropdowns by default
        return {'display': 'block'}, {'display': 'block'}

    # Determine which button was clicked
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'btn-map':
        # Show year and category dropdowns for the map, hide country dropdown
        return {'display': 'block'}, {'display': 'block'}
    elif button_id == 'btn-bar':
        # Only show the year dropdown for the bar plot
        return {'display': 'none'}, {'display': 'none'}

    # Default case
    return {'display': 'block'}, {'display': 'block'}

# callback to color active plot button
# Define button style change callback
@app.callback(
    [Output('btn-map', 'className'),
     Output('btn-bar', 'className')],
    [Input('btn-map', 'n_clicks'),
     Input('btn-bar', 'n_clicks')]
)
def set_button_style(map_clicks, bar_clicks):
    ctx = dash.callback_context

    # Check which button triggered the callback
    if ctx.triggered:
        clicked_button = ctx.triggered[0]['prop_id'].split('.')[0]
    else:
        clicked_button = None

    # Set className for each button based on the clicked one
    if clicked_button == 'btn-map':
        return 'active', 'inactive'
    elif clicked_button == 'btn-bar':
        return 'inactive', 'active'

    # Default: no button is active
    return 'active', 'inactive'

'''
# Callback to store the active plot based on button clicks
@app.callback(
    Output('active-plot', 'data'),
    [Input('btn-map', 'n_clicks'), 
     Input('btn-bar', 'n_clicks')]
)
def update_active_plot(map_clicks, bar_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return 'map'  # Default to map
    triggered_button = ctx.triggered[0]['prop_id'].split('.')[0]

    if triggered_button == 'btn-map':
        return 'map'
    elif triggered_button == 'btn-bar':
        return 'bar'

    return 'map'  # Default to map if no button is pressed

# Update plot area based on dropdowns and the active plot
@app.callback(
    Output('plot-area', 'children'),
    [Input('year-dropdown', 'value'), 
     Input('category-dropdown', 'value'),
     Input('active-plot', 'data')]
)
def update_plot_area(year, selected_category, active_plot):
    if year is None:
        year = DEFAULT_YEAR
    
    if active_plot == 'map':
        return update_map(year, selected_category)
    elif active_plot == 'bar':
        return dcc.Graph(figure=update_stacked_barplot())
	print("active_plot=", active_plot, "year=", year, "selected_category=", selected_category)#for debug

    return update_map(year, selected_category)  # Default to map
'''

@app.callback(
    Output('active-plot', 'data'),
    Input('btn-map', 'n_clicks'),
    Input('btn-bar', 'n_clicks'),
    prevent_initial_call=False,
)
def update_active_plot(map_clicks, bar_clicks):
    # default on initial load
    if ctx.triggered_id is None:
        return 'map'
    if ctx.triggered_id == 'btn-map':
        return 'map'
    if ctx.triggered_id == 'btn-bar':
        return 'bar'
    return 'map'

@app.callback(
    Output('plot-area', 'children'),
    Input('year-dropdown', 'value'),
    Input('category-dropdown', 'value'),
    Input('active-plot', 'data'),
)
def update_plot_area(year, selected_category, active_plot):
    year = year or DEFAULT_YEAR

    if active_plot == 'map':
        return update_map(year, selected_category)

    if active_plot == 'bar':
        fig = update_stacked_barplot()  # your global, year-independent table
        return dcc.Graph(figure=fig, config={'displayModeBar': False})

    # fallback
    return update_map(year, selected_category)




# Callback for the Folium Map

# color mapping and custom_legend creation function at the top of script
# Function to add a custom legend to the map
def add_custom_legend(m, category_colors):
    legend_html = '''
     <div style="
     position: absolute; 
     right: 10px; bottom: 50px; 
     width: 10px; height: auto; 
     background-color: white; z-index:9999; font-size:12px;
     border: 1px solid black; padding: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
     ">
     <strong>Inflation Categories</strong><br>
    '''
    for category, color in category_colors.items():
        legend_html += f'<i style="background:{color};width:12px;height:12px;display:inline-block;"></i>&nbsp;{category}<br>'

    legend_html += '</div>'
    
    m.get_root().html.add_child(folium.Element(legend_html))


'''
def update_map(year, selected_category):
    # Filter data based on the selected year and category
    filtered_data = country_year_mean[country_year_mean['Year'] == year]
    
    if selected_category:
        filtered_data = filtered_data[filtered_data['Inflation_Category'] == selected_category]

    # Initialize the map
    m = folium.Map(location=[20, 0], zoom_start=1)

    # Construct the GeoJSON file path
    try:
        geojson_file = str((DATA_DIR / f'Inflation_{year}.geojson').as_posix())

        # Add GeoJson layer for category-based coloring
        folium.GeoJson(
            geojson_file,
            style_function=lambda feature: {
                'fillColor': category_colors.get(
                    filtered_data.loc[
                        filtered_data['Area Code (ISO3)'] == feature['properties']['combined_iso_a3'],
                        'Inflation_Category'
                    ].values[0] if not filtered_data.loc[
                        filtered_data['Area Code (ISO3)'] == feature['properties']['combined_iso_a3']
                    ].empty else None, '#808080'  # Default to gray if category is missing
                ),
                'color': 'gray',
                'weight': 0.5,
                'fillOpacity': 0.7,
                'lineOpacity': 0.2
            },
            highlight_function=lambda feature: {
                'weight': 3,
                'color': 'blue',
                'fillOpacity': 0.7,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['name'],
                aliases=['Country:'],
            ),
            popup=folium.GeoJsonPopup(
                fields=['name_long', 'Value'],
                aliases=['Country:', 'Inflation Rate:'],
                localize=True,
                labels=True,
                sticky=False
            )
        ).add_to(m)

        # Add the custom legend outside of the plot area
        #add_custom_legend(m, category_colors)

    except Exception as e:
        print(f"Error: {e}")
        return html.Div(f"An error occurred while creating the map: {str(e)}")

    # Generate the map's HTML representation
    map_html = m._repr_html_()

    # Return the map
    return html.Div([
        html.Div(html.Iframe(srcDoc=map_html, width='100%', height='300px')),
    ], style={'padding-bottom': '0px'})
'''
def update_map(year, selected_category):
    import json

    # 1) Filter data for the selected year (and category if set)
    filtered_data = country_year_mean[country_year_mean['Year'] == year].copy()
    if selected_category:
        filtered_data = filtered_data[filtered_data['Inflation_Category'] == selected_category]

    # If nothing to show, still render a base map
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodbpositron")

    # 2) Build lookups from ISO3 -> category/value
    iso_col = "Area Code (ISO3)"
    if iso_col not in filtered_data.columns:
        return html.Div("Missing ISO3 column in data.", style={"color": "crimson"})

    value_col = next((c for c in ["Annual_Mean", "Value", "Inflation"] if c in filtered_data.columns), None)

    cat_by_iso = dict(
        zip(filtered_data[iso_col].astype(str),
            filtered_data["Inflation_Category"].astype(str))
    )
    val_by_iso = dict(
        zip(filtered_data[iso_col].astype(str),
            (filtered_data[value_col].tolist() if value_col else [None] * len(filtered_data)))
    )

    # 3) Helper to extract ISO3 from each feature's properties
    def extract_iso3(props):
        return (
            props.get("combined_iso_a3")
            or props.get("iso_a3")
            or props.get("ISO_A3")
            or props.get("ADM0_A3")
            or props.get("A3")
            or props.get("iso3")
            or props.get("Area Code (ISO3)")
        )

    # 4) Load GeoJSON as JSON and enrich feature props
    geojson_path = DATA_DIR / f"Inflation_{year}.geojson"
    if not geojson_path.exists():
        return html.Div(f"GeoJSON not found: {geojson_path}", style={"color": "crimson"})

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
    except Exception as e:
        return html.Div(f"Failed to read GeoJSON: {e}", style={"color": "crimson"})

    for feat in gj.get("features", []):
        props = feat.get("properties", {}) or {}
        iso3 = extract_iso3(props)
        iso3 = str(iso3) if iso3 is not None else None

        cat = cat_by_iso.get(iso3)
        val = val_by_iso.get(iso3)

        # Ensure consistent tooltip fields exist
        props["Category"] = cat if cat is not None else None
        props["Value"] = float(val) if (val is not None and pd.notna(val)) else None
        props["name"] = props.get("name") or props.get("NAME") or props.get("ADMIN") or props.get("name_long") or ""
        props["iso_a3"] = props.get("iso_a3") or props.get("ISO_A3") or props.get("ADM0_A3") or (iso3 or "")

        feat["properties"] = props

    # 5) Add styled GeoJSON (color by category)
    folium.GeoJson(
        gj,
        style_function=lambda feature: {
            "fillColor": category_colors.get(feature["properties"].get("Category"), "#808080"),
            "color": "white",
            "weight": 0.5,
            "fillOpacity": 0.75,
        },
        highlight_function=lambda feature: {"weight": 2, "color": "blue"},
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "iso_a3", "Category", "Value"],
            aliases=["Country", "ISO3", "Category", "Value"],
            localize=True,
        ),
    ).add_to(m)

    # Optional: add_custom_legend(m, category_colors)

    # 6) Return the map as HTML (same pattern you use)
    map_html = m._repr_html_()
    return html.Div(
        html.Iframe(srcDoc=map_html, width="100%", height="320px", style={"border": "0"}),
        style={"padding-bottom": "0px"},
    )

        
# Global insights
def default_insights():
    # Top countries maintaining target inflation
    target_data = country_year_mean[country_year_mean['Inflation_Category'] == 'Target Inflation']
    target_countries = target_data['Area'].value_counts().head(5)
    
    # Regions most affected by high to hyperinflation (2001–2024)
    high_inflation_regions = country_year_mean[
        country_year_mean['Inflation_Category'].isin(['High Inflation', 'Very High Inflation', 'Hyperinflation'])
    ]['Region'].value_counts().head(5)
    
    # Countries experiencing high inflation, very high inflation, and hyperinflation most frequently
    high_inflation_countries = country_year_mean[
        country_year_mean['Inflation_Category'].isin(['High Inflation', 'Very High Inflation', 'Hyperinflation'])
    ]['Area'].value_counts().head(5)
    
    # Global deflation and hyperinflation years
    deflationary_years = country_year_mean[country_year_mean['Inflation_Category'] == 'Deflation']['Year'].value_counts().head(5)
    hyperinflationary_years = country_year_mean[country_year_mean['Inflation_Category'] == 'Hyperinflation']['Year'].value_counts().head(5)
    
    # Prepare insights for display
    insights = html.Div([
        html.H4("Global Inflation Insights"),
        
        html.P("Top 5 hyperinflationary years globally:"),
        html.Ul([html.Li(f"{year}: {count} countries") for year, count in hyperinflationary_years.items()]),
        
        html.P("Top 5 deflationary years globally:"),
        html.Ul([html.Li(f"{year}: {count} countries") for year, count in deflationary_years.items()]),
        
        html.P("Top 5 countries maintaining target inflation the most frequently:"),
        html.Ul([html.Li(f"{country}: {count} times") for country, count in target_countries.items()]),
        
        html.P("Top 5 regions most affected by high to hyperinflation (2001–2024):"),
        html.Ul([html.Li(f"{region}: {count} occurrences") for region, count in high_inflation_regions.items()]),
        
        html.P("Top 5 countries experiencing high inflation, very high inflation, and hyperinflation most frequently:"),
        html.Ul([html.Li(f"{country}: {count} occurrences") for country, count in high_inflation_countries.items()])    
    ])
    
    return insights

# Insight for a selected inflation category
def update_category_insights(selected_category):
    # If no category is selected, display default insight for Target inflation
    if not selected_category:
        return html.Div([
            html.P("Showing insight for Target inflation (around 2%). Select another category for insights about it.")
        ] + generate_insight_for_category('Target Inflation'))
    
    # Generate insights for the selected category
    return generate_insight_for_category(selected_category)

# Helper function to avoid duplicating insight generation logic
def generate_insight_for_category(category):
    # Filter data for the selected category
    filtered_data = country_year_mean[country_year_mean['Inflation_Category'] == category]
    
    # Apply additional filter if the category is 'Target Inflation'
    #if category == 'Target Inflation':
    #    filtered_data = filtered_data[(filtered_data['Value'] >= 1.5) & (filtered_data['Value'] <= 2)]
    
    if filtered_data.empty:
        return [html.P("No insights available for this category.")]

    # Top 3 countries most frequently experiencing the selected category
    top_countries = filtered_data['Area'].value_counts().head(3)
    
    # Average inflation for this category
    avg_inflation = filtered_data['Value'].mean()
    
    # Find years with the most occurrences of the selected inflation category
    top_years = filtered_data['Year'].value_counts().head(3)
    
    # Minimum and maximum inflation in the category
    min_inflation = filtered_data['Value'].min()
    max_inflation = filtered_data['Value'].max()

    # Prepare insights for display
    return [
        html.H4(f"Insights for {category}"),
        html.P(f"Top 3 countries most frequently experiencing {category}:"),
        html.Ul([html.Li(f"{country}: {count} times") for country, count in top_countries.items()]),
        html.P(f"Average inflation in this category: {avg_inflation:.2f}%"),
        html.P(f"Minimum inflation in this category: {min_inflation:.2f}%"),
        html.P(f"Maximum inflation in this category: {max_inflation:.2f}%"),
        html.P(f"Top 3 years with the most occurrences of {category}:"),
        html.Ul([html.Li(f"{year}: {count} occurrences") for year, count in top_years.items()])
    ]


# callback for updating the insight text
@app.callback(
    Output('insight-text', 'children'),
    [Input('category-dropdown', 'value')]
)
def update_insight(selected_category):
    return update_category_insights(selected_category)  # Show insights for the selected category

    
# update global insight (info text)
@app.callback(
    Output('info-text', 'children'),
    [Input('category-dropdown', 'value')]
)
def update_info_text(selected_category):
    return  default_insights()


# wordcloud update callback
# Callback for category chart/word cloud, top years, and inflation range
@app.callback(
    [Output('wordcloud-graph', 'src'),  # Word cloud as image
     Output('inflation-range', 'children')],  # Inflation range text
    [Input('category-dropdown', 'value'), Input('year-dropdown', 'value')]
)
def update_category_graph_top_years_and_range(selected_category, selected_year):
    # If no category or year is selected, show the default word cloud based on average inflation
    if selected_category is None and selected_year:
        # Calculate average inflation for each country from 2001–2024
        default_data = country_year_mean.dropna(subset=['Area', 'Value'])
        default_data = default_data[default_data['Year'] == selected_year]
        country_avg_inflation = default_data.groupby('Area')['Value'].mean().to_dict()  # Mean inflation by country

        # Generate word cloud sized by average inflation
        word_cloud_image = generate_word_cloud(country_avg_inflation)

        # Calculate overall inflation range across all years
        min_inflation = default_data['Value'].min()
        max_inflation = default_data['Value'].max()
        inflation_range = f"Inflation rates for {selected_year} ranged from {min_inflation:.2f}% to {max_inflation:.2f}%."

        return (
            f'data:image/png;base64,{word_cloud_image}',  # Update src for html.Img
            inflation_range  # Update inflation range text
        )
    
    # Filter data based on category and year
    filtered_data = country_year_mean.dropna(subset=['Area', 'Value'])
    if selected_category:
        filtered_data = filtered_data[filtered_data['Inflation_Category'] == selected_category]
    if selected_year:
        filtered_data = filtered_data[filtered_data['Year'] == selected_year]

    # If no data after filtering, return appropriate message
    if filtered_data.empty:
        return (
            None,  
            "No inflation range available for the selected category/year."
        )

    # Generate word cloud for the selected category and year based on inflation values
    # Generate word cloud for the selected category and year based on inflation values
    if selected_category == "Deflation":
        # Adjust the values so countries with more deflation (further from zero) are larger
        country_inflation = {country: abs(value) for country, value in zip(filtered_data['Area'], filtered_data['Value'])}
    else:
        # Default behavior: use the actual inflation values
        country_inflation = dict(zip(filtered_data['Area'], filtered_data['Value']))

    word_cloud_image = generate_word_cloud(country_inflation)

    #country_inflation = dict(zip(filtered_data['Area'], filtered_data['Value']))
    #word_cloud_image = generate_word_cloud(country_inflation)

    # Calculate inflation range for the filtered data
    min_inflation = filtered_data['Value'].min()
    max_inflation = filtered_data['Value'].max()
    inflation_range = f"Inflation rates for inflation category '{selected_category}' in {selected_year} ranged from {min_inflation:.2f}% to {max_inflation:.2f}%."

    return (
        f'data:image/png;base64,{word_cloud_image}',  # Update word cloud src
        inflation_range  # Update inflation range
    )


if __name__ == "__main__":
    import os, argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8050")))
    parser.add_argument("--debug", action="store_true", help="Enable Dash debug (dev tools). Avoid in Colab.")
    args = parser.parse_args()

    # In Colab / headless envs: force-disable the reloader even if debug=True sneaks in
    use_reloader = False

    print(f"Starting Dash on http://{args.host}:{args.port} (debug={args.debug}, reloader={use_reloader})")
    # Dash ≥ 2.17
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=use_reloader)

#if __name__ == '__main__':
#    app.run_server(debug=True)
