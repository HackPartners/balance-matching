#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_FILE="${DIR}/../src/main.py"

source "${DIR}/.env.local"

# TODO: update target name
functions-framework \
  --source=${SOURCE_FILE} \
  --target=run_localisation \
  --signature-type=http \
  --port=4000 \
  --debug
