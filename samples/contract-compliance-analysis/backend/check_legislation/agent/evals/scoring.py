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

from typing import Any, Dict, Optional, Union


def calculate_score(
    named_scores: Dict[str, float], context: Optional[Dict[str, Any]] = None
) -> Dict[str, Union[bool, float, str]]:
  # we will ignore the llm-rubric assertion for now, since it might be a little bit too subjective.
  # in the future, if we want to re-consider it, we can simply remove the custom assertScoringFunction from the
  # defaultTest key of promptfooconfig.yaml
  all_assertion_results_without_llm_rubric = [
    result
    for result in context.get("componentResults", [])
    if result["assertion"]["type"] != "llm-rubric"
  ]

  return {
    "pass": all(result["pass"] for result in all_assertion_results_without_llm_rubric),
    "score": sum(
      result["score"] for result in all_assertion_results_without_llm_rubric
    ) / len(all_assertion_results_without_llm_rubric),
    "reason": f"Ignoring llm-rubric",
  }
