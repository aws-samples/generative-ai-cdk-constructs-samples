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
Enable Anthropic Claude models by submitting use case information.

This is a one-time setup required per AWS account before using any Claude models.
The submission is inherited by all accounts in the same AWS Organization if done
at the management account level.
"""

import argparse
import sys

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


def submit_anthropic_use_case(
    company_name: str,
    company_website: str,
    use_cases: str,
    intended_users: str,
    industry: str,
    region: str = None,
    dry_run: bool = False
) -> bool:
    """
    Submit Anthropic use case information to enable Claude models.
    
    Args:
        company_name: Your company name
        company_website: Your company website URL
        use_cases: Description of how you'll use Claude models
        intended_users: "0" (internal only), "1" (external only), "2" (both)
        industry: Your industry sector
        region: AWS region (uses default from AWS config if not specified)
        dry_run: If True, only validate parameters without submitting
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Validate intended_users format
    if intended_users not in ["0", "1", "2"]:
        print(f"Error: intended_users must be '0', '1', or '2', got '{intended_users}'")
        return False
    
    print("\n=== Anthropic Use Case Submission ===")
    print(f"Company Name: {company_name}")
    print(f"Company Website: {company_website}")
    print(f"Industry: {industry}")
    print(f"Intended Users: {intended_users} ({'Internal' if intended_users == '0' else 'External' if intended_users == '1' else 'Both'})")
    print(f"Use Cases: {use_cases[:100]}{'...' if len(use_cases) > 100 else ''}")
    
    if dry_run:
        print("\n[DRY RUN] Would submit use case information (no actual API call)")
        return True
    
    try:
        bedrock = boto3.client("bedrock", region_name=region)
        
        # Submit use case - API only accepts formData as blob
        import json
        import base64
        
        form_data = {
            "companyName": company_name,
            "companyWebsite": company_website,
            "intendedUsers": intended_users,
            "industryOption": industry,
            "useCases": use_cases
        }
        
        # Encode form data as base64 blob
        form_data_json = json.dumps(form_data)
        form_data_blob = base64.b64encode(form_data_json.encode('utf-8'))
        
        print("\nSubmitting use case information...")
        bedrock.put_use_case_for_model_access(
            formData=form_data_blob
        )
        
        print("\n✓ Successfully submitted Anthropic use case!")
        print("  All Claude models are now enabled for this account.")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"\n✗ Error submitting use case: {error_code}")
        print(f"  {error_msg}")
        
        if error_code == "AccessDeniedException":
            print("\n  Required IAM permissions:")
            print("    - bedrock:PutUseCaseForModelAccess")
            print("    - bedrock:GetUseCaseForModelAccess")
        
        return False
    
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Enable Anthropic Claude models by submitting use case information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for input)
  python enable_anthropic_models.py
  
  # With command-line arguments
  python enable_anthropic_models.py \\
    --company-name "AnyCompany" \\
    --company-website "https://example.com" \\
    --use-cases "Contract compliance analysis using AI" \\
    --intended-users "0" \\
    --industry "Technology"
  
  # Dry run to test without submitting
  python enable_anthropic_models.py --dry-run
        """
    )
    
    parser.add_argument(
        "--company-name",
        help="Your company name"
    )
    parser.add_argument(
        "--company-website",
        help="Your company website URL"
    )
    parser.add_argument(
        "--use-cases",
        help="Description of how you'll use Claude models"
    )
    parser.add_argument(
        "--intended-users",
        choices=["0", "1", "2"],
        help="0=Internal only, 1=External only, 2=Both (required)"
    )
    parser.add_argument(
        "--industry",
        help="Your industry sector (required)"
    )
    parser.add_argument(
        "--region",
        help="AWS region (uses default from AWS config if not specified)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate parameters without submitting"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Resubmit even if use case was already submitted"
    )
    
    args = parser.parse_args()
    
    # Check if already submitted (before asking for EULA/form)
    if not args.dry_run and not args.force:
        try:
            bedrock = boto3.client("bedrock", region_name=args.region)
            bedrock.get_use_case_for_model_access()
            print("✓ Anthropic use case already submitted for this account")            
            sys.exit(0)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                print(f"✗ Error checking existing submission: {e.response['Error']['Message']}")
                sys.exit(1)
            # Not submitted yet, continue
        except Exception as e:
            print(f"✗ Error connecting to AWS: {str(e)}")
            sys.exit(1)
    
    # EULA agreement first (skip for dry-run)
    if not args.dry_run:
        print("="*70)
        print("⚠️  IMPORTANT: By using Claude models, you agree to:")
        print("   - AWS Service Terms: https://aws.amazon.com/service-terms/")
        print("   - Anthropic EULA: https://aws.amazon.com/legal/bedrock/third-party-models/")
        print("="*70)
        
        while True:
            agreement = input("\nDo you agree to these terms? (yes/no): ").strip().lower()
            if agreement in ["yes", "y"]:
                print()
                break
            elif agreement in ["no", "n"]:
                print("\n✗ You must agree to the terms to use Claude models.")
                sys.exit(1)
            else:
                print("Please enter 'yes' or 'no'")
    
    # Interactive mode if required fields not provided
    company_name = args.company_name
    company_website = args.company_website
    use_cases = args.use_cases
    intended_users = args.intended_users
    industry = args.industry
    
    if not company_name:
        company_name = input("Company Name: ").strip()
        if not company_name:
            print("Error: Company name is required")
            sys.exit(1)
    
    if not company_website:
        company_website = input("Company Website: ").strip()
        if not company_website:
            print("Error: Company website is required")
            sys.exit(1)
    
    if not use_cases:
        print("Use Cases (describe how you'll use Claude models):")
        use_cases = input("> ").strip()
        if not use_cases:
            print("Error: Use cases description is required")
            sys.exit(1)
    
    if not intended_users:
        while True:
            print("Intended Users:")
            print("  0 = Internal use only")
            print("  1 = External use only")
            print("  2 = Both internal and external use")
            intended_users = input("Enter choice (0/1/2): ").strip()
            if intended_users in ["0", "1", "2"]:
                break
            print("Error: Please enter 0, 1, or 2\n")
    
    if not industry:
        industry = input("Industry: ").strip()
        if not industry:
            print("Error: Industry is required")
            sys.exit(1)
    
    success = submit_anthropic_use_case(
        company_name=company_name,
        company_website=company_website,
        use_cases=use_cases,
        intended_users=intended_users,
        industry=industry,
        region=args.region,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
