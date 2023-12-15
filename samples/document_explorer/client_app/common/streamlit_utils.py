# Third party imports 
import streamlit as st

def hide_deploy_button():
  """Hide default deploy button."""

  st.markdown(
    """
    <style>
    .stDeployButton {
            visibility: hidden;
        }
    </style>
    """, 
    unsafe_allow_html=True
  )