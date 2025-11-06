#!/bin/bash
asciidoctor-pdf --theme=custom-theme.yml -r asciidoctor-lists -a currentdate="$(date '+%B %-d, %Y')" technical-documentation.adoc
echo "PDF report has been successfully generated"
