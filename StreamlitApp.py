import streamlit as st, pandas as pd, requests, plotly.express as px

base_url = 'http://127.0.0.1:8000/api'

st.title('Water Quality Dashboard')

st.sidebar.header('Filters')

# Sidebar filters
min_temp = st.sidebar.slider('Minimum Temperature (°C)', value=0.0, max_value=50.0)
max_temp = st.sidebar.slider('Maximum Temperature (°C)', value=0.0, max_value=50.0)
min_sal = st.sidebar.slider('Minimum Salinity (ppt)', value=0.0, max_value=50.0)
max_sal = st.sidebar.slider('Maximum Salinity (ppt)', value=0.0, max_value=50.0)
min_odo = st.sidebar.slider('Minimum ODO (mg/L)', value=0.0, max_value=20.0)
max_odo = st.sidebar.slider('Maximum ODO (mg/L)', value=0.0, max_value=20.0)
limit = st.sidebar.number_input('Limit', value=100, min_value=1, max_value=1000)
skip = st.sidebar.number_input('Skip', value=0, min_value=0)

st.sidebar.header('Outliers')
outlier_field = st.sidebar.selectbox('Field', ['Temperature_c', 'Salinity_ppt', 'ODO_mg_L'])
outlier_method = st.sidebar.selectbox('Method', ['z-score', 'iqr'])
k = st.sidebar.number_input('Threshold (k)', value=3.0, step=0.1)

# Query parameters
params = {'limit': limit, 'skip': skip}

if min_temp != 0.0: params['min_temp'] = min_temp
if max_temp != 0.0: params['max_temp'] = max_temp
if min_sal != 0.0: params['min_sal'] = min_sal
if max_sal != 0.0: params['max_sal'] = max_sal
if min_odo != 0.0: params['min_odo'] = min_odo
if max_odo != 0.0: params['max_odo'] = max_odo

# Fetch observations
df = pd.DataFrame()
obs_response = requests.get(f'{base_url}/observations', params=params)
if obs_response.status_code == 200:
    obs_data = obs_response.json().get('items', [])
    df = pd.DataFrame(obs_data)
    if not df.empty:
        st.subheader('Observation Table')
        st.dataframe(df)
else:
    st.error('Failed to fetch observations')

# Fetch stats
stats_response = requests.get(f'{base_url}/stats')
if stats_response.status_code == 200:
    stats_data = stats_response.json()
    st.subheader('Statistics')
    st.json(stats_data)
else:
    st.error('Failed to fetch statistics')

if not df.empty:
    # Line chart
    if "Time_hh_mm_ss" in df.columns and "Temperature_c" in df.columns:
        fig_line = px.line(df, x="Time_hh_mm_ss", y="Temperature_c", title="Temperature Over Time")
        st.plotly_chart(fig_line)

    # Histogram
    if "Salinity_ppt" in df.columns:
        fig_hist = px.histogram(df, x="Salinity_ppt", nbins=20, title="Salinity Distribution")
        st.plotly_chart(fig_hist)

    # Scatter plot
    if all(col in df.columns for col in ["Temperature_c", "Salinity_ppt", "ODO_mg_L"]):
        fig_scatter = px.scatter(df, x="Temperature_c", y="Salinity_ppt",
                                 color="ODO_mg_L", title="Temperature vs. Salinity colored by ODO")
        st.plotly_chart(fig_scatter)

# Fetch outliers
outliers_response = requests.get(f'{base_url}/outliers', params={
    'field': outlier_field,
    'method': outlier_method,
    'k': k
})
if outliers_response.status_code == 200:
    outliers = pd.DataFrame(outliers_response.json().get('items', []))
    st.subheader('Outliers')
    st.dataframe(outliers)
else:
    st.error('Failed to fetch outliers')

# Map
if "Latitude" in df.columns and "Longitude" in df.columns:
    df['latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    st.subheader('Vehicle Path Map')
    st.map(df[['latitude', 'longitude']].dropna())
