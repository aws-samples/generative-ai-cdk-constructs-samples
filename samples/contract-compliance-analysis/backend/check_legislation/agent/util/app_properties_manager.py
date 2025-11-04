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

# NOTE: Simplified version for agent (no Lambda Powertools dependency)
# Based on stack/lambda/common_layer/app_properties_manager.py

"""
Application Properties Manager for agent using boto3 SSM client.
Provides hierarchical parameter lookup with task-specific overrides.
"""

import os
import boto3
from typing import Optional


class AppPropertiesManager:
    """Manages application properties from AWS Systems Manager Parameter Store."""
    
    def __init__(self, region: Optional[str] = None):
        """Initialize with optional region override."""
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.ssm = boto3.client('ssm', region_name=self.region)
        self.base_path = "/ContractAnalysis"
    
    def get_parameter(self, parameter_name: str, task_name: Optional[str] = None, default: Optional[str] = None) -> str:
        """
        Get parameter with hierarchical lookup.
        
        Args:
            parameter_name: Name of the parameter (e.g., 'LanguageModelId')
            task_name: Optional task name for task-specific override (e.g., 'LegislationCheck')
            default: Default value if parameter not found
            
        Returns:
            Parameter value or default
        """
        print(f"Getting parameter: {parameter_name}, task_name: {task_name}")
        
        # Try task-specific parameter first
        if task_name:
            task_path = f"{self.base_path}/{task_name}/{parameter_name}"
            print(f"Trying task-specific parameter: {task_path}")
            try:
                response = self.ssm.get_parameter(Name=task_path)
                value = response['Parameter']['Value']
                print(f"Found task-specific parameter: {task_path}")
                return value
            except self.ssm.exceptions.ParameterNotFound:
                print(f"Task-specific parameter not found: {task_path}")
        
        # Try global parameter
        global_path = f"{self.base_path}/{parameter_name}"
        print(f"Trying global parameter: {global_path}")
        try:
            response = self.ssm.get_parameter(Name=global_path)
            value = response['Parameter']['Value']
            print(f"Found global parameter: {global_path}")
            return value
        except self.ssm.exceptions.ParameterNotFound:
            if default is not None:
                print(f"Using default for parameter: {parameter_name}")
                return default
            print(f"ERROR: Parameter not found: {parameter_name}")
            raise ValueError(f"Parameter {parameter_name} not found and no default provided")
