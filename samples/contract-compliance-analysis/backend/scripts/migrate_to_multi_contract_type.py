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
Migration script to transform single contract type system to multi-contract type support.

This script migrates data from an old stack (single contract type) to a new stack (multi-contract type)
by:
1. Creating a contract type from existing Parameter Store configuration
2. Migrating guidelines with new schema (contract_type_id + clause_type_id)
3. Migrating jobs with contract_type_id field
4. Validating data integrity after migration
"""

import argparse
import boto3
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key


class MultiContractTypeMigrator:
    """Migrates data from single contract type system to multi-contract type support"""

    def __init__(self, old_stack_name: str, new_stack_name: str, region: Optional[str] = None):
        """
        Initialize migrator with old and new stack names

        Args:
            old_stack_name: CloudFormation stack name for the old system
            new_stack_name: CloudFormation stack name for the new system
            region: AWS region (optional, uses default if not provided)
        """
        self.old_stack_name = old_stack_name
        self.new_stack_name = new_stack_name
        self.region = region

        # Initialize AWS clients
        self.cf_client = boto3.client('cloudformation', region_name=region)
        self.ssm_client = boto3.client('ssm', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)

        # Get stack resources
        self.old_stack_resources = self._get_stack_resources(old_stack_name)
        self.new_stack_resources = self._get_stack_resources(new_stack_name)

        # Cache for contract type data
        self._contract_type_data = None

    def _get_stack_resources(self, stack_name: str) -> Dict[str, str]:
        """Get CloudFormation stack outputs as a dictionary"""
        try:
            response = self.cf_client.describe_stacks(StackName=stack_name)
            outputs = response["Stacks"][0]["Outputs"]

            resources = {}
            for output in outputs:
                resources[output["OutputKey"]] = output["OutputValue"]

            return resources

        except ClientError as e:
            raise RuntimeError(f"Failed to get stack resources for {stack_name}: {e}")

    def _slugify_contract_type(self, contract_type: str) -> str:
        """Convert contract type name to slugified ID format"""
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', contract_type.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    def _get_parameter_value(self, parameter_name: str, stack_resources: Dict[str, str]) -> Optional[str]:
        """Get parameter value from Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(Name=parameter_name)
            return response['Parameter']['Value']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                return None
            raise RuntimeError(f"Failed to get parameter {parameter_name}: {e}")

    def _create_contract_type_from_existing_config(self) -> Dict[str, Any]:
        """
        Create contract type from existing Parameter Store configuration

        Returns:
            Dict containing the created contract type data
        """
        print("Creating contract type from existing configuration...")

        # Get contract type name from Parameter Store
        contract_type_param = self._get_parameter_value('/ContractAnalysis/ContractType', self.old_stack_resources)
        if not contract_type_param:
            raise ValueError("ContractType parameter not found in old stack Parameter Store")

        # Generate contract type ID
        contract_type_id = self._slugify_contract_type(contract_type_param)

        # Get other parameters with defaults
        company_party_type = self._get_parameter_value('/ContractAnalysis/CompanyPartyType', self.old_stack_resources) or "Customer"
        other_party_type = self._get_parameter_value('/ContractAnalysis/OtherPartyType', self.old_stack_resources) or "Service Provider"
        high_risk_threshold = self._get_parameter_value('/ContractAnalysis/HighRiskThreshold', self.old_stack_resources) or "0"
        medium_risk_threshold = self._get_parameter_value('/ContractAnalysis/MediumRiskThreshold', self.old_stack_resources) or "1"
        low_risk_threshold = self._get_parameter_value('/ContractAnalysis/LowRiskThreshold', self.old_stack_resources) or "3"
        default_language = self._get_parameter_value('/ContractAnalysis/Language', self.old_stack_resources) or "en"

        # Create contract type record
        now = datetime.now().isoformat()
        contract_type_data = {
            'contract_type_id': contract_type_id,
            'name': contract_type_param,
            'description': contract_type_param,  # Use name as description for migration
            'company_party_type': company_party_type,
            'other_party_type': other_party_type,
            'high_risk_threshold': Decimal(high_risk_threshold),
            'medium_risk_threshold': Decimal(medium_risk_threshold),
            'low_risk_threshold': Decimal(low_risk_threshold),
            'is_active': True,
            'default_language': default_language,
            'created_at': now,
            'updated_at': now
        }

        # Get new stack's ContractTypes table
        contract_types_table_name = self.new_stack_resources.get('ContractTypesTableName')
        if not contract_types_table_name:
            raise ValueError("ContractTypesTableName not found in new stack outputs")

        contract_types_table = self.dynamodb.Table(contract_types_table_name)

        # Check if contract type already exists
        try:
            response = contract_types_table.get_item(Key={'contract_type_id': contract_type_id})
            if 'Item' in response:
                print(f"Contract type '{contract_type_id}' already exists, skipping creation")
                self._contract_type_data = response['Item']
                return dict(self._contract_type_data)
        except ClientError as e:
            raise RuntimeError(f"Failed to check existing contract type: {e}")

        # Create contract type
        try:
            contract_types_table.put_item(Item=contract_type_data)
            print(f"Created contract type: {contract_type_id} ({contract_type_param})")
            self._contract_type_data = contract_type_data
            return contract_type_data

        except ClientError as e:
            raise RuntimeError(f"Failed to create contract type: {e}")

    def _migrate_guidelines(self) -> int:
        """
        Migrate guidelines from old schema to new schema with contract type support

        Returns:
            Number of guidelines migrated
        """
        print("Migrating guidelines data...")

        if not self._contract_type_data:
            raise RuntimeError("Contract type must be created before migrating guidelines")

        contract_type_id = self._contract_type_data['contract_type_id']

        # Get old and new guidelines tables
        old_guidelines_table_name = self.old_stack_resources.get('GuidelinesTableName')
        new_guidelines_table_name = self.new_stack_resources.get('GuidelinesTableName')

        if not old_guidelines_table_name:
            raise ValueError("GuidelinesTableName not found in old stack outputs")
        if not new_guidelines_table_name:
            raise ValueError("GuidelinesTableName not found in new stack outputs")

        old_table = self.dynamodb.Table(old_guidelines_table_name)
        new_table = self.dynamodb.Table(new_guidelines_table_name)

        # Read all guidelines from old table
        try:
            response = old_table.scan()
            old_guidelines = response.get('Items', [])

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = old_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                old_guidelines.extend(response.get('Items', []))

        except ClientError as e:
            raise RuntimeError(f"Failed to read guidelines from old table: {e}")

        if not old_guidelines:
            print("No guidelines found in old table")
            return 0

        # Transform guidelines data
        migrated_count = 0

        # Clear existing guidelines for this contract type in new table
        try:
            existing_response = new_table.query(
                KeyConditionExpression=Key('contract_type_id').eq(contract_type_id),
                ProjectionExpression='contract_type_id, clause_type_id'
            )
            existing_items = existing_response.get('Items', [])

            if existing_items:
                print(f"Removing {len(existing_items)} existing guidelines for contract type '{contract_type_id}'")
                with new_table.batch_writer() as batch:
                    for item in existing_items:
                        batch.delete_item(Key={
                            'contract_type_id': item['contract_type_id'],
                            'clause_type_id': item['clause_type_id']
                        })
        except ClientError as e:
            raise RuntimeError(f"Failed to clear existing guidelines: {e}")

        # Migrate guidelines with new schema
        try:
            with new_table.batch_writer() as batch:
                for guideline in old_guidelines:
                    # Transform the guideline data
                    new_guideline = {
                        'contract_type_id': contract_type_id,
                        'clause_type_id': guideline.get('type_id'),  # Rename from type_id to clause_type_id
                        'name': guideline.get('name'),
                        'standard_wording': guideline.get('standard_wording'),
                        'level': guideline.get('level'),
                        'evaluation_questions': guideline.get('evaluation_questions'),
                        'examples': guideline.get('examples')
                    }

                    # Remove None values
                    new_guideline = {k: v for k, v in new_guideline.items() if v is not None}

                    if not new_guideline.get('clause_type_id'):
                        print(f"Skipping guideline with missing clause_type_id: {guideline}")
                        continue

                    batch.put_item(Item=new_guideline)
                    migrated_count += 1

        except ClientError as e:
            raise RuntimeError(f"Failed to write guidelines to new table: {e}")

        print(f"Migrated {migrated_count} guidelines for contract type '{contract_type_id}'")
        return migrated_count

    def _migrate_jobs(self) -> int:
        """
        Migrate jobs from old schema to new schema with contract_type_id field

        Returns:
            Number of jobs migrated
        """
        print("Migrating jobs data...")

        if not self._contract_type_data:
            raise RuntimeError("Contract type must be created before migrating jobs")

        contract_type_id = self._contract_type_data['contract_type_id']

        # Get old and new jobs tables
        old_jobs_table_name = self.old_stack_resources.get('JobsTableName')
        new_jobs_table_name = self.new_stack_resources.get('JobsTableName')

        if not old_jobs_table_name:
            raise ValueError("JobsTableName not found in old stack outputs")
        if not new_jobs_table_name:
            raise ValueError("JobsTableName not found in new stack outputs")

        old_table = self.dynamodb.Table(old_jobs_table_name)
        new_table = self.dynamodb.Table(new_jobs_table_name)

        # Read all jobs from old table
        try:
            response = old_table.scan()
            old_jobs = response.get('Items', [])

            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = old_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                old_jobs.extend(response.get('Items', []))

        except ClientError as e:
            raise RuntimeError(f"Failed to read jobs from old table: {e}")

        if not old_jobs:
            print("No jobs found in old table")
            return 0

        # Migrate jobs with contract_type_id field
        migrated_count = 0

        try:
            with new_table.batch_writer() as batch:
                for job in old_jobs:
                    # Add contract_type_id to existing job data
                    new_job = dict(job)
                    new_job['contract_type_id'] = contract_type_id

                    batch.put_item(Item=new_job)
                    migrated_count += 1

        except ClientError as e:
            raise RuntimeError(f"Failed to write jobs to new table: {e}")

        print(f"Migrated {migrated_count} jobs with contract type '{contract_type_id}'")
        return migrated_count

    def _validate_migration(self) -> bool:
        """
        Validate data integrity after migration

        Returns:
            True if validation passes, raises exception otherwise
        """
        print("Validating migration...")

        if not self._contract_type_data:
            raise RuntimeError("Contract type data not available for validation")

        contract_type_id = self._contract_type_data['contract_type_id']

        # Validate contract type exists
        contract_types_table_name = self.new_stack_resources.get('ContractTypesTableName')
        if contract_types_table_name:
            contract_types_table = self.dynamodb.Table(contract_types_table_name)
            try:
                response = contract_types_table.get_item(Key={'contract_type_id': contract_type_id})
                if 'Item' not in response:
                    raise RuntimeError(f"Contract type '{contract_type_id}' not found after migration")
                print(f"✓ Contract type '{contract_type_id}' exists")
            except ClientError as e:
                raise RuntimeError(f"Failed to validate contract type: {e}")

        # Validate guidelines count
        old_guidelines_table_name = self.old_stack_resources.get('GuidelinesTableName')
        new_guidelines_table_name = self.new_stack_resources.get('GuidelinesTableName')

        if old_guidelines_table_name and new_guidelines_table_name:
            old_table = self.dynamodb.Table(old_guidelines_table_name)
            new_table = self.dynamodb.Table(new_guidelines_table_name)

            try:
                # Count old guidelines
                old_response = old_table.scan(Select='COUNT')
                old_count = old_response['Count']

                # Count new guidelines for this contract type
                new_response = new_table.query(
                    KeyConditionExpression=Key('contract_type_id').eq(contract_type_id),
                    Select='COUNT'
                )
                new_count = new_response['Count']

                if old_count != new_count:
                    raise RuntimeError(f"Guidelines count mismatch: old={old_count}, new={new_count}")

                print(f"✓ Guidelines count matches: {new_count}")

            except ClientError as e:
                raise RuntimeError(f"Failed to validate guidelines count: {e}")

        # Validate jobs count
        old_jobs_table_name = self.old_stack_resources.get('JobsTableName')
        new_jobs_table_name = self.new_stack_resources.get('JobsTableName')

        if old_jobs_table_name and new_jobs_table_name:
            old_table = self.dynamodb.Table(old_jobs_table_name)
            new_table = self.dynamodb.Table(new_jobs_table_name)

            try:
                # Count old jobs
                old_response = old_table.scan(Select='COUNT')
                old_count = old_response['Count']

                # Count new jobs with this contract type
                new_response = new_table.query(
                    IndexName='contract_type_id-created_at-index',
                    KeyConditionExpression=Key('contract_type_id').eq(contract_type_id),
                    Select='COUNT'
                )
                new_count = new_response['Count']

                if old_count != new_count:
                    raise RuntimeError(f"Jobs count mismatch: old={old_count}, new={new_count}")

                print(f"✓ Jobs count matches: {new_count}")

            except ClientError as e:
                raise RuntimeError(f"Failed to validate jobs count: {e}")

        # Validate sample job has contract_type_id
        if new_jobs_table_name:
            new_table = self.dynamodb.Table(new_jobs_table_name)
            try:
                response = new_table.scan(Limit=1)
                if response.get('Items'):
                    sample_job = response['Items'][0]
                    if 'contract_type_id' not in sample_job:
                        raise RuntimeError("Sample job missing contract_type_id field")
                    if sample_job['contract_type_id'] != contract_type_id:
                        raise RuntimeError(f"Sample job has wrong contract_type_id: {sample_job['contract_type_id']}")
                    print(f"✓ Sample job has correct contract_type_id: {contract_type_id}")
            except ClientError as e:
                raise RuntimeError(f"Failed to validate sample job: {e}")

        print("✅ Migration validation completed successfully")
        return True

    def migrate(self) -> Dict[str, Any]:
        """
        Execute full migration process

        Returns:
            Dictionary with migration results
        """
        print(f"Starting migration from {self.old_stack_name} to {self.new_stack_name}")

        results = {
            'contract_type_created': False,
            'guidelines_migrated': 0,
            'jobs_migrated': 0,
            'validation_passed': False
        }

        try:
            # Step 1: Create contract type from existing config
            contract_type_data = self._create_contract_type_from_existing_config()
            results['contract_type_created'] = True
            results['contract_type_id'] = contract_type_data['contract_type_id']
            results['contract_type_name'] = contract_type_data['name']

            # Step 2: Migrate guidelines
            guidelines_count = self._migrate_guidelines()
            results['guidelines_migrated'] = guidelines_count

            # Step 3: Migrate jobs
            jobs_count = self._migrate_jobs()
            results['jobs_migrated'] = jobs_count

            # Step 4: Validate migration
            self._validate_migration()
            results['validation_passed'] = True

            print(f"✅ Migration completed successfully!")
            print(f"   Contract type: {results['contract_type_id']} ({results['contract_type_name']})")
            print(f"   Guidelines migrated: {results['guidelines_migrated']}")
            print(f"   Jobs migrated: {results['jobs_migrated']}")

            return results

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise


def main():
    """Main entry point for the migration script"""
    parser = argparse.ArgumentParser(
        description="Migrate data from single contract type system to multi-contract type support"
    )
    parser.add_argument(
        "--old-stack",
        type=str,
        required=True,
        help="CloudFormation stack name for the old system"
    )
    parser.add_argument(
        "--new-stack",
        type=str,
        required=True,
        help="CloudFormation stack name for the new system"
    )
    parser.add_argument(
        "--region",
        type=str,
        help="AWS region (optional, uses default if not provided)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually performing the migration"
    )

    args = parser.parse_args()

    try:
        if args.dry_run:
            print("DRY RUN MODE: No actual changes will be made")
            # TODO: Implement dry-run functionality
            print("Dry-run mode not yet implemented")
            return

        # Create migrator and run migration
        migrator = MultiContractTypeMigrator(
            old_stack_name=args.old_stack,
            new_stack_name=args.new_stack,
            region=args.region
        )

        results = migrator.migrate()

        print("\n" + "="*50)
        print("MIGRATION SUMMARY")
        print("="*50)
        print(f"Contract Type ID: {results['contract_type_id']}")
        print(f"Contract Type Name: {results['contract_type_name']}")
        print(f"Guidelines Migrated: {results['guidelines_migrated']}")
        print(f"Jobs Migrated: {results['jobs_migrated']}")
        print(f"Validation: {'PASSED' if results['validation_passed'] else 'FAILED'}")

    except Exception as e:
        print(f"❌ Migration script failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()