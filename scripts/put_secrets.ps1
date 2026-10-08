# Copy secrets from .env into SSM Parameter Store SecureStrings under /clearsky/{STAGE}/... (Windows).
# Usage (PowerShell, repo root):  .\scripts\put_secrets.ps1
# Only non-empty values are written; existing parameters are overwritten. Needs the AWS CLI with
# credentials for the target account ($env:AWS_PROFILE if you use a named profile).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) { throw "No .env found at $envFile (copy .env.example)" }

$values = @{}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$') { $values[$Matches[1]] = $Matches[2].Trim('"') }
}
$stage = if ($values["STAGE"]) { $values["STAGE"] } else { "dev" }
$region = if ($values["AWS_REGION"]) { $values["AWS_REGION"] } else { "ap-south-1" }

$paths = [ordered]@{
    "WA_PHONE_NUMBER_ID" = "wa/phone_number_id"
    "WA_ACCESS_TOKEN"    = "wa/access_token"
    "WA_APP_SECRET"      = "wa/app_secret"
    "WA_VERIFY_TOKEN"    = "wa/verify_token"
    "FIRMS_MAP_KEY"      = "firms/map_key"
    "LLM_API_KEY"        = "llm/api_key"
    "STT_API_KEY"        = "stt/api_key"
}
foreach ($name in $paths.Keys) {
    $value = $values[$name]
    $param = "/clearsky/$stage/$($paths[$name])"
    if (-not $value) { Write-Output "skip  $name (empty)"; continue }
    aws ssm put-parameter --region $region --name $param --type SecureString --value $value --overwrite | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "failed to write $param" }
    Write-Output "wrote $param"
}
