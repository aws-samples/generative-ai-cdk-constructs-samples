#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from unittest.mock import Mock

import pytest

from amzn_code_expert_code_expert.EvaluateRules.file_manager import FileManager
from amzn_code_expert_code_expert.EvaluateRules.rule_detector import RuleDetector
from amzn_code_expert_code_expert.models.rules import RuleSet


@pytest.fixture
def rule_set():
    return RuleSet.model_validate(
        {
            "languages": [{"name": "python", "defaultPatterns": ["*.py"], "defaultExcludePatterns": ["test_*.py"]}],
            "categories": [{"name": "test-python", "languages": ["python"], "exists": ["src/__init__.py"]}],
            "rules": [
                {
                    "rule": "python-1",
                    "category": "test-python",
                    "language": "python",
                    "ruleDesc": "Avoid Large Classes. Classes should follow Single Responsibility Principle. A class should not have more than 10 methods. Methods should be cohesive and related to the class's primary purpose",
                },
                {
                    "rule": "python-2",
                    "category": "test-python",
                    "language": "python",
                    "ruleDesc": "Exception Handling Anti-pattern. Avoid bare except clauses. Always catch specific exceptions. Don't silently pass exceptions.",
                },
            ],
        }
    )


@pytest.fixture
def file_manager():
    mock_file_manager = Mock(spec=FileManager)
    mock_file_manager.all_files = {"src/__init__.py", "main.py", "test_exclude.py"}
    mock_file_manager.match_glob_pattern.side_effect = FileManager.match_glob_pattern
    return mock_file_manager


@pytest.fixture
def rule_detector(file_manager, rule_set):
    return RuleDetector(file_manager, rule_set)


def test_languages(rule_detector):
    languages = rule_detector.languages
    assert len(languages) == 1
    assert languages[0].name == "python"


def test_categories(rule_detector):
    categories = rule_detector.categories
    assert len(categories) == 1
    assert categories[0].name == "test-python"


def test_simple_rules(rule_detector):
    simple_rules = rule_detector.simple_rules
    assert len(simple_rules) == 2
    assert simple_rules[0].rule == "python-1"
    assert simple_rules[1].rule == "python-2"


def test_context_rules(rule_detector):
    context_rules = rule_detector.context_rules
    assert len(context_rules) == 0


def test_determine_languages(rule_detector, file_manager):
    languages = rule_detector._determine_languages()
    assert len(languages) == 1
    assert languages[0].name == "python"
    file_manager.match_glob_pattern.assert_called()


def test_determine_categories(rule_detector, file_manager):
    categories = rule_detector._determine_categories()
    assert len(categories) == 1
    assert categories[0].name == "test-python"
    file_manager.match_glob_pattern.assert_called()


def test_determine_rules(rule_detector):
    simple_rules, context_rules = rule_detector._determine_rules()
    assert len(simple_rules) == 2
    assert len(context_rules) == 0
    assert simple_rules[0].rule == "python-1"
    assert simple_rules[1].rule == "python-2"


def test_ensure_rules_determined(rule_detector):
    rule_detector._ensure_rules_determined()
    assert rule_detector._simple_rules is not None
    assert rule_detector._context_rules is not None
