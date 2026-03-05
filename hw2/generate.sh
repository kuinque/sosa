#!/bin/bash
set -e

mkdir -p app/generated
datamodel-codegen \
    --input openapi/marketplace.yaml \
    --output app/generated/models.py \
    --input-file-type openapi \
    --output-model-type pydantic_v2.BaseModel
touch app/generated/__init__.py

echo "Code generation complete: app/generated/models.py"
