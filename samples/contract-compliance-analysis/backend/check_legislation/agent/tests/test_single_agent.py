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

import pytest
from agents.single_agent import extract_items_from_tagged_list


class TestExtractItemsFromTaggedList:
    """Test cases for the XML-based extract_items_from_tagged_list function"""

    def test_simple_single_tag(self):
        text = "<item>First item</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["First item"]

    def test_multiple_tags(self):
        text = "<item>First item</item><item>Second item</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["First item", "Second item"]

    def test_nested_tags_extracts_all(self):
        text = "<item>Outer<item>Inner</item></item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Outer", "Inner"]

    def test_tags_with_attributes(self):
        text = '<item id="1">Content with attributes</item>'
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Content with attributes"]

    def test_multiline_content(self):
        text = "<item>Line 1\nLine 2</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Line 1\nLine 2"]

    def test_empty_tags_ignored(self):
        text = "<item></item><item>Valid content</item><item>   </item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Valid content"]

    def test_no_matching_tags(self):
        text = "<other>Some content</other>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == []

    def test_mixed_content(self):
        text = "Some text <item>First</item> more text <item>Second</item> end"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["First", "Second"]

    def test_deeply_nested_tags(self):
        text = "<container><item>First</item><section><item>Second</item></section></container>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["First", "Second"]

    def test_self_closing_tags(self):
        text = "<item/><item>Content</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Content"]

    def test_empty_input(self):
        text = ""
        result = extract_items_from_tagged_list(text, "item")
        assert result == []

    def test_whitespace_only_input(self):
        text = "   \n\t  "
        result = extract_items_from_tagged_list(text, "item")
        assert result == []

    # Edge cases for malformed XML - should be handled gracefully with regex fallback
    def test_unclosed_tag_handled_gracefully(self):
        text = "<item>Unclosed content"
        result = extract_items_from_tagged_list(text, "item")
        assert result == []  # No complete tags found

    def test_malformed_opening_tag_handled_gracefully(self):
        text = "<item asdfasd </item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == []  # Malformed opening tag won't match regex

    def test_missing_closing_bracket_handled_gracefully(self):
        text = "<item>foo"
        result = extract_items_from_tagged_list(text, "item")
        assert result == []  # No closing tag found

    def test_mismatched_tags_handled_gracefully(self):
        text = "<item>Content</other>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == []  # No matching closing tag

    def test_nested_unclosed_tags_handled_gracefully(self):
        text = "<item>Outer<item>Inner</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Inner"]  # Regex finds the complete inner tag

    def test_broken_attribute_syntax_handled_gracefully(self):
        text = '<item id="unclosed>Content</item>'
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Content"]  # Regex fallback is more permissive

    def test_invalid_xml_characters_handled_gracefully(self):
        text = "<item>Content & more</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Content & more"]  # Regex handles special chars fine

    def test_multiple_root_elements_handled(self):
        text = "<item>First</item><item>Second</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["First", "Second"]

    def test_whitespace_handling(self):
        text = "<item>  Content with spaces  </item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Content with spaces"]

    def test_complex_nested_structure(self):
        text = "<root><item>Level1<sub><item>Level2</item></sub></item><item>Another</item></root>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Level1", "Level2", "Another"]

    def test_tags_with_complex_attributes(self):
        text = '<item class="test" data-value="123" style="color:red">Content</item>'
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Content"]

    # Additional robustness tests
    def test_partial_tags_ignored(self):
        text = "<ite>Not a match</ite><item>Match</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Match"]

    def test_case_sensitive_tags(self):
        text = "<Item>Wrong case</Item><item>Right case</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Right case"]

    def test_mixed_malformed_and_valid(self):
        text = "<item>Valid</item><item>Unclosed<item>Another valid</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Valid", "Another valid"]

    def test_html_entities_preserved(self):
        text = "<item>&lt;escaped&gt; content</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["<escaped> content"]  # XML parser decodes entities

    def test_cdata_sections_handled(self):
        text = "<item><![CDATA[Raw content with <tags>]]></item>"
        result = extract_items_from_tagged_list(text, "item")
        # XML parser handles CDATA, regex fallback treats it as text
        assert len(result) == 1

    def test_very_long_content(self):
        long_content = "x" * 10000
        text = f"<item>{long_content}</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == [long_content]

    def test_unicode_content(self):
        text = "<item>Conteúdo em português with émojis 🚀</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Conteúdo em português with émojis 🚀"]

    # Extreme robustness tests
    def test_binary_content_handled(self):
        text = "<item>\x00\x01\x02binary</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["\x00\x01\x02binary"]

    def test_deeply_malformed_xml_handled(self):
        text = "<<<>>><<item>>content<</item>>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == [">content<"]  # Regex finds what it can

    def test_mixed_valid_invalid_complex(self):
        text = "<item>Valid1</item><<broken><item>Valid2</item><item>Unclosed"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["Valid1", "Valid2"]

    def test_xml_comments_ignored(self):
        text = "<!-- comment --><item>content</item><?xml version='1.0'?>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["content"]

    def test_very_long_content_handled(self):
        long_content = "A" * 10000
        text = f"<item>{long_content}</item>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == [long_content]

    def test_similar_tag_names_precise(self):
        text = "<item>content</item><items>not matched</items><itemx>also not</itemx>"
        result = extract_items_from_tagged_list(text, "item")
        assert result == ["content"]
