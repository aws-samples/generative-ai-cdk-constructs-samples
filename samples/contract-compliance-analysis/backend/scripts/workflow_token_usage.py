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
Query token usage from CloudWatch Log Insights for contract compliance analysis.

This script queries token usage across all Lambda functions (preprocessing, classification, evaluation)
and aggregates the results by correlation_id (job_id).
"""

import argparse
import boto3
import time
from datetime import datetime
from typing import Dict, List, Any

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


def get_log_groups_from_stack_outputs(cf_client, stack_name: str) -> List[str]:
    """Get log group names from CloudFormation stack outputs."""
    print(f"Looking up log groups from CloudFormation stack outputs: {stack_name}")

    # Expected output keys for log groups
    expected_outputs = [
        'PreprocessingLogGroup',
        'ClassificationLogGroup',
        'EvaluationLogGroup'
    ]

    log_groups = []

    try:
        # Get stack outputs
        response = cf_client.describe_stacks(StackName=stack_name)

        if not response['Stacks']:
            print(f"Stack {stack_name} not found")
            return []

        stack = response['Stacks'][0]
        outputs = stack.get('Outputs', [])

        # Create a map of output key to value
        output_map = {output['OutputKey']: output['OutputValue'] for output in outputs}

        # Look for our expected log group outputs
        for output_key in expected_outputs:
            if output_key in output_map:
                log_group = output_map[output_key]
                log_groups.append(log_group)
                function_type = output_key.replace('LogGroup', '')
                print(f"  Found {function_type}: {log_group}")
            else:
                print(f"  Output {output_key} not found in stack")

        if len(log_groups) == 0:
            print("No log group outputs found in stack. Available outputs:")

        return log_groups

    except Exception as e:
        print(f"Error getting stack outputs: {e}")
        return []


def build_query(correlation_id: str = None) -> str:
    """Build the CloudWatch Log Insights query."""
    base_query = """
    fields @timestamp, correlation_id, token_usage.model_id, token_usage.input_tokens, token_usage.output_tokens
    | filter ispresent(token_usage.input_tokens)
     and service = "contract-compliance-analysis"
    """

    if correlation_id:
        base_query += f' and correlation_id = "{correlation_id}"'

    base_query += """
    | stats
        sum(token_usage.input_tokens) as total_input_tokens,
        sum(token_usage.output_tokens) as total_output_tokens,
        sum(token_usage.cache_read_tokens) as total_cache_read_tokens,
        sum(token_usage.cache_write_tokens) as total_cache_write_tokens,
        count() as llm_calls
        by correlation_id, token_usage.model_id
    """

    return base_query.strip()


def run_query(logs_client, query: str, log_groups: List[str], start_time: int, end_time: int) -> Dict[str, Any]:
    """Run the CloudWatch Log Insights query and return results."""
    print(f"Starting query across {len(log_groups)} log groups...")
    print(f"Time range: {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(end_time)}")

    # Start the query
    response = logs_client.start_query(
        logGroupNames=log_groups,
        startTime=start_time,
        endTime=end_time,
        queryString=query
    )

    query_id = response['queryId']
    print(f"Query ID: {query_id}")

    # Poll for results
    while True:
        result = logs_client.get_query_results(queryId=query_id)
        status = result['status']

        if status == 'Complete':
            return result
        elif status == 'Failed':
            raise Exception(f"Query failed: {result}")
        elif status in ['Running', 'Scheduled']:
            print("Query running, waiting...")
            time.sleep(2)  # nosemgrep: arbitrary-sleep
        else:
            raise Exception(f"Unknown query status: {status}")


def print_table_with_tabulate(table_data: List[Dict], total_input: int, total_output: int, 
                             total_cache_read: int, total_cache_write: int, total_calls: int) -> None:
    """Print the table using the tabulate library in simple format."""
    if not TABULATE_AVAILABLE:
        print("⚠️  tabulate library not available. Install with: pip install tabulate")
        return
    
    # Prepare data for tabulate
    headers = ["Job ID", "Model", "Input", "Output", "Cache Read", "Cache Write", "Calls"]
    
    # Convert table data to list of lists
    rows = []
    for row in table_data:
        rows.append([
            row['job_id'],
            row['model_id'],
            row['input_tokens'],
            row['output_tokens'],
            row['cache_read_tokens'],
            row['cache_write_tokens'],
            row['llm_calls']
        ])
    
    # Print table in simple format (no TOTAL row)
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def format_results(results: Dict[str, Any]) -> None:
    """Format and display the query results using tabulate."""
    print("\n" + "=" * 120)
    print("TOKEN USAGE ANALYSIS RESULTS")
    print("=" * 120)

    # Display statistics
    stats = results['statistics']
    records_matched = int(stats['recordsMatched'])
    
    if records_matched > 0:
        print(f"Records matched: {records_matched}")

    # Display results
    query_results = results['results']

    if not query_results:
        print("\nNo results found.")
        print("\nTroubleshooting suggestions:")
        print("  • Expand the time range with --hours 24")
        print("  • Check if the job ID is correct")
        print("  • Verify the job made LLM calls")
        return

    print(f"\nFound {len(query_results)} result(s):")

    # Prepare table data
    table_data = []
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    total_calls = 0

    for result in query_results:
        row_data = {field['field']: field['value'] for field in result}

        job_id = row_data.get('correlation_id', 'N/A')
        model_id = row_data.get('token_usage.model_id', 'N/A')
        input_tokens = int(row_data.get('total_input_tokens', 0))
        output_tokens = int(row_data.get('total_output_tokens', 0))
        cache_read_tokens = int(row_data.get('total_cache_read_tokens', 0))
        cache_write_tokens = int(row_data.get('total_cache_write_tokens', 0))
        llm_calls = int(row_data.get('llm_calls', 0))

        table_data.append({
            'job_id': job_id,
            'model_id': model_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cache_read_tokens': cache_read_tokens,
            'cache_write_tokens': cache_write_tokens,
            'llm_calls': llm_calls
        })

        total_input += input_tokens
        total_output += output_tokens
        total_cache_read += cache_read_tokens
        total_cache_write += cache_write_tokens
        total_calls += llm_calls

    # Print table using tabulate
    print_table_with_tabulate(table_data, total_input, total_output, total_cache_read, total_cache_write, total_calls)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Query token usage from CloudWatch Log Insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query token usage for a specific job ID
  python workflow_token_usage.py --job-id e1737ab0-ddf0-4403-ad77-f54077b89809
  
  # Query all token usage in the last hour (default)
  python workflow_token_usage.py --hours 1
  
  # Query all token usage in the last 24 hours
  python workflow_token_usage.py --hours 24
  
  # Query with custom stack name
  python workflow_token_usage.py --job-id e1737ab0-ddf0-4403-ad77-f54077b89809 --stack-name MyCustomStack
        """
    )

    parser.add_argument(
        '--job-id',
        help='Specific job ID to query'
    )

    parser.add_argument(
        '--hours',
        type=int,
        default=1,
        help='Number of hours to look back from now (default: 1)'
    )

    parser.add_argument(
        '--stack-name',
        default='MainBackendStack',
        help='CloudFormation stack name (default: MainBackendStack)'
    )

    parser.add_argument(
        '--region',
        help='AWS region (uses default from profile/environment if not specified)'
    )

    args = parser.parse_args()

    # Set up AWS session
    session_kwargs = {}
    if args.region:
        session_kwargs['region_name'] = args.region

    session = boto3.Session(**session_kwargs)
    logs_client = session.client('logs')
    cf_client = session.client('cloudformation')

    # Calculate time range
    end_time = int(datetime.now().timestamp())
    start_time = end_time - (args.hours * 3600)

    # Build query
    query = build_query(args.job_id)

    # Get log groups from CloudFormation stack outputs
    log_groups = get_log_groups_from_stack_outputs(cf_client, args.stack_name)

    if not log_groups:
        print("Error: No log groups found in CloudFormation stack outputs.")
        print("\nTroubleshooting:")
        print("  • Check if the stack name is correct with --stack-name")
        print("  • Verify the stack has been deployed with log group outputs")
        print("  • Ensure you have permissions to describe CloudFormation stacks")
        return 1

    print(f"\nUsing {len(log_groups)} log groups for query")
    print()

    try:
        # Run query
        results = run_query(logs_client, query, log_groups, start_time, end_time)

        # Format and display results
        format_results(results)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
