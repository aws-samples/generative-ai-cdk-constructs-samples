#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import yaml

REQUIRED_PROPERTIES = ['language', 'company_name', 'contract_type', 'company_party_type', 'other_party_type']


class AppProperties:
    def __init__(self, properties_file_path):
        with open(properties_file_path, 'r') as f:
            self.properties = yaml.safe_load(f)

            missing_properties = [prop for prop in REQUIRED_PROPERTIES if prop not in self.properties]

            if missing_properties:
                raise ValueError(f'Missing property in properties file: {missing_properties}')

    def get_all_property_names(self):
        return self.properties.keys()

    def get_value(self, property_name, fallback_value=''):
        return self.properties.get(property_name, fallback_value)
