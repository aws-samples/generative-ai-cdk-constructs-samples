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

"""
Sync app_properties.yaml to AWS Systems Manager Parameter Store
"""

import yaml
import boto3
import os
import sys
import argparse

def convert_yaml_key_to_parameter_path(key):
    """Convert YAML key to Parameter Store path."""
    if '/' in key:
        # Handle function-specific overrides like "ContractPreprocessing/LanguageModelId"
        function_name, parameter_name = key.split('/', 1)
        return f"/ContractAnalysis/{function_name}/{parameter_name}"
    else:
        # Handle global parameters like "CompanyName"
        return f"/ContractAnalysis/{key}"

def sync_to_parameter_store(yaml_file, preview=False, region=None):
    """Sync YAML config to Parameter Store."""
    if not os.path.exists(yaml_file):
        print(f"ERROR: {yaml_file} not found")
        return False

    with open(yaml_file) as f:
        config = yaml.safe_load(f)

    if not config:
        print(f"ERROR: {yaml_file} is empty or invalid")
        return False

    ssm = boto3.client('ssm', region_name=region) if region else boto3.client('ssm')

    # Get expected parameters from YAML
    expected_params = set()
    for key in config.keys():
        parameter_name = convert_yaml_key_to_parameter_path(key)
        expected_params.add(parameter_name)

    # Get existing parameters from SSM with their values
    try:
        paginator = ssm.get_paginator('get_parameters_by_path')
        existing_params = {}
        for page in paginator.paginate(Path='/ContractAnalysis', Recursive=True):
            for param in page['Parameters']:
                existing_params[param['Name']] = param['Value']
    except Exception as e:
        print(f"ERROR getting existing parameters: {e}")
        return False

    success_count = 0
    delete_count = 0

    # Update/create parameters from YAML
    for key, value in config.items():
        parameter_name = convert_yaml_key_to_parameter_path(key)
        value_str = str(value)
        
        # Check if parameter needs to be updated
        existing_value = existing_params.get(parameter_name)
        needs_update = existing_value != value_str

        if preview:
            if existing_value is None:
                print(f"Would create: {parameter_name} = {value_str}")
                success_count += 1
            elif needs_update:
                print(f"Would update: {parameter_name} = {value_str} (current: {existing_value})")
                success_count += 1
        else:
            if needs_update:
                try:
                    ssm.put_parameter(
                        Name=parameter_name,
                        Value=value_str,
                        Type='String',
                        Overwrite=True
                    )
                    action = "Created" if existing_value is None else "Updated"
                    print(f"{action}: {parameter_name} = {value_str}")
                    success_count += 1
                except Exception as e:
                    print(f"ERROR setting {parameter_name}: {e}")

    # Delete parameters not in YAML
    params_to_delete = set(existing_params.keys()) - expected_params
    for param_name in params_to_delete:
        if preview:
            print(f"Would delete: {param_name}")
            delete_count += 1
        else:
            try:
                ssm.delete_parameter(Name=param_name)
                print(f"Deleted: {param_name}")
                delete_count += 1
            except Exception as e:
                print(f"ERROR deleting {param_name}: {e}")

    if preview:
        if success_count == 0 and delete_count == 0:
            print(f"\nNo changes needed - all parameters are up to date")
        else:
            print(f"\nPreview complete: {success_count} parameters would be changed, {delete_count} would be deleted")
    else:
        print(f"\nSync complete: {success_count} parameters updated, {delete_count} parameters deleted")

    return True

def main():
    """Main entry point."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)  # Parent of scripts/
    default_config = os.path.join(backend_dir, 'app_properties.yaml')

    parser = argparse.ArgumentParser(description='Apply YAML config to Parameter Store')
    parser.add_argument('--preview', action='store_true',
                       help='Show what would be changed (dry-run)')
    parser.add_argument('--file', default=default_config,
                       help=f'YAML file to apply (default: {os.path.basename(default_config)})')
    parser.add_argument('--region',
                       help='AWS region (defaults to AWS profile default region)')

    args = parser.parse_args()

    # Always show current region
    current_region = args.region or boto3.Session().region_name or 'us-east-1'
    print(f"Using region: {current_region}")

    if args.preview:
        print("Preview mode: showing changes without applying them")

    success = sync_to_parameter_store(args.file, preview=args.preview, region=args.region)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
