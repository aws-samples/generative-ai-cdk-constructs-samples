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

import json
import argparse
import boto3
import boto3.dynamodb.conditions
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Optional, Tuple
import sys
from datetime import datetime, timezone
from decimal import Decimal

DEFAULT_BACKEND_STACK_NAME = "MainBackendStack"

REQUIRED_GUIDELINE_FIELDS = [
    'clause_type_id',
    'name',
    'standard_wording',
    'level',
    'evaluation_questions'
]

VALID_LEVELS = ['low', 'medium', 'high']

class GuidelinesImportError(Exception):
    """Custom exception for guidelines import errors"""
    pass

class GuidelineValidator:
    """Validates guideline data structure and content"""

    @staticmethod
    def validate_guideline(guideline: Dict[str, Any], index: int) -> List[str]:
        """Validate a single guideline and return list of errors"""
        errors = []

        # Check required fields
        for field in REQUIRED_GUIDELINE_FIELDS:
            if field not in guideline:
                errors.append(f"Missing required field '{field}'")
            elif not guideline[field]:
                errors.append(f"Field '{field}' cannot be empty")

        # Validate clause_type_id format
        if 'clause_type_id' in guideline:
            clause_id = guideline['clause_type_id']
            if not isinstance(clause_id, str):
                errors.append("clause_type_id must be a string")
            elif not clause_id.replace('-', '').replace('_', '').isalnum():
                errors.append("clause_type_id must contain only alphanumeric characters, hyphens, and underscores")
            elif len(clause_id) > 50:
                errors.append("clause_type_id must be 50 characters or less")

        # Validate name
        if 'name' in guideline:
            name = guideline['name']
            if not isinstance(name, str):
                errors.append("name must be a string")
            elif len(name) > 200:
                errors.append("name must be 200 characters or less")

        # Validate standard_wording
        if 'standard_wording' in guideline:
            wording = guideline['standard_wording']
            if not isinstance(wording, str):
                errors.append("standard_wording must be a string")
            elif len(wording) > 5000:
                errors.append("standard_wording must be 5000 characters or less")

        # Validate level
        if 'level' in guideline:
            level = guideline['level']
            if not isinstance(level, str):
                errors.append("level must be a string")
            elif level not in VALID_LEVELS:
                errors.append(f"level must be one of: {', '.join(VALID_LEVELS)}")

        # Validate evaluation_questions
        if 'evaluation_questions' in guideline:
            questions = guideline['evaluation_questions']
            if not isinstance(questions, list):
                errors.append("evaluation_questions must be a list")
            elif len(questions) == 0:
                errors.append("evaluation_questions must contain at least one question")
            elif len(questions) > 10:
                errors.append("evaluation_questions must contain no more than 10 questions")
            else:
                for i, question in enumerate(questions):
                    if not isinstance(question, str):
                        errors.append(f"evaluation_questions[{i}] must be a string")
                    elif len(question.strip()) == 0:
                        errors.append(f"evaluation_questions[{i}] cannot be empty")
                    elif len(question) > 500:
                        errors.append(f"evaluation_questions[{i}] must be 500 characters or less")

        # Validate examples (optional field)
        if 'examples' in guideline:
            examples = guideline['examples']
            if not isinstance(examples, list):
                errors.append("examples must be a list")
            elif len(examples) > 20:
                errors.append("examples must contain no more than 20 items")
            else:
                for i, example in enumerate(examples):
                    if not isinstance(example, str):
                        errors.append(f"examples[{i}] must be a string")
                    elif len(example) > 1000:
                        errors.append(f"examples[{i}] must be 1000 characters or less")

        return errors

class GuidelinesJSONImporter:
    """Handles importing guidelines from JSON files"""

    def __init__(self, region: Optional[str] = None):
        self.region = region
        if region:
            boto3.setup_default_session(region_name=region)

        self.dynamodb = boto3.resource('dynamodb', region_name=region) if region else boto3.resource('dynamodb')
        self.cf_client = boto3.client('cloudformation', region_name=region) if region else boto3.client('cloudformation')

    def get_table_names(self, backend_stack_name: str) -> Tuple[str, str]:
        """Get both guidelines and contract types table names from CloudFormation stack"""
        try:
            response = self.cf_client.describe_stacks(StackName=backend_stack_name)
            outputs = response["Stacks"][0]["Outputs"]

            guidelines_table_name = None
            contract_types_table_name = None

            for output in outputs:
                key_name = output["OutputKey"]
                if key_name == "GuidelinesTableName":
                    guidelines_table_name = output["OutputValue"]
                elif key_name == "ContractTypesTableName":
                    contract_types_table_name = output["OutputValue"]

            if not guidelines_table_name:
                raise GuidelinesImportError("GuidelinesTableName not found in CloudFormation stack outputs")
            if not contract_types_table_name:
                raise GuidelinesImportError("ContractTypesTableName not found in CloudFormation stack outputs")

            return guidelines_table_name, contract_types_table_name

        except ClientError as e:
            raise GuidelinesImportError(f"Failed to get table names from CloudFormation: {e}")

    def create_or_update_contract_type(self, contract_type_id: str, contract_type_data: Dict[str, Any],
                                      contract_types_table_name: str) -> Dict[str, Any]:
        """Create or update contract type in the ContractTypesTable"""
        # Validate contract_type_id format
        if not isinstance(contract_type_id, str):
            raise GuidelinesImportError(f"contract_type_id must be a string, got {type(contract_type_id)}")
        if not contract_type_id:
            raise GuidelinesImportError("contract_type_id cannot be empty")
        if not contract_type_id.replace('-', '').isalnum():
            raise GuidelinesImportError(f"contract_type_id '{contract_type_id}' must contain only alphanumeric characters and hyphens")
        if len(contract_type_id) > 50:
            raise GuidelinesImportError(f"contract_type_id '{contract_type_id}' must be 50 characters or less")
        
        try:
            contract_types_table = self.dynamodb.Table(contract_types_table_name)
            current_time = datetime.now(timezone.utc).isoformat()

            # Check if contract type already exists
            response = contract_types_table.get_item(Key={'contract_type_id': contract_type_id})

            contract_type_record = {
                'contract_type_id': contract_type_id,
                'name': contract_type_data.get('name', contract_type_id.replace('-', ' ').title()),
                'description': contract_type_data.get('description', f'Contract type for {contract_type_id}'),
                'company_party_type': contract_type_data.get('company_party_type', 'Company'),
                'other_party_type': contract_type_data.get('other_party_type', 'Service Provider'),
                'high_risk_threshold': Decimal(str(contract_type_data.get('high_risk_threshold', 0.7))),
                'medium_risk_threshold': Decimal(str(contract_type_data.get('medium_risk_threshold', 0.4))),
                'low_risk_threshold': Decimal(str(contract_type_data.get('low_risk_threshold', 0.1))),
                'default_language': contract_type_data.get('default_language', 'en'),
                'is_active': contract_type_data.get('is_active', True),
                'updated_at': current_time
            }

            if 'Item' not in response:
                # Create new contract type
                contract_type_record['created_at'] = current_time
                contract_types_table.put_item(Item=contract_type_record)
                print(f"✓ Created new contract type '{contract_type_id}'")
            else:
                # Update existing contract type
                existing_item = response['Item']
                contract_type_record['created_at'] = existing_item.get('created_at', current_time)
                contract_types_table.put_item(Item=contract_type_record)
                print(f"✓ Updated existing contract type '{contract_type_id}'")

            return contract_type_record

        except ClientError as e:
            raise GuidelinesImportError(f"Failed to create/update contract type: {e}")

    def load_json_file(self, json_file_path: str) -> Dict[str, Any]:
        """Load and parse JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✓ Successfully loaded JSON file: {json_file_path}")
            return data
        except FileNotFoundError:
            raise GuidelinesImportError(f"JSON file not found: {json_file_path}")
        except json.JSONDecodeError as e:
            raise GuidelinesImportError(f"Invalid JSON format in file {json_file_path}: {e}")
        except Exception as e:
            raise GuidelinesImportError(f"Error reading JSON file {json_file_path}: {e}")

    def extract_contract_types_from_json(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract all contract types from JSON data"""
        # Only support multi-contract type format with contract_types object
        if isinstance(data, dict) and 'contract_types' in data:
            contract_types = data['contract_types']
            if not isinstance(contract_types, dict):
                raise GuidelinesImportError("contract_types must be an object/dictionary")

            print(f"✓ Found {len(contract_types)} contract types in JSON file")
            return contract_types
        else:
            raise GuidelinesImportError(
                "Invalid JSON format. Expected multi-contract type format:\n"
                "{'contract_types': {'contract-id': {'name': '...', 'description': '...', 'guidelines': [...]}}}"
            )

    def extract_guidelines_from_contract_type(self, contract_type_data: Dict[str, Any], contract_type_id: str) -> List[Dict[str, Any]]:
        """Extract guidelines from a single contract type"""
        guidelines = contract_type_data.get('guidelines', [])

        if not isinstance(guidelines, list):
            raise GuidelinesImportError(f"Guidelines for contract type '{contract_type_id}' must be an array/list")

        return guidelines

    def validate_guidelines(self, guidelines: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate all guidelines and return valid ones plus error list"""
        valid_guidelines = []
        all_errors = []
        clause_type_ids = set()

        for i, guideline in enumerate(guidelines):
            errors = GuidelineValidator.validate_guideline(guideline, i)

            if errors:
                error_msg = f"Guideline {i+1} ({guideline.get('clause_type_id', 'unknown')}): " + "; ".join(errors)
                all_errors.append(error_msg)
            else:
                # Check for duplicate clause_type_ids
                clause_id = guideline['clause_type_id']
                if clause_id in clause_type_ids:
                    all_errors.append(f"Guideline {i+1}: Duplicate clause_type_id '{clause_id}'")
                else:
                    clause_type_ids.add(clause_id)
                    valid_guidelines.append(guideline)

        return valid_guidelines, all_errors

    def clear_existing_guidelines(self, contract_type_id: str, guidelines_table_name: str) -> int:
        """Clear existing guidelines for the contract type"""
        try:
            guidelines_table = self.dynamodb.Table(guidelines_table_name)

            # Query all items for this contract type
            response = guidelines_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('contract_type_id').eq(contract_type_id),
                ProjectionExpression='contract_type_id, clause_type_id'
            )

            existing_items = response.get('Items', [])

            if existing_items:
                print(f"✓ Found {len(existing_items)} existing guidelines to remove")
                # Delete items in batches
                with guidelines_table.batch_writer() as batch:
                    for item in existing_items:
                        batch.delete_item(Key={
                            'contract_type_id': item['contract_type_id'],
                            'clause_type_id': item['clause_type_id']
                        })
                print(f"✓ Removed {len(existing_items)} existing guidelines")
            else:
                print("✓ No existing guidelines found for this contract type")

            return len(existing_items)

        except ClientError as e:
            raise GuidelinesImportError(f"Failed to clear existing guidelines: {e}")

    def import_guidelines(self, guidelines: List[Dict[str, Any]], contract_type_id: str,
                         guidelines_table_name: str) -> Tuple[int, int]:
        """Import guidelines to DynamoDB"""
        try:
            guidelines_table = self.dynamodb.Table(guidelines_table_name)
            imported_count = 0
            error_count = 0

            # Add timestamps and contract_type_id to each guideline
            current_time = datetime.now(timezone.utc).isoformat()

            with guidelines_table.batch_writer() as batch:
                for guideline in guidelines:
                    try:
                        # Prepare guideline data
                        guideline_data = {
                            'contract_type_id': contract_type_id,
                            'clause_type_id': guideline['clause_type_id'],
                            'name': guideline['name'],
                            'standard_wording': guideline['standard_wording'],
                            'level': guideline['level'],
                            'evaluation_questions': guideline['evaluation_questions'],
                            'examples': guideline.get('examples', []),
                            'created_at': current_time,
                            'updated_at': current_time
                        }

                        batch.put_item(Item=guideline_data)
                        imported_count += 1

                    except Exception as e:
                        print(f"✗ Error importing guideline '{guideline.get('clause_type_id', 'unknown')}': {e}")
                        error_count += 1

            return imported_count, error_count

        except ClientError as e:
            raise GuidelinesImportError(f"Failed to import guidelines to DynamoDB: {e}")

    def import_from_json(self, json_file_path: str, backend_stack_name: str, clear_existing: bool = True) -> Dict[str, Any]:
        """Main import method - processes all contract types in the JSON file"""
        print(f"🚀 Starting guidelines import from JSON file...")
        print(f"   File: {json_file_path}")
        print(f"   Backend Stack: {backend_stack_name}")
        print(f"   Clear Existing: {clear_existing}")
        print()

        results = {
            'contract_types_processed': 0,
            'contract_types_created': 0,
            'contract_types_updated': 0,
            'total_imported': 0,
            'total_skipped': 0,
            'total_errors': 0,
            'total_cleared': 0,
            'contract_type_results': {}
        }

        try:
            # Get table names
            guidelines_table_name, contract_types_table_name = self.get_table_names(backend_stack_name)
            print(f"✓ Guidelines table: {guidelines_table_name}")
            print(f"✓ Contract types table: {contract_types_table_name}")

            # Load JSON file
            data = self.load_json_file(json_file_path)

            # Extract all contract types from JSON
            contract_types = self.extract_contract_types_from_json(data)

            if not contract_types:
                print("⚠️  No contract types found in JSON file")
                return results

            # Process each contract type
            for contract_type_id, contract_type_data in contract_types.items():
                print(f"\n📋 Processing contract type: {contract_type_id}")

                contract_result = {
                    'imported': 0,
                    'skipped': 0,
                    'errors': 0,
                    'validation_errors': [],
                    'cleared_existing': 0
                }

                try:
                    # Create or update contract type record
                    contract_type_record = self.create_or_update_contract_type(
                        contract_type_id, contract_type_data, contract_types_table_name
                    )

                    if 'created_at' in contract_type_record and contract_type_record['created_at'] == contract_type_record['updated_at']:
                        results['contract_types_created'] += 1
                    else:
                        results['contract_types_updated'] += 1

                    # Extract guidelines for this contract type
                    guidelines = self.extract_guidelines_from_contract_type(contract_type_data, contract_type_id)

                    if not guidelines:
                        print(f"⚠️  No guidelines found for contract type '{contract_type_id}'")
                        contract_result['skipped'] = 0
                    else:
                        print(f"✓ Found {len(guidelines)} guidelines for '{contract_type_id}'")

                        # Validate guidelines
                        valid_guidelines, validation_errors = self.validate_guidelines(guidelines)
                        contract_result['validation_errors'] = validation_errors
                        contract_result['skipped'] = len(guidelines) - len(valid_guidelines)

                        if validation_errors:
                            print(f"⚠️  Found {len(validation_errors)} validation errors for '{contract_type_id}':")
                            for error in validation_errors:
                                print(f"   ✗ {error}")

                        if valid_guidelines:
                            print(f"✓ {len(valid_guidelines)} guidelines passed validation for '{contract_type_id}'")

                            # Clear existing guidelines if requested
                            if clear_existing:
                                contract_result['cleared_existing'] = self.clear_existing_guidelines(
                                    contract_type_id, guidelines_table_name
                                )

                            # Import guidelines
                            imported_count, error_count = self.import_guidelines(
                                valid_guidelines, contract_type_id, guidelines_table_name
                            )
                            contract_result['imported'] = imported_count
                            contract_result['errors'] = error_count
                        else:
                            print(f"❌ No valid guidelines to import for '{contract_type_id}' after validation")
                            contract_result['errors'] = len(guidelines)

                    results['contract_type_results'][contract_type_id] = contract_result
                    results['contract_types_processed'] += 1

                    # Update totals
                    results['total_imported'] += contract_result['imported']
                    results['total_skipped'] += contract_result['skipped']
                    results['total_errors'] += contract_result['errors']
                    results['total_cleared'] += contract_result['cleared_existing']

                    print(f"✓ Completed processing '{contract_type_id}': {contract_result['imported']} imported, {contract_result['skipped']} skipped, {contract_result['errors']} errors")

                except Exception as e:
                    print(f"❌ Error processing contract type '{contract_type_id}': {e}")
                    contract_result['errors'] = 1
                    results['contract_type_results'][contract_type_id] = contract_result
                    results['total_errors'] += 1

            # Print final summary
            print()
            print("📊 Final Import Summary:")
            print(f"   📋 Contract types processed: {results['contract_types_processed']}")
            print(f"   ➕ Contract types created: {results['contract_types_created']}")
            print(f"   🔄 Contract types updated: {results['contract_types_updated']}")
            print(f"   ✅ Total guidelines imported: {results['total_imported']}")
            if results['total_cleared'] > 0:
                print(f"   🗑️  Total guidelines cleared: {results['total_cleared']}")
            if results['total_skipped'] > 0:
                print(f"   ⚠️  Total skipped (validation errors): {results['total_skipped']}")
            if results['total_errors'] > 0:
                print(f"   ❌ Total errors: {results['total_errors']}")

            return results

        except GuidelinesImportError as e:
            print(f"❌ Import failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error during import: {e}")
            raise GuidelinesImportError(f"Unexpected error: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Import contract types and guidelines from JSON file into DynamoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all contract types and guidelines from JSON file
  python load_guidelines.py --json-file guidelines.json

  # Import with custom stack name and region
  python load_guidelines.py --json-file guidelines.json \\
    --backend-stack-name MyCustomStack --region us-west-2

  # Import without clearing existing guidelines
  python load_guidelines.py --json-file guidelines.json --no-clear-existing

  # Dry run to validate without importing
  python load_guidelines.py --json-file guidelines.json --dry-run

Supported JSON format:
  Multi-contract type: {"contract_types": {"contract-id": {"name": "...", "description": "...", "guidelines": [...]}}}
        """
    )

    parser.add_argument(
        "--json-file",
        type=str,
        required=True,
        help="Path to JSON file containing contract types and guidelines"
    )

    parser.add_argument(
        "--backend-stack-name",
        type=str,
        default=DEFAULT_BACKEND_STACK_NAME,
        help=f"CloudFormation Backend Stack Name (default: {DEFAULT_BACKEND_STACK_NAME})"
    )

    parser.add_argument(
        "--region",
        type=str,
        help="AWS region (uses default region if not specified)"
    )

    parser.add_argument(
        "--no-clear-existing",
        action="store_true",
        help="Do not clear existing guidelines before import (default: clear existing)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate JSON and show what would be imported without actually importing"
    )

    args = parser.parse_args()

    try:
        importer = GuidelinesJSONImporter(region=args.region)

        if args.dry_run:
            print("🔍 DRY RUN MODE - No data will be imported")
            print()

            # Load and validate only
            data = importer.load_json_file(args.json_file)
            contract_types = importer.extract_contract_types_from_json(data)

            total_guidelines = 0
            total_valid = 0
            total_errors = 0

            print(f"📊 Dry Run Results:")
            print(f"   Contract types found: {len(contract_types)}")
            print()

            for contract_type_id, contract_type_data in contract_types.items():
                print(f"📋 Contract Type: {contract_type_id}")
                print(f"   Name: {contract_type_data.get('name', 'N/A')}")
                print(f"   Description: {contract_type_data.get('description', 'N/A')}")

                guidelines = importer.extract_guidelines_from_contract_type(contract_type_data, contract_type_id)
                if guidelines:
                    valid_guidelines, validation_errors = importer.validate_guidelines(guidelines)

                    total_guidelines += len(guidelines)
                    total_valid += len(valid_guidelines)
                    total_errors += len(validation_errors)

                    print(f"   Guidelines: {len(guidelines)} total, {len(valid_guidelines)} valid, {len(validation_errors)} errors")

                    if validation_errors:
                        print(f"   ⚠️  Validation Errors:")
                        for error in validation_errors[:3]:  # Show first 3 errors
                            print(f"      ✗ {error}")
                        if len(validation_errors) > 3:
                            print(f"      ... and {len(validation_errors) - 3} more errors")

                    if valid_guidelines:
                        print(f"   ✅ Would import guidelines:")
                        for guideline in valid_guidelines[:5]:  # Show first 5 guidelines
                            print(f"      • {guideline['clause_type_id']}: {guideline['name']}")
                        if len(valid_guidelines) > 5:
                            print(f"      ... and {len(valid_guidelines) - 5} more guidelines")
                else:
                    print(f"   Guidelines: 0")
                print()

            print(f"📊 Summary:")
            print(f"   Total contract types: {len(contract_types)}")
            print(f"   Total guidelines: {total_guidelines}")
            print(f"   Valid guidelines: {total_valid}")
            print(f"   Validation errors: {total_errors}")

        else:
            results = importer.import_from_json(
                json_file_path=args.json_file,
                backend_stack_name=args.backend_stack_name,
                clear_existing=not args.no_clear_existing
            )

            # Exit with error code if there were issues
            if results['total_errors'] > 0 or results['total_skipped'] > 0:
                print(f"\n⚠️  Import completed with issues")
                sys.exit(1)
            else:
                print(f"\n✅ Import completed successfully!")
                sys.exit(0)

    except GuidelinesImportError as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️  Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()