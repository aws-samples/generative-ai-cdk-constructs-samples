#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.


set -e

# must be run from project root
if [ ! -f "pnpm-lock.yaml" ]; then
    echo "Must be run from project root"
    exit 1
fi

# takes one argument, the output pdf filename
if [ $# -ne 1 ]; then
    echo "Usage: $0 <output.pdf>"
    exit 1
fi
# validate that output is pdf
if [[ $1 != *.pdf ]]; then
    echo "Output must be a pdf file"
    exit 1
fi

export MERMAID_FILTER_FORMAT=pdf

pandoc --metadata title="Code Expert" \
  -V colorlinks=true -V linkcolor=blue -V toccolor=gray -V urlcolor=blue \
  -F mermaid-filter -f markdown-implicit_figures -f markdown+rebase_relative_paths --file-scope \
  --number-sections --toc --toc-depth=2 -s \
  README.md \
  documentation/technical-approach.md documentation/rules.md documentation/improvements.md documentation/security.md \
  notebooks/README.md demo/README.md \
  -o $1