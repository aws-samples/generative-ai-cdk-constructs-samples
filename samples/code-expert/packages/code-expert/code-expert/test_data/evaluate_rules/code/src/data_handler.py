#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

class DataHandler:
    def process_data(self, data):
        try:
            result = self.complex_operation(data)
            return result
        except:  # Bare except clause
            print("An error occurred")  # Silently handling error

    def complex_operation(self, data):
        try:
            # Some complex operation
            return data * 2
        except Exception:  # Too broad exception
            pass  # Silent pass
