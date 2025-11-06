#!/bin/bash
docker run --rm -v $(pwd):/app asciidoc-generator bash -c \
  "asciidoctor-pdf --theme=custom-theme.yml -r asciidoctor-lists -a currentdate=\"\$(date '+%B %-d, %Y')\" ${1:-technical-documentation.adoc}"