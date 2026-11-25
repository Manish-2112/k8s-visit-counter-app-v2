#!/usr/bin/env bash
# Week 11: Creates AWS ECR repositories (with lifecycle policies) and AWS SSM Parameter Store secrets.
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-ProdSecurePass2026!}"

echo "=== 1. Creating ECR Repositories in ${AWS_REGION} ==="
for REPO in visit-counter-backend visit-counter-frontend; do
  aws ecr describe-repositories --repository-names "${REPO}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
    aws ecr create-repository \
      --repository-name "${REPO}" \
      --image-scanning-configuration scanOnPush=true \
      --region "${AWS_REGION}"

  # Production hygiene: Keep only the last 10 images to control ECR storage costs
  aws ecr put-lifecycle-policy \
    --repository-name "${REPO}" \
    --region "${AWS_REGION}" \
    --lifecycle-policy-text '{
      "rules": [{
        "rulePriority": 1,
        "description": "Keep last 10 images",
        "selection": {
          "tagStatus": "any",
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": { "type": "expire" }
      }]
    }'
done

echo "=== 2. Storing Config & Secrets in AWS Systems Manager (SSM) Parameter Store ==="
aws ssm put-parameter \
  --name "/visit-counter/prod/POSTGRES_USER" \
  --value "${DB_USER}" \
  --type "String" \
  --overwrite \
  --region "${AWS_REGION}"

aws ssm put-parameter \
  --name "/visit-counter/prod/POSTGRES_PASSWORD" \
  --value "${DB_PASS}" \
  --type "SecureString" \
  --overwrite \
  --region "${AWS_REGION}"

echo "=== Done! ECR repos and SSM parameters are ready. ==="
