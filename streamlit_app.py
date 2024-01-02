#                _          __  __      _                     
# __      ____ _| |_ ___ _ _\ \/ /_ __ | | ___  _ __ ___ _ __ 
# \ \ /\ / / _` | __/ _ \ '__\  /| '_ \| |/ _ \| '__/ _ \ '__|
#  \ V  V / (_| | ||  __/ |  /  \| |_) | | (_) | | |  __/ |   
#   \_/\_/ \__,_|\__\___|_| /_/\_\ .__/|_|\___/|_|  \___|_|   
#                                |_|                          
# Author: Cameron Roberts

# RUN: streamlit run streamlit_app.py
# MacOS ctrl + C to close app from terminal

import streamlit as st
import pandas as pd
import datetime
import requests
import plotly.express as px
import matplotlib.pyplot as plt

st.title(":sweat_drops: Queensland Water Data Explorer")
st.markdown('''
            This app utilises data from [Queensland Governments Water Monitoring Information Portal](https://water-monitoring.information.qld.gov.au/)  
            It facilitates quick visualisation of the time series dataset and provides an avenue for the user to check exceedance probability of their own desired threshold.  
            '''
            )

#import WMIP site list
@st.cache_data
def wmip_sites():
    url = 'https://water-monitoring.information.qld.gov.au/cgi/webservice.exe?{"function":"get_db_info","version":"3","params":{"table_name":"SITE","return_type":"array","field_list":["STATION","STNAME","REGION","STNTYPE","LATITUDE","LONGITUDE","COMMENCE","CEASE"]}}'
    r = requests.get(url)
    x = r.json()
    df = pd.DataFrame(x['return'])
    df = pd.json_normalize(df['rows'])
    df = df[df['cease'] == 18991230]
    df = df[df['stntype'].isin(['G', 'GQ'])].sort_values(by='station')
    # Convert 'latitude' and 'longitude' columns to numeric
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    return df
site_list = wmip_sites()


#User Interface
#site = st.sidebar.text_input("Gauging Station Number:", value ="110001D", key="site")
sitename = st.sidebar.selectbox(
    "Gauging Station:",
    options=site_list['stname'],
    index=25
)
option = st.sidebar.selectbox(
    'Select Parameter:',
    ('level', 'discharge', 'rainfall', 'temperature', 'conductivity', 'turbidity'))

dt = st.sidebar.date_input(
    "Select Lookback Date:",
    datetime.date(2019, 7, 1),
    datetime.date(1970, 1, 1),
    format="YYYY/MM/DD"
)
specific_value = st.sidebar.number_input("Exceedance probability value:")

#site = st.session_state.site
site = site_list.loc[site_list['stname'] == sitename, 'station'].values[0]
#print(sitename)
print(site)
param = option
start_time = dt.strftime('%Y%m%d')

# Get the current date
current_date = datetime.datetime.now()
# Add one day to the current date
next_day = current_date + datetime.timedelta(days=1)
# Format the date as YYYYMMDD
end_time = next_day.strftime('%Y%m%d')
#end_time = datetime.datetime.now().strftime('%Y%m%d')


@st.cache_data
def wmip_hist(site, start_time, var, datasource = 'AT', end_time = end_time):
    #translate var input into the HYdstra varfrom/varto format
    match var:
        case "level":
            var = "varfrom=100.00&varto=100.00"
        case "discharge":
            var ="varfrom=100.00&varto=140.00"
        case "rainfall":
            var ="varfrom=10.00&varto=10.00"
        case "temperature":
            var ="varfrom=2080.00&varto=2080.00"
        case "conductivity":
            var ="varfrom=2010.00&varto=2010.00"
        case "pH":
            var ="varfrom=2100.00&varto=2100.00"
        case "turbidity":
            var ="varfrom=2030.00&varto=2030.00"
        case _:
            print("invalid variable input")
    
    df = pd.read_csv('https://water-monitoring.information.qld.gov.au/cgi/webservice.exe?function=get_ts_traces&site_list='+site+'&datasource='+datasource+'&'+var+'&start_time='+start_time+'&end_time='+end_time+'&data_type=mean&interval=hour&multiplier=1&format=csv')
    df['time'] = pd.to_datetime(df['time'], format='%Y%m%d%H%M%S')
    return df

#data import
df = wmip_hist(site= site, start_time= start_time, var= param)
df = df[df['quality'] != 255]

#st.line_chart(data= df, x= 'time',y= 'value')
#plotly time series
fig = px.line(df, x="time", y="value")
fig.update_layout(
        xaxis_title='',
        yaxis_title=df['varname'].values[1],
        title=sitename
        # Add more layout customization here
    )
st.plotly_chart(fig)

#exceedance prob
prb = df
prb['cdf'] = prb['value'].rank(method='average', pct=True)
prb = prb.sort_values('cdf', ascending=False)

fig2 = plt.figure()
plt.semilogy(prb['cdf'] * 100, prb['value'])
plt.xlim(100, 0)
plt.xlabel('Exceedance probability [%]')
plt.ylabel(prb['varname'].values[1])
plt.grid(True, which="both", ls=':', color='0.65')
plt.axhline(y=specific_value, color='r', linestyle='--')  # Adding a dotted line at specific_value

st.pyplot(fig2)

lat = site_list.loc[site_list['stname'] == sitename, 'latitude'].values[0]
lon = site_list.loc[site_list['stname'] == sitename, 'longitude'].values[0]
st.map(site_list[site_list['stname'] == sitename])
