#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import streamlit as st

from args import Args

# Load arguments
Args()

st.set_page_config(page_title='Code Expert', page_icon=':material/code:')
st.logo('logo.png', size='large')

# Hack to remove the 'Deploy' button
st.markdown('''
<style>
    .stAppDeployButton {
        visibility: hidden;
    }
</style>
''', unsafe_allow_html=True)

start_execution_page = st.Page('start_execution.py', title='Start execution', icon=':material/start:')
executions_page = st.Page('executions.py', title='Executions', icon=':material/list_alt:')
pg = st.navigation({'Code Expert': [start_execution_page, executions_page]})
pg.run()
