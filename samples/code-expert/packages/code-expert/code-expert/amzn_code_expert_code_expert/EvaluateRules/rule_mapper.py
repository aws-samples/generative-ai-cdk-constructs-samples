#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from amzn_code_expert_code_expert.models.rules import Rule


class RuleMapper:
    def __init__(self, file_manager, rule_detector):
        self.file_manager = file_manager
        self.rule_detector = rule_detector
        self._rules_by_file = None
        self._context_files_by_rule = None
        self._context_rules_by_file = None
        self._context_rules_by_context_file = None

    @property
    def rules_by_file(self) -> dict[str, list[Rule]]:
        """
        The rules that apply to each file in the repository.

        Returns:
            dict[str, list[Rule]]: A dictionary where the keys are file paths and the values are lists of Rule objects that apply to that file.
        """
        if not self._rules_by_file:
            rules_by_file = {}
            for file in self.file_manager.all_files:
                rules = []
                for rule in self.rule_detector.simple_rules:
                    if any(
                        self.file_manager.match_glob_pattern(file, pattern) for pattern in rule.patterns
                    ) and not any(
                        self.file_manager.match_glob_pattern(file, exclude) for exclude in rule.exclude_patterns
                    ):
                        rules.append(rule)
                if rules:
                    rules_by_file[file] = rules
            self._rules_by_file = rules_by_file
        return self._rules_by_file

    @property
    def context_rules_by_context_file(self) -> dict[str, list[Rule]]:
        """
        The rules that need a given file for context.

        Returns:
            dict[str, list[Rule]]: A dictionary where the keys are file paths and the values are lists of Rule objects that need that file for context.
        """
        if not self._context_rules_by_context_file:
            rules_by_context_file = {}
            for file in self.file_manager.all_files:
                rules = []
                for rule in self.rule_detector.context_rules:
                    if any(self.file_manager.match_glob_pattern(file, pattern) for pattern in rule.context_patterns):
                        rules.append(rule)
                if rules:
                    rules_by_context_file[file] = rules
            self._context_rules_by_context_file = rules_by_context_file
        return self._context_rules_by_context_file

    @property
    def context_files_by_rule(self) -> dict[str, list[str]]:
        """
        The files that are needed for context for each rule.

        Returns:
            dict[str, list[str]]: A dictionary where the keys are rule ids and the values are lists of file paths that are needed for context for that rule.
        """
        if not self._context_files_by_rule:
            context_files_by_rule = {}
            for file, rules in self.context_rules_by_context_file.items():
                for rule in rules:
                    if rule.rule not in context_files_by_rule:
                        context_files_by_rule[rule.rule] = []
                    context_files_by_rule[rule.rule].append(file)
            self._context_files_by_rule = context_files_by_rule
        return self._context_files_by_rule

    @property
    def context_rules_by_file(self) -> dict[str, list[Rule]]:
        """
        The context rules that apply to each file in the repository.

        Returns:
            dict[str, list[Rule]]: A dictionary where the keys are file paths and the values are lists of Rule objects that apply to that file.
        """
        if not self._context_rules_by_file:
            context_rules_by_file = {}
            for file in self.file_manager.all_files:
                rules = []
                for rule in self.rule_detector.context_rules:
                    if any(
                        self.file_manager.match_glob_pattern(file, pattern) for pattern in rule.patterns
                    ) and not any(
                        self.file_manager.match_glob_pattern(file, exclude) for exclude in rule.exclude_patterns
                    ):
                        rules.append(rule)
                if rules:
                    context_rules_by_file[file] = rules
            self._context_rules_by_file = context_rules_by_file
        return self._context_rules_by_file
