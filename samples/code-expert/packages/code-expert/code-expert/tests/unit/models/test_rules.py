#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import pytest

from amzn_code_expert_code_expert.models.rules import RuleSet, RuleLanguage, RuleCategory, Rule, MissingPatternsError


@pytest.fixture
def base_rules():
    return {
        "languages": [{"name": "test", "defaultPatterns": ["**/*.test"]}],
        "categories": [
            {
                "name": "test",
                "languages": ["test"],
                "exists": [
                    "**/*.test",
                ],
            }
        ],
        "rules": [
            {
                "rule": "1",
                "category": "test",
                "language": "test",
                "ruleDesc": "rule text",
            },
        ],
    }


@pytest.fixture
def rule_set_with_patterns():
    return RuleSet.model_validate(
        {
            "languages": [
                {"name": "python", "defaultPatterns": ["**/*.py"], "defaultExcludePatterns": ["**/venv/**"]},
                {"name": "java", "defaultPatterns": ["**/*.java"]},
            ],
            "categories": [
                {
                    "name": "security",
                    "languages": ["python", "java"],
                    "defaultPatterns": ["**/security/*.py", "**/security/*.java"],
                    "defaultExcludePatterns": ["**/test/**"],
                },
                {"name": "performance", "languages": ["python", "java"]},
            ],
            "rules": [
                {
                    "rule": "1",
                    "category": "security",
                    "language": "python",
                    "ruleDesc": "Python security rule",
                    "patterns": ["**/custom/*.py"],
                    "excludePatterns": ["**/generated/**"],
                },
                {"rule": "2", "category": "security", "language": "java", "ruleDesc": "Java security rule"},
                {"rule": "3", "category": "performance", "language": "python", "ruleDesc": "Python performance rule"},
            ],
        }
    )


def test_validate_base_rules(base_rules):
    rule_set = RuleSet.model_validate(base_rules)
    assert isinstance(rule_set.languages["test"], RuleLanguage)
    assert rule_set.languages["test"].name == "test"
    assert isinstance(rule_set.categories["test"], RuleCategory)
    assert rule_set.categories["test"].name == "test"
    assert isinstance(rule_set.categories["test"].languages[0], RuleLanguage)
    assert rule_set.categories["test"].languages[0].name == "test"
    assert isinstance(rule_set.rules[0], Rule)
    assert rule_set.rules[0].rule == "1"
    assert isinstance(rule_set.rules[0].category, RuleCategory)
    assert isinstance(rule_set.rules[0].language, RuleLanguage)
    assert rule_set.rules[0].description == "rule text"


def test_multiple_languages_and_categories():
    multi_rules = {
        "languages": [
            {"name": "python", "defaultPatterns": ["**/*.py"]},
            {"name": "javascript", "defaultPatterns": ["**/*.js"]},
        ],
        "categories": [
            {"name": "security", "languages": ["python", "javascript"]},
            {"name": "performance", "languages": ["python", "javascript"]},
        ],
        "rules": [
            {"rule": "1", "category": "security", "language": "python", "ruleDesc": "Python security rule"},
            {"rule": "2", "category": "performance", "language": "javascript", "ruleDesc": "JS performance rule"},
        ],
    }
    rule_set = RuleSet.model_validate(multi_rules)
    assert len(rule_set.languages) == 2
    assert len(rule_set.categories) == 2
    assert len(rule_set.rules) == 2
    # assert len(rule_set.get_rules_for_language("python")) == 1
    # assert len(rule_set.get_rules_for_language("javascript")) == 1
    # assert len(rule_set.get_rules_for_category("security")) == 1
    # assert len(rule_set.get_rules_for_category("performance")) == 1


def test_custom_patterns():
    custom_rules = {
        "languages": [{"name": "python", "defaultPatterns": ["**/*.py"]}],
        "categories": [{"name": "custom", "languages": ["python"]}],
        "rules": [
            {
                "rule": "1",
                "category": "custom",
                "language": "python",
                "ruleDesc": "Custom rule",
                "patterns": ["**/custom/*.py"],
                "contextPatterns": ["**/context/*.py"],
            }
        ],
    }
    rule_set = RuleSet.model_validate(custom_rules)
    assert rule_set.rules[0].patterns == ["**/custom/*.py"]
    assert rule_set.rules[0].context_patterns == ["**/context/*.py"]


def test_out_of_order_input():
    unordered_rules_json = """{
        "rules": [
            {
                "rule": "1",
                "category": "security",
                "language": "python",
                "ruleDesc": "Python security rule"
            },
            {
                "rule": "2",
                "category": "performance",
                "language": "javascript",
                "ruleDesc": "JS performance rule"
            }
        ],
        "categories": [
            {"name": "security", "languages": ["python", "javascript"]},
            {"name": "performance", "languages": ["python", "javascript"]}
        ],
        "languages": [
            {"name": "python", "defaultPatterns": ["**/*.py"]},
            {"name": "javascript", "defaultPatterns": ["**/*.js"]}
        ]
    }"""

    rule_set = RuleSet.model_validate_json(unordered_rules_json)

    # Verify that all components are correctly processed
    assert len(rule_set.languages) == 2
    assert len(rule_set.categories) == 2
    assert len(rule_set.rules) == 2

    # Check if languages are correctly processed
    assert isinstance(rule_set.languages["python"], RuleLanguage)
    assert isinstance(rule_set.languages["javascript"], RuleLanguage)

    # Check if categories are correctly processed
    assert isinstance(rule_set.categories["security"], RuleCategory)
    assert isinstance(rule_set.categories["performance"], RuleCategory)

    # Check if rules are correctly processed and linked
    for rule in rule_set.rules:
        assert isinstance(rule, Rule)
        assert isinstance(rule.category, RuleCategory)
        assert isinstance(rule.language, RuleLanguage)


def test_rule_patterns(rule_set_with_patterns):
    # Rule with its own patterns
    assert rule_set_with_patterns.rules[0].patterns == ["**/custom/*.py"]

    # Rule using category patterns
    assert rule_set_with_patterns.rules[1].patterns == ["**/security/*.py", "**/security/*.java"]

    # Rule using language patterns
    assert rule_set_with_patterns.rules[2].patterns == ["**/*.py"]


def test_rule_exclude_patterns(rule_set_with_patterns):
    # Rule with its own exclude patterns
    assert rule_set_with_patterns.rules[0].exclude_patterns == ["**/generated/**"]

    # Rule using category exclude patterns
    assert rule_set_with_patterns.rules[1].exclude_patterns == ["**/test/**"]

    # Rule using language exclude patterns
    assert rule_set_with_patterns.rules[2].exclude_patterns == ["**/venv/**"]


def test_missing_patterns():
    rule_set = RuleSet.model_validate(
        {
            "languages": [{"name": "ruby", "defaultPatterns": []}],
            "categories": [{"name": "misc", "languages": ["ruby"]}],
            "rules": [{"rule": "1", "category": "misc", "language": "ruby", "ruleDesc": "Ruby misc rule"}],
        }
    )

    with pytest.raises(MissingPatternsError):
        _ = rule_set.rules[0].patterns


def test_missing_exclude_patterns():
    rule_set = RuleSet.model_validate(
        {
            "languages": [{"name": "ruby", "defaultPatterns": ["**/*.rb"]}],
            "categories": [{"name": "misc", "languages": ["ruby"]}],
            "rules": [{"rule": "1", "category": "misc", "language": "ruby", "ruleDesc": "Ruby misc rule"}],
        }
    )

    # Should return an empty list when no exclude patterns are defined
    assert rule_set.rules[0].exclude_patterns == []


def test_patterns_precedence(rule_set_with_patterns):
    # Create a new rule with patterns at all levels
    new_rule = Rule(
        rule="4",
        category=rule_set_with_patterns.categories["security"],
        language=rule_set_with_patterns.languages["python"],
        ruleDesc="Test precedence",
        patterns=["**/rule_level/*.py"],
    )

    # Rule-level patterns should take precedence
    assert new_rule.patterns == ["**/rule_level/*.py"]

    # Remove rule-level patterns
    new_rule.rule_patterns = []
    # Category-level patterns should be used
    assert new_rule.patterns == ["**/security/*.py", "**/security/*.java"]

    # Remove category-level patterns
    new_rule.category.default_patterns = []
    # Language-level patterns should be used
    assert new_rule.patterns == ["**/*.py"]


def test_exclude_patterns_precedence(rule_set_with_patterns):
    # Create a new rule with exclude patterns at all levels
    new_rule = Rule(
        rule="4",
        category=rule_set_with_patterns.categories["security"],
        language=rule_set_with_patterns.languages["python"],
        ruleDesc="Test precedence",
        excludePatterns=["**/rule_exclude/**"],
    )

    # Rule-level exclude patterns should take precedence
    assert new_rule.exclude_patterns == ["**/rule_exclude/**"]

    # Remove rule-level exclude patterns
    new_rule.rule_exclude_patterns = []
    # Category-level exclude patterns should be used
    assert new_rule.exclude_patterns == ["**/test/**"]

    # Remove category-level exclude patterns
    new_rule.category.default_exclude_patterns = []
    # Language-level exclude patterns should be used
    assert new_rule.exclude_patterns == ["**/venv/**"]

    # Remove language-level exclude patterns
    new_rule.language.default_exclude_patterns = []
    # Should return an empty list when no exclude patterns are defined
    assert new_rule.exclude_patterns == []


def test_rule_with_int_identifiers():
    rule_set = RuleSet.model_validate(
        {
            "languages": [{"name": "ruby", "defaultPatterns": []}],
            "categories": [{"name": "misc", "languages": ["ruby"]}],
            "rules": [{"rule": 1, "category": "misc", "language": "ruby", "ruleDesc": "Ruby misc rule"}],
        }
    )

    assert rule_set.rules[0].rule == "1"
