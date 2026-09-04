#!/usr/bin/env bash
set -euo pipefail

if ! command -v gitleaks >/dev/null 2>&1; then
  echo "FAIL: gitleaks is required" >&2
  exit 1
fi

ERRORS=0

assert_ignored() {
  local path="$1"
  if git check-ignore --quiet --no-index "$path"; then
    echo "  OK ignored: $path"
  else
    echo "  FAIL not ignored: $path"
    ERRORS=$((ERRORS + 1))
  fi
}

assert_trackable() {
  local path="$1"
  if git check-ignore --quiet --no-index "$path"; then
    echo "  FAIL unexpectedly ignored: $path"
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK trackable: $path"
  fi
}

echo "=== Verifying public-repository ignore rules ==="
for path in \
  .DS_Store \
  claude/hooks/tests/.DS_Store \
  .serena/project.yml \
  reports/audit.md \
  claude/hooks/tests/__pycache__/module.pyc \
  .npmrc \
  .env \
  app/.env.production \
  deploy.key \
  deploy.pem \
  signing.p12 \
  id_ed25519; do
  assert_ignored "$path"
done

for path in .npmrc.example .env.example config/.env.dev.example; do
  assert_trackable "$path"
done

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
mkdir -p "$tmp_dir/leak" "$tmp_dir/clean"

synthetic_prefix="AKIA"
synthetic_tail="Q7W4ERT5Y2UI6OPA"
printf 'aws_access_key_id = %s%s\n' \
  "$synthetic_prefix" "$synthetic_tail" > "$tmp_dir/leak/credentials"

echo "=== Verifying a synthetic credential is rejected ==="
report="$tmp_dir/findings.json"
if gitleaks dir --no-banner --no-color --redact --timeout 30 \
  --report-format json --report-path "$report" "$tmp_dir/leak"; then
  echo "  FAIL: synthetic credential was not detected"
  ERRORS=$((ERRORS + 1))
elif python3 - "$report" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as findings_file:
    findings = json.load(findings_file)

if not any(finding.get("RuleID") == "aws-access-token" for finding in findings):
    raise SystemExit(1)
PY
then
  echo "  OK: synthetic credential detected"
else
  echo "  FAIL: scanner failed without the expected finding"
  ERRORS=$((ERRORS + 1))
fi

printf '%s\n' \
  'API_TOKEN=${API_TOKEN}' \
  'AWS_ACCESS_KEY_ID=replace-me' \
  'private_key_path=/path/to/private.key' > "$tmp_dir/clean/.env.example"

echo "=== Verifying placeholder configuration is accepted ==="
if gitleaks dir --no-banner --no-color --redact --timeout 30 "$tmp_dir/clean"; then
  echo "  OK: placeholder configuration accepted"
else
  echo "  FAIL: placeholder configuration produced a finding"
  ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -ne 0 ]; then
  echo "FAILED: $ERRORS error(s)"
  exit 1
fi

echo "All public-repository boundary tests passed!"
