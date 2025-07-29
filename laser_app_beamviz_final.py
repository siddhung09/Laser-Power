
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.special import i0

st.set_page_config(page_title="Laser Power Transfer - Theia Labs", layout="centered")
st.title("🔋 End-to-End Laser Power Transmission Model (Physical Formulas)")

# === Input Parameters ===
st.sidebar.header("System Parameters")

wavelength = 445e-9  # [m]
distance = st.sidebar.number_input("Propagation Distance [m]", min_value=1.0, value=5.0, step=1.0, format="%.2f")
w0 = st.sidebar.number_input("Beam Waist w0 [m]", 0.001, 0.1, 0.05)
receiver_radius = st.sidebar.number_input("Receiver Radius [m]", 0.01, 1.0, 0.3)
offset = st.sidebar.number_input("Beam Offset at Receiver d [m]", 0.0, 10.0, 0.01)
pointing_error = st.sidebar.number_input("Pointing Error [rad]", 0.0, 1e-6, 1e-8)
num_lasers = st.sidebar.number_input("Number of Lasers", 1, 10, 1)
input_power_kW = st.sidebar.number_input("Input Power (kW)", 0.1, 10.0, 0.4)

# Constants
driver_eff = 0.95
laser_eff = 0.30
optical_eff = 0.97
receiver_optics_eff = (1 - 0.01)**4
pv_eff = 0.60
conditioning_eff = 0.90

input_power = input_power_kW * 1000  # W

# === Power Calculations ===
power = []
labels = []

required_driver_input = input_power / driver_eff
driver_output = required_driver_input * driver_eff
power.append(driver_output)
labels.append("Driver Output")

laser_output = driver_output * laser_eff * num_lasers
power.append(laser_output)
labels.append("Laser Output")

optics_output = laser_output * optical_eff
power.append(optics_output)
labels.append("After Optics")

delta_r = pointing_error * distance
pointing_eff = np.exp(-2 * (delta_r / w0)**2)
pointing_output = optics_output * pointing_eff
power.append(pointing_output)
labels.append("After Pointing")

atmospheric_output = pointing_output
power.append(atmospheric_output)
labels.append("Atmospheric (Skipped)")

# === Correct Geometrical Efficiency using Gaussian Overlap with Offset ===
w_final = w0 * np.sqrt(1 + (wavelength * distance / (np.pi * w0**2))**2)

def gaussian_overlap(R, w, d):
    from scipy.special import i0
    term = (4 * R * d) / (w ** 2)
    eta = 1 - np.exp(-2 * d**2 / w**2) * np.exp(-2 * R**2 / w**2) * i0(term)
    return max(eta, 0.0)

geo_eff = gaussian_overlap(receiver_radius, w_final, offset)
geo_output = atmospheric_output * geo_eff
power.append(geo_output)
labels.append("After Geometric Loss")

collection_eff = 1 - np.exp(-2 * (receiver_radius / w_final)**2)
collection_output = geo_output * collection_eff
power.append(collection_output)
labels.append("After Collection")

receiver_optics_output = collection_output * receiver_optics_eff
power.append(receiver_optics_output)
labels.append("After Receiver Optics")

pv_area = np.pi * receiver_radius**2
pv_output = receiver_optics_output * pv_area * pv_eff
power.append(pv_output)
labels.append("PV Output")

final_output = pv_output * conditioning_eff
power.append(final_output)
labels.append("Final Output")

# === Bar Chart ===
st.subheader("📊 Power at Each Stage")
fig = go.Figure(data=[go.Bar(x=labels, y=power, marker_color='green')])
fig.update_layout(title="Power Through Each Stage", yaxis_title="Power (W)", xaxis_title="System Stage")
st.plotly_chart(fig)
st.metric("⚡ Final Output Power", f"{final_output:.2f} W")
st.metric("📈 Total System Efficiency", f"{(final_output / required_driver_input) * 100:.2f} %")

# === Beam Propagation Plot ===
st.subheader("🔭 Beam Propagation and Circular Receiver")

z_vals = np.linspace(0, distance, 300)
w_z = w0 * np.sqrt(1 + (wavelength * z_vals / (np.pi * w0**2))**2)
beam_offset_z = offset * (z_vals / distance)

x_vals = z_vals
y_upper = beam_offset_z + w_z
y_lower = beam_offset_z - w_z

theta = np.linspace(0, 2 * np.pi, 100)
receiver_x = distance + 0.01 * np.cos(theta)
receiver_y = receiver_radius * np.sin(theta)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=x_vals, y=y_upper, mode='lines', name='Beam Top', line=dict(color='blue')))
fig2.add_trace(go.Scatter(x=x_vals, y=y_lower, mode='lines', name='Beam Bottom', line=dict(color='blue')))
fig2.add_trace(go.Scatter(x=receiver_x, y=receiver_y, mode='lines', name='Receiver', fill='toself',
                          fillcolor='rgba(0,255,0,0.2)', line=dict(color='green')))

fig2.update_layout(title="2D Beam Envelope vs Circular Receiver",
                   xaxis_title="Distance from Transmitter (m)",
                   yaxis_title="Height (m)",
                   showlegend=True)
st.plotly_chart(fig2)

st.caption("Beam starts centered at transmitter; offset applies progressively toward receiver. Geometric loss is now strictly enforced.")
