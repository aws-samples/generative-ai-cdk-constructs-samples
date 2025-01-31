#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from amzn_code_expert_code_expert.models.rules import RuleSet, RuleLanguage, RuleCategory, Rule
from .file_manager import FileManager


class RuleDetector:
    def __init__(self, file_manager: FileManager, rule_set: RuleSet):
        self.file_manager = file_manager
        self.rule_set = rule_set
        self._languages = None
        self._categories = None
        self._simple_rules = None
        self._context_rules = None

    @property
    def languages(self) -> list[RuleLanguage]:
        """the languages used in the repository.

        Return
            list[RuleLanguage]: A list of RuleLanguage objects that are used in the repository.
        """
        if self._languages is None:
            self._languages = self._determine_languages()
        return self._languages

    @property
    def categories(self) -> list[RuleCategory]:
        """the categories used in the repository.

        Return
            list[RuleCategory]: A list of RuleCategory objects that are used in the repository.
        """
        if self._categories is None:
            self._categories = self._determine_categories()
        return self._categories

    @property
    def simple_rules(self) -> list[Rule]:
        """the simple rules used in the repository.

        Return
            list[Rule]: A list of Rule objects that are used in the repository.
        """
        self._ensure_rules_determined()
        return self._simple_rules

    @property
    def context_rules(self) -> list[Rule]:
        """the context rules used in the repository.

        Return
            list[Rule]: A list of Rule objects that are used in the repository.
        """
        self._ensure_rules_determined()
        return self._context_rules

    def _determine_languages(self) -> list[RuleLanguage]:
        """Determine the languages used in the repository.

        Return
            list[RuleLanguage]: A list of RuleLanguage objects that are used in the repository.
        """
        languages = []
        for language in self.rule_set.languages.values():
            if any(
                self.file_manager.match_glob_pattern(file, pattern)
                for pattern in language.default_patterns
                for file in self.file_manager.all_files
            ):
                languages.append(language)

        return languages

    def _determine_categories(self) -> list[RuleCategory]:
        """Determine the categories used in the repository.

        Return
            list[RuleCategory]: A list of RuleCategory objects that are used in the repository.
        """
        categories = []
        for category in self.rule_set.categories.values():
            if set([l.name for l in category.languages]).isdisjoint((l.name for l in self.languages)):
                continue
            # if the category has patterns in exists, all of them must be in the repository
            if category.exists and not all(
                any(self.file_manager.match_glob_pattern(file, pattern) for file in self.file_manager.all_files)
                for pattern in category.exists
            ):
                continue
            categories.append(category)
        return categories

    def _determine_rules(self) -> tuple[list[Rule], list[Rule]]:
        """Determine the rules used in the repository.

        Return
            tuple[list[Rule], list[Rule]]: A tuple with two lists of Rule objects,
                the first list contains simple rules, and the second list contains context rules.
        """
        simple_rules = list()
        context_rules = list()
        for rule in self.rule_set.rules:
            if rule.language not in self.languages or rule.category not in self.categories:
                continue
            if rule.context_patterns:
                context_rules.append(rule)
            else:
                simple_rules.append(rule)
        return simple_rules, context_rules

    def _ensure_rules_determined(self):
        if self._simple_rules is None or self._context_rules is None:
            self._simple_rules, self._context_rules = self._determine_rules()
