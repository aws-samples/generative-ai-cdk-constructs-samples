#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
from pydantic import BaseModel, Field, model_validator

from amzn_code_expert_code_expert.pace_core_utils.logger import logger


class MissingPatternsError(Exception):
    """Raised when no patterns are found for a rule"""

    pass


class RuleLanguage(BaseModel):
    name: str = Field(..., description="The programming language of the code")
    default_patterns: list[str] = Field(
        ..., description="The glob patterns to use to detect the language and evaluate rules", alias="defaultPatterns"
    )
    default_exclude_patterns: Optional[list[str]] = Field(
        default_factory=list,
        description="The glob patterns to use to exclude files from evaluation",
        alias="defaultExcludePatterns",
    )


class RuleCategory(BaseModel):
    name: str = Field(..., description="The category of the code")
    languages: list[RuleLanguage] = Field(..., description="The languages that rules in this category can evaluate")
    exists: Optional[list[str]] = Field(
        default_factory=list, description="The glob patterns to use to detect if this category applies to the repo"
    )
    default_patterns: Optional[list[str]] = Field(
        default_factory=list, description="The glob patterns to use to evaluate rules", alias="defaultPatterns"
    )
    default_exclude_patterns: Optional[list[str]] = Field(
        default_factory=list,
        description="The glob patterns to use to exclude files from evaluation",
        alias="defaultExcludePatterns",
    )


class Rule(BaseModel):
    rule: str = Field(..., description="The unique identifier of the rule")
    description: str = Field(..., description="The rule to evaluate in natural language", alias="ruleDesc")
    category: RuleCategory = Field(..., description="The category that the rule can apply to")
    language: RuleLanguage = Field(..., description="The programming language the rule can be applied to")
    rule_patterns: Optional[list[str]] = Field(
        default_factory=list,
        description="The glob patterns to use to identify which files to evaluate with the rule.",
        alias="patterns",
    )
    context_patterns: Optional[list[str]] = Field(
        default_factory=list,
        description="The glob patterns to use to identify which files may have additional context needed to evaluate this rule.",
        alias="contextPatterns",
    )
    rule_exclude_patterns: Optional[list[str]] = Field(
        default_factory=list,
        description="The glob patterns to use to exclude files from evaluation",
        alias="excludePatterns",
    )

    @model_validator(mode="before")
    @classmethod
    def convert_rule_to_str(cls, data: dict) -> dict:
        if isinstance(data.get("rule"), int):
            data["rule"] = str(data["rule"])
        return data

    @property
    def patterns(self) -> list[str]:
        """
        Determine the patterns that apply to a specific rule.

        Returns:
            list[str]: A list of patterns that apply to the rule.
        """
        if self.rule_patterns:
            return self.rule_patterns
        elif self.category.default_patterns:
            return self.category.default_patterns
        elif self.language.default_patterns:
            return self.language.default_patterns
        else:
            raise MissingPatternsError(
                f"No patterns found for rule {self.rule}, category {self.category.name}, "
                f" and language {self.language.name}"
            )

    @property
    def exclude_patterns(self) -> list[str]:
        """
        Determine the exclude patterns that apply to a specific rule.

        Returns:
            list[str]: A list of patterns that apply to the rule. Default []
        """
        if self.rule_exclude_patterns:
            return self.rule_exclude_patterns
        elif self.category.default_exclude_patterns:
            return self.category.default_exclude_patterns
        elif self.language.default_exclude_patterns:
            return self.language.default_exclude_patterns
        else:
            return []


class RuleSet(BaseModel):
    languages: dict[str, RuleLanguage] = Field(default_factory=dict)
    categories: dict[str, RuleCategory] = Field(default_factory=dict)
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def build_relationships(cls, data: dict) -> dict:
        # Create a new dict for the processed data
        processed = {"languages": {}, "categories": {}, "rules": []}

        # Process languages
        for lang_data in data.get("languages", []):
            language = RuleLanguage(**lang_data)
            processed["languages"][lang_data["name"]] = language

        # Process categories
        for cat_data in data.get("categories", []):
            # Convert language names to RuleLanguage objects
            cat_data = cat_data.copy()
            cat_data["languages"] = [processed["languages"][lang_name] for lang_name in cat_data["languages"]]
            category = RuleCategory(**cat_data)
            processed["categories"][cat_data["name"]] = category

        # Process rules
        for rule_data in data.get("rules", []):
            # Convert string references to actual objects
            rule_data = rule_data.copy()  # Make a copy to avoid modifying the input
            rule_data["language"] = processed["languages"][rule_data["language"]]
            rule_data["category"] = processed["categories"][rule_data["category"]]
            processed["rules"].append(rule_data)

        return processed


def load_rules_s3(s3_client: "S3Client", bucket: str, key: str) -> RuleSet:
    rules_json = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    rules = RuleSet.model_validate_json(rules_json)
    logger.debug(f"Loaded rules from S3: {rules_json}")
    logger.debug({"message": "loaded rules", "rules": rules.model_dump()})
    return rules
