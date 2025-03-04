#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import fnmatch
import os


class FileManager:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self._all_files = None

    @property
    def all_files(self) -> set[str]:
        """all files in the repository.

        Returns:
            set[str]: A list of file paths in the repository.
        """
        if self._all_files is None:
            self._all_files = self._list_files()
        return self._all_files

    def _list_files(self):
        """List all files in the repository.

        Returns:
            set[str]: A list of file paths in the repository.
        """
        all_files = set()
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                all_files.add(os.path.relpath(os.path.join(root, file), self.repo_path))
        return all_files

    @staticmethod
    def match_glob_pattern(file, pattern):
        # prepend './' to match files in the root directory with patterns that start with '**/'
        if pattern.startswith("**/") and not file.startswith("./"):
            file = "./" + file
        return fnmatch.fnmatch(file, pattern)
