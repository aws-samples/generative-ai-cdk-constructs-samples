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
class LLMNotLoadedException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = f"[501] The LLM {message} was not loaded correctly"
        

class KnowledgeBaseIDNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = f"[404] Error occured, Reason ::  {message}"
        
class FileNotFound(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = f"[404] File not found, {message}"
        
class TaskTokenMissing(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = f"[404] step function task token not found, {message}"

class UserQuestionMissing(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = f"[404] user question or question id is not found, {message}"