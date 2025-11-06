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
Setup script for personal configuration overrides.
Creates app_properties.yaml from template for customization.
"""

import shutil
import os
import sys

def init_config():
    """Initialize personal configuration from template."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(script_dir)  # Parent of scripts/

    config = os.path.join(backend_dir, 'app_properties.yaml')
    template_config = os.path.join(backend_dir, 'app_properties.template.yaml')

    if os.path.exists(config):
        print(f"WARNING: {os.path.basename(config)} already exists")
        response = input("Overwrite? (y/N): ").lower().strip()
        if response != 'y':
            print("Cancelled.")
            return False

    if not os.path.exists(template_config):
        print(f"ERROR: Template file {os.path.basename(template_config)} not found")
        return False

    try:
        shutil.copy(template_config, config)
        print(f"Created {os.path.basename(config)} from template")
        print()
        print("Next steps:")
        print(f"1. Edit {os.path.basename(config)} with your preferred settings")
        print("2. Run: python scripts/apply_app_properties.py")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create config: {e}")
        return False

def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python setup_config.py")
        print("Creates app_properties.yaml from template")
        return

    init_config()

if __name__ == "__main__":
    main()
