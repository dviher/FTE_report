import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Load and process the data
@st.cache
def load_data(file):
    df = pd.read_excel(file, sheet_name='SQL_202405291057', engine='openpyxl')
    df['BASIC_START_DATE'] = pd.to_datetime(df['BASIC_START_DATE'])
    return df

def summarize_data(df, material_type, time_range):
    faze_mapping = {
        'PC01': 'Cutting',
        'PS01': 'Slaughtering',
        'PD01': 'Deboning',
        'PP01': 'Packaging',
        'PX01': 'Service Slaughtering'
    }

    column_order = ['Plan', 'Target', 'Actual']
    df['DISASSEMBLY_FAZE_MAPPED'] = df['DISASSEMBLY_FAZE'].map(faze_mapping)
    df = df[(df['BASIC_START_DATE'] >= time_range[0]) & (df['BASIC_START_DATE'] <= time_range[1])]

    if material_type == 'input':
        daily_summary_df = df.drop_duplicates(subset=['ORDER_NUMBER', 'SKU_CODE', 'BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED']).groupby(['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED']).agg({
            'PLAN_QTY': 'sum',
            'TARGET_QTY': 'sum',
            'ACTUAL_QTY': 'sum'
        }).reset_index()
        total_summary_df = df.drop_duplicates(subset=['ORDER_NUMBER', 'SKU_CODE']).groupby('DISASSEMBLY_FAZE_MAPPED').agg({
            'PLAN_QTY': 'sum',
            'TARGET_QTY': 'sum',
            'ACTUAL_QTY': 'sum'
        }).reset_index()
        daily_summary_df.rename(columns={'PLAN_QTY': 'Plan', 'TARGET_QTY': 'Target', 'ACTUAL_QTY': 'Actual'}, inplace=True)
        total_summary_df.rename(columns={'PLAN_QTY': 'Plan', 'TARGET_QTY': 'Target', 'ACTUAL_QTY': 'Actual'}, inplace=True)
    elif material_type == 'output':
        daily_summary_df = df.groupby(['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED', 'QTY_TYPE_NAME']).agg({
            'QTY': 'sum'
        }).reset_index()
        total_summary_df = df.groupby(['DISASSEMBLY_FAZE_MAPPED', 'QTY_TYPE_NAME']).agg({
            'QTY': 'sum'
        }).reset_index()
        daily_summary_df = daily_summary_df.pivot(index=['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED'], columns='QTY_TYPE_NAME', values='QTY').reset_index()
        total_summary_df = total_summary_df.pivot(index='DISASSEMBLY_FAZE_MAPPED', columns='QTY_TYPE_NAME', values='QTY').reset_index()
        daily_summary_df.rename(columns={'PLAN': 'Plan', 'TARGET': 'Target', 'ACTUAL': 'Actual'}, inplace=True)
        total_summary_df.rename(columns={'PLAN': 'Plan', 'TARGET': 'Target', 'ACTUAL': 'Actual'}, inplace=True)
    elif material_type == 'working_hours':
        df['Working_Hours'] = df['Working_hours_Plan_L3'] + df['Working_hours_Plan_L4']
        daily_summary_df = df.groupby(['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED', 'QTY_TYPE_NAME']).agg({
            'Working_Hours': 'sum'
        }).reset_index()
        total_summary_df = df.groupby(['DISASSEMBLY_FAZE_MAPPED', 'QTY_TYPE_NAME']).agg({
            'Working_Hours': 'sum'
        }).reset_index()
        daily_summary_df = daily_summary_df.pivot(index=['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED'], columns='QTY_TYPE_NAME', values='Working_Hours').reset_index()
        total_summary_df = total_summary_df.pivot(index='DISASSEMBLY_FAZE_MAPPED', columns='QTY_TYPE_NAME', values='Working_Hours').reset_index()
        daily_summary_df.rename(columns={'PLAN': 'Plan', 'TARGET': 'Target', 'ACTUAL': 'Actual'}, inplace=True)
        total_summary_df.rename(columns={'PLAN': 'Plan', 'TARGET': 'Target', 'ACTUAL': 'Actual'}, inplace=True)

    daily_summary_df = daily_summary_df.fillna(0)
    daily_summary_df = daily_summary_df[['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED'] + column_order]
    total_summary_df = total_summary_df.fillna(0)
    total_summary_df = total_summary_df[['DISASSEMBLY_FAZE_MAPPED'] + column_order]
    return daily_summary_df, total_summary_df

def calculate_productivity(daily_material_summary, daily_working_hours_summary):
    daily_material_summary = daily_material_summary.set_index(['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED'])
    daily_working_hours_summary = daily_working_hours_summary.set_index(['BASIC_START_DATE', 'DISASSEMBLY_FAZE_MAPPED'])

    productivity_df = daily_working_hours_summary.copy()
    for col in ['Plan', 'Target', 'Actual']:
        with np.errstate(divide='ignore', invalid='ignore'):
            productivity_df[col] = np.where(daily_material_summary[col] != 0, (daily_working_hours_summary[col] * 3600) / daily_material_summary[col], np.nan)

    productivity_df.reset_index(inplace=True)
    productivity_df = productivity_df.fillna(0)
    return productivity_df

def calculate_total_productivity(total_material_summary, total_working_hours_summary):
    total_material_summary = total_material_summary.set_index('DISASSEMBLY_FAZE_MAPPED')
    total_working_hours_summary = total_working_hours_summary.set_index('DISASSEMBLY_FAZE_MAPPED')

    productivity_df = total_working_hours_summary.copy()
    for col in ['Plan', 'Target', 'Actual']:
        with np.errstate(divide='ignore', invalid='ignore'):
            productivity_df[col] = np.where(total_material_summary[col] != 0, (total_working_hours_summary[col] * 3600) / total_material_summary[col], np.nan)

    productivity_df.reset_index(inplace=True)
    productivity_df = productivity_df.fillna(0)
    return productivity_df

def plot_phase_productivity(productivity_df, phase, material_type):
    phase_df = productivity_df[productivity_df['DISASSEMBLY_FAZE_MAPPED'] == phase]
    fig = go.Figure()
    for col, color in zip(['Plan', 'Target', 'Actual'], ['lightgreen', 'green', 'darkgreen']):
        fig.add_trace(go.Scatter(x=phase_df['BASIC_START_DATE'], y=phase_df[col], mode='lines+markers', name=f'{material_type} {col}', line=dict(color=color)))
    fig.update_layout(title=f'{phase} Productivity ({material_type})', xaxis_title='Date', yaxis_title='Productivity (seconds per unit)')
    return fig

def plot_all_phases(productivity_df, material_type):
    phases = productivity_df['DISASSEMBLY_FAZE_MAPPED'].unique()
    fig = make_subplots(rows=len(phases), cols=1, shared_xaxes=True, subplot_titles=[f'{phase} ({material_type})' for phase in phases])
    for i, phase in enumerate(phases):
        phase_df = productivity_df[productivity_df['DISASSEMBLY_FAZE_MAPPED'] == phase]
        for col, color in zip(['Plan', 'Target', 'Actual'], ['lightgreen', 'green', 'darkgreen']):
            fig.add_trace(go.Scatter(x=phase_df['BASIC_START_DATE'], y=phase_df[col], mode='lines+markers', name=f'{phase} {col}', line=dict(color=color)), row=i+1, col=1)
    fig.update_layout(title=f'{material_type.capitalize()} Productivity per Phase', height=300*len(phases), showlegend=False)
    return fig

# Streamlit interface
st.title("Production Data Analysis")

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.write("Data loaded successfully!")

    min_date = df['BASIC_START_DATE'].min()
    max_date = df['BASIC_START_DATE'].max()
    date_range = st.date_input("Select date range", [min_date, max_date], min_value=min_date, max_value=max_date)

    if st.button("Generate Report"):
        time_range = [pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])]

        input_daily_summary, input_total_summary = summarize_data(df, 'input', time_range)
        output_daily_summary, output_total_summary = summarize_data(df, 'output', time_range)
        working_hours_daily_summary, working_hours_total_summary = summarize_data(df, 'working_hours', time_range)

        input_productivity = calculate_productivity(input_daily_summary, working_hours_daily_summary)
        output_productivity = calculate_productivity(output_daily_summary, working_hours_daily_summary)
        total_input_productivity = calculate_total_productivity(input_total_summary, working_hours_total_summary)
        total_output_productivity = calculate_total_productivity(output_total_summary, working_hours_total_summary)

        # Plotting
        st.header("Input Materials Productivity per Phase")
        st.plotly_chart(plot_all_phases(input_productivity, "Input"))

        st.header("Output Materials Productivity per Phase")
        st.plotly_chart(plot_all_phases(output_productivity, "Output"))

        st.header("Summary Tables")
        st.write("Input Summary")
        st.dataframe(input_total_summary)

        st.write("Output Summary")
        st.dataframe(output_total_summary)

        st.write("Working Hours Summary")
        st.dataframe(working_hours_total_summary)

        st.write("Total Input Productivity")
        st.dataframe(total_input_productivity)

        st.write("Total Output Productivity")
        st.dataframe(total_output_productivity)
