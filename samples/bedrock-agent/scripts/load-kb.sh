#!/bin/env bash

set -e -x

# first parameter is the S3 uri with bucket and prefix
# e.g. s3://my-bucket/my-prefix/
# second parameter is the Knowledge Base ID
# e.g. my-kb-id
# third parameter is the Data Source ID
# check that we have the right number of parameters
if [ $# -ne 3 ]; then
    echo "Usage: $0 <s3-uri> <kb-id> <data-source-id"
    exit 1
fi

S3_URI=$1
KB_ID=$2
DS_ID=$3

BOOKS_LIST=("https://www.gutenberg.org/ebooks/84.txt.utf-8"
  "https://www.gutenberg.org/ebooks/1342.txt.utf-8"
  "https://www.gutenberg.org/ebooks/2701.txt.utf-8"
  "https://www.gutenberg.org/ebooks/1513.txt.utf-8")

# make a temporary directory to download the books
BOOKS_DIR=`mktemp -d -t books`

pushd $BOOKS_DIR

# download the books
for book in "${BOOKS_LIST[@]}"
do
  curl -L -o "$(basename $book).txt" $book
done

aws s3 sync . $S3_URI
popd
rm -rf $BOOKS_DIR

# sync kb
aws bedrock-agent start-ingestion-job --knowledge-base-id $KB_ID --data-source-id $DS_ID
