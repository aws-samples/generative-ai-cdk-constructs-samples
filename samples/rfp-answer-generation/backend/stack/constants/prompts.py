#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

SUPPORTING_DOCUMENT_PARSING_PROMPT = """
Extract the content from an image page and output in Markdown syntax. Enclose the content in the <markdown></markdown> tag and do not use code blocks. If the image is empty then output a <markdown></markdown> without anything in it.

Follow these steps:

1. Examine the provided page carefully.

2. Identify all elements present in the page, including headers, body text, footnotes, tables, images, captions, and page numbers, etc.

3. Use markdown syntax to format your output:
    - Headings: # for main, ## for sections, ### for subsections, etc.
    - Lists: * or - for bulleted, 1. 2. 3. for numbered
    - Do not repeat yourself

4. If the element is an image (not table)
    - If the image is a logo or stock image, ignore it
    - If the information in the image can be represented by a table, generate the table containing the information of the image
    - Otherwise provide a detailed description about the information in image
    - Classify the element as one of: Chart, Diagram, Logo, Icon, Natural Image, Screenshot, Other. Enclose the class in <figure_type></figure_type>
    - Enclose <figure_type></figure_type>, the table or description, and the figure title or caption (if available), in <figure></figure> tags
    - Do not transcribe text in the image after providing the table or description

5. If the element is a table
    - Create a markdown table, ensuring every row has the same number of columns
    - Maintain cell alignment as closely as possible
    - Do not split a table into multiple tables
    - If a merged cell spans multiple rows or columns, place the text in the top-left cell and output ' ' for other
    - Use | for column separators, |-|-| for header row separators
    - If a cell has multiple items, list them in separate rows
    - If the table contains sub-headers, separate the sub-headers from the headers in another row

6. If the element is a paragraph
    - Transcribe each text element precisely as it appears

7. If the element is a header, footer, footnote, page number
    - Do not transcribe

Output Example:
<markdown>
<figure>
<figure_type>Chart</figure_type>
Figure 3: This chart shows annual sales in millions. The year 2020 was significantly down due to the COVID-19 pandemic.
A bar chart showing annual sales figures, with the y-axis labeled "Sales ($Million)" and the x-axis labeled "Year". The chart has bars for 2018 ($12M), 2019 ($18M), 2020 ($8M), and 2021 ($22M).
</figure>

<figure>
<figure_type>Chart</figure_type>
Figure 3: This chart shows annual sales in millions. The year 2020 was significantly down due to the COVID-19 pandemic.
| Year | Sales ($Million) |
|-|-|
| 2018 | $12M |
| 2019 | $18M |
| 2020 | $8M |
| 2021 | $22M |
</figure>

# Annual Report

## Financial Highlights

* Revenue: $40M
* Profit: $12M
* EPS: $1.25

| | Year Ended December 31, | |
| | 2021 | 2022 |
|-|-|-|
| Cash provided by (used in): | | |
| Operating activities | $ 46,327 | $ 46,752 |
| Investing activities | (58,154) | (37,601) |
| Financing activities | 6,291 | 9,718 |

</markdown>
"""
