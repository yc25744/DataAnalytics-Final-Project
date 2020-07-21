#get_default_color
import dash
#pip install dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

#import necessary libraries
from plotly import tools
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import plotly.graph_objects as go #for calling graph objects from plotly library.
import pandas as pd
import numpy as np 
import requests
#!pip install wget
from datetime import datetime
from scipy.interpolate import interp1d

#loading global COVID-19 datasets
death_df =  pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv')
confirmed_df = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv')
recovered_df = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv')
country_df = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/web-data/data/cases_country.csv')

dates = confirmed_df.columns[4:]
confirmed_df_long = confirmed_df.melt(
    id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], 
    value_vars=dates, 
    var_name='Date', 
    value_name='Confirmed'
)
death_df_long = death_df.melt(
    id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], 
    value_vars=dates, 
    var_name='Date', 
    value_name='Deaths'
)
recovered_df_long = recovered_df.melt(
    id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], 
    value_vars=dates, 
    var_name='Date', 
    value_name='Recovered'
)

recovered_df_long = recovered_df_long[recovered_df_long['Country/Region']!='Canada']

full_table = confirmed_df_long.merge(
  right=death_df_long, 
  how='left',
  on=['Province/State', 'Country/Region', 'Date', 'Lat', 'Long']
)
# Merging full_table and recovered_df_long
full_table = full_table.merge(
  right=recovered_df_long, 
  how='left',
  on=['Province/State', 'Country/Region', 'Date', 'Lat', 'Long']
)

full_table['Date'] = pd.to_datetime(full_table['Date'])
full_table['Recovered'] = full_table['Recovered'].fillna(0)

ship_rows = full_table['Province/State'].str.contains('Grand Princess') | full_table['Province/State'].str.contains('Diamond Princess') | full_table['Country/Region'].str.contains('Diamond Princess') | full_table['Country/Region'].str.contains('MS Zaandam')
full_ship = full_table[ship_rows]
full_table = full_table[~(ship_rows)]
full_table['Active'] = full_table['Confirmed'] - full_table['Deaths'] - full_table['Recovered']
full_grouped = full_table.groupby(['Date', 'Country/Region', 'Lat', 'Long'])['Confirmed', 'Deaths', 'Recovered', 'Active'].sum().reset_index()

temp = full_grouped.groupby(['Country/Region', 'Date', ])['Confirmed', 'Deaths', 'Recovered']
temp = temp.sum().diff().reset_index()
mask = temp['Country/Region'] != temp['Country/Region'].shift(1)
temp.loc[mask, 'Confirmed'] = np.nan
temp.loc[mask, 'Deaths'] = np.nan
temp.loc[mask, 'Recovered'] = np.nan
# renaming columns
temp.columns = ['Country/Region', 'Date', 'New cases', 'New deaths', 'New recovered']
# merging new values
full_grouped = pd.merge(full_grouped, temp, on=['Country/Region', 'Date'])
# filling na with 0
full_grouped = full_grouped.fillna(0)
# fixing data types
cols = ['New cases', 'New deaths', 'New recovered']
full_grouped[cols] = full_grouped[cols].astype('int')
# 
full_grouped['New cases'] = full_grouped['New cases'].apply(lambda x: 0 if x<0 else x)
full_grouped["Date"] = full_grouped["Date"].dt.strftime('%Y/%m/%d')



#plot
def global_animation():
    fig = px.scatter_mapbox(full_grouped,
                            lat="Lat", 
                            lon="Long",                       
                            color="Confirmed", 
                            size=full_grouped['Confirmed']**0.5*50,
                            template='seaborn',
                            color_continuous_scale="spectral", 
                            size_max=50, 
                            animation_frame='Date', 
                            zoom=0.7, 
                            hover_data= ['Country/Region'])
    
    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r":1,"t":1,"l":1,"b":1})
    #update frame speed
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 200
    #update different layouts
    fig.layout.sliders[0].currentvalue.prefix=""
    fig.layout.sliders[0].len=.9
    fig.layout.sliders[0].currentvalue.font.color="black"
    fig.layout.sliders[0].currentvalue.font.size=18
    return fig

death_df.drop('Province/State', axis=1, inplace=True)
confirmed_df.drop('Province/State', axis=1, inplace=True)
recovered_df.drop('Province/State', axis=1, inplace=True)
country_df.drop(['People_Tested', 'People_Hospitalized'], axis=1, inplace=True)

death_df.rename(columns={'Country/Region': 'Country'}, inplace=True)
confirmed_df.rename(columns={'Country/Region': 'Country'}, inplace=True)
recovered_df.rename(columns={'Country/Region': 'Country'}, inplace=True)
country_df.rename(columns={'Country_Region': 'Country', 'Long_': 'Long'}, inplace=True)
country_df.sort_values('Confirmed', ascending=False, inplace=True)

#top ten countries by case
def bubble_fig():
    fig = px.scatter(confirmed_df.head(10), 
    x = 'Country', 
    y ='Confirmed', 
    size = 'Confirmed', 
    color = 'Country', 
    hover_name = 'Country',
    size_max = 50)
    return fig 

df_list = [confirmed_df, recovered_df, death_df]

def plot_cases_for_country(ad):
    labels = ['Confirmed', 'Recoverd', 'Deaths']
    colors = ['#5e4fa2', '#66c2a5', '#d53e50']
    mode_size = [4,4,4]
    line_size = [4,4,4]

    fig = go.Figure()
    
    for i, df in enumerate (df_list):
        if ad =='world' or ad =='World':
            x_data = np.array(list (df.iloc[:,5:].columns))
            y_data = np.sum(np.asarray(df.iloc[:,5:]),axis = 0)
        
        else:
            x_data = np.array(list (df.iloc[:,5:].columns))
            y_data = np.sum(np.asarray(df[df['Country']==ad].iloc[:,5:]),axis = 0)
                        
        fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines+markers',name=labels[i],
            line=dict(color=colors[i], width=line_size[i]),
            connectgaps=True,
            text = "Total " +str(labels[i]+ ":" +str(y_data[-1]))
         )) 
    return fig
