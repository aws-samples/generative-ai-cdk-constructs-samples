#!/usr/bin/env python3
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

from enum import Enum
import aws_cdk as cdk

class BackendLanguage(str, Enum):
    JAVA = "java"
    PYTHON = "python"

def get_backend_language(app: cdk.App) -> BackendLanguage:
    """Get the backend language from the CDK context."""
    # Get backend language from context
    backend_language = app.node.try_get_context("custom:backendLanguage").lower()

    # Return JAVA as default
    if not backend_language or backend_language == BackendLanguage.JAVA: 
        return BackendLanguage.JAVA

    if backend_language == BackendLanguage.PYTHON:
        return BackendLanguage.PYTHON
    
    # Throw error for invalid input
    raise ValueError(
        f"Invalid backend language: {backend_language}. Valid options are: {', '.join([e.value for e in BackendLanguage])}"
    )
