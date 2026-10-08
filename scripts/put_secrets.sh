#!/usr/bin/env bash
# Copy secrets from .env into SSM Parameter Store SecureStrings under /clearsky/{STAGE}/...
# Usage: ./scripts/put_secrets.sh            (only non-empty values are written; existing ones are overwritten)
# Runs on macOS/Linux or Git Bash on Windows. Needs the AWS CLI with credentials for the target account.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[ -f "$ENV_FILE" ] || { echo "No .env found at $ENV_FILE (copy .env.example)"; exit 1; }

get() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/\r$//"; }

STAGE="$(get STAGE)"; STAGE="${STAGE:-dev}"
REGION="$(get AWS_REGION)"; REGION="${REGION:-ap-south-1}"

declare -A PATHS=(
  [WA_PHONE_NUMBER_ID]="wa/phone_number_id"
  [WA_ACCESS_TOKEN]="wa/access_token"
  [WA_APP_SECRET]="wa/app_secret"
  [WA_VERIFY_TOKEN]="wa/verify_token"
  [FIRMS_MAP_KEY]="firms/map_key"
)

for NAME in "${!PATHS[@]}"; do
  VALUE="$(get "$NAME" || true)"
  PARAM="/clearsky/$STAGE/${PATHS[$NAME]}"
  if [ -z "$VALUE" ]; then
    echo "skip  $NAME (empty)"
    continue
  fi
  aws ssm put-parameter --region "$REGION" --name "$PARAM" --type SecureString --value "$VALUE" --overwrite >/dev/null
  echo "wrote $PARAM"
done
