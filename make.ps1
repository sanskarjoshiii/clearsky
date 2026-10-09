# clearsky monorepo commands for Windows (same targets as the Makefile).
#   .\make.ps1 test        .\make.ps1 chat        .\make.ps1 deploy -Confirm yes
param(
    [Parameter(Position = 0)][string]$Target = "help",
    [string]$Confirm = "",
    [string]$ChatArgs = "--local --debug"
)
# Native tools (uv, sam) write progress to stderr; Windows PowerShell 5.1 would treat that as a failure
# under "Stop". Success is decided by exit codes instead (see the throws below).
$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot

# Resolve uv once: the `uv` binary if on PATH, else `python -m uv` via the current python's full path
# (so changing PATH later can't make `python` point at an interpreter without uv).
$UvCmd = @()
if (Get-Command uv -ErrorAction SilentlyContinue) { $UvCmd = @((Get-Command uv).Source) }
else { $UvCmd = @((Get-Command python).Source, "-m", "uv") }

function Uv([string[]]$UvArgs) {
    $exe = $UvCmd[0]; $pre = @($UvCmd | Select-Object -Skip 1)
    & $exe @pre @UvArgs
}

function Invoke-Uv([string[]]$UvArgs) {
    Push-Location (Join-Path $Root "backend")
    try {
        Uv $UvArgs
        if ($LASTEXITCODE -ne 0) { throw "uv $($UvArgs -join ' ') failed ($LASTEXITCODE)" }
    } finally { Pop-Location }
}

function Invoke-Sam([string[]]$SamArgs) {
    Push-Location (Join-Path $Root "infra")
    $oldPath = $env:Path
    try {
        # `sam build` needs a python3.12 with pip on PATH (the Lambda runtime). Use uv's managed 3.12.
        $py312 = Uv @("python", "find", "3.12")
        if ($LASTEXITCODE -eq 0 -and $py312) { $env:Path = (Split-Path "$py312".Trim()) + ";" + $env:Path }
        $env:SAM_CLI_TELEMETRY = "0"
        if (Get-Command sam -ErrorAction SilentlyContinue) { & sam @SamArgs }
        else { Uv (@("tool", "run", "--from", "aws-sam-cli", "sam") + $SamArgs) }
        if ($LASTEXITCODE -ne 0) { throw "sam $($SamArgs -join ' ') failed ($LASTEXITCODE)" }
    } finally { $env:Path = $oldPath; Pop-Location }
}

# Dependencies are resolved and installed for the Lambda target (Linux arm64, Python 3.12) into a layer,
# so host-only packages (e.g. pywin32 on Windows) never leak in and SAM only copies our source.
$LambdaPlatform = @("--python-version", "3.12", "--python-platform", "aarch64-manylinux_2_28")
function Build-Layer {
    Invoke-Uv (@("pip", "compile", "pyproject.toml") + $LambdaPlatform + @("--no-header", "--no-annotate", "--quiet", "-o", "requirements-lambda.txt"))
    $layer = Join-Path $Root "infra\.layer"
    if (Test-Path $layer) { Remove-Item -Recurse -Force $layer }
    Invoke-Uv (@("pip", "install", "-r", "requirements-lambda.txt", "--target", "../infra/.layer/python") + $LambdaPlatform + @("--only-binary", ":all:", "--quiet"))
}

switch ($Target) {
    "install" { Invoke-Uv @("sync") }
    "lint" {
        Invoke-Uv @("run", "ruff", "check", "src", "tests", "scripts")
        Invoke-Uv @("run", "ruff", "format", "--check", "src", "tests", "scripts")
        Invoke-Uv @("run", "mypy")
    }
    "format" {
        Invoke-Uv @("run", "ruff", "check", "--fix", "src", "tests", "scripts")
        Invoke-Uv @("run", "ruff", "format", "src", "tests", "scripts")
    }
    "test" { Invoke-Uv @("run", "pytest") }
    "cov" { Invoke-Uv @("run", "pytest", "--cov=clearsky", "--cov-report=term-missing:skip-covered") }
    "layer" { Build-Layer }
    "build" { Build-Layer; Invoke-Sam @("build") }
    "validate" { Invoke-Sam @("validate", "--lint") }
    "deploy" {
        if ($Confirm -ne "yes") { throw "Refusing to deploy without -Confirm yes (team approval required)." }
        Invoke-Sam @("build"); Invoke-Sam @("deploy")
    }
    "gen-seed" { Invoke-Uv @("run", "python", "scripts/gen_seed.py", "--seed", "42") }
    "seed" {
        Invoke-Uv @("run", "python", "scripts/gen_seed.py", "--seed", "42")
        Invoke-Uv @("run", "python", "scripts/seed_dynamo.py", "--reset", "--set-clock")
    }
    "chat" { Invoke-Uv (@("run", "python", "scripts/chat_cli.py") + ($ChatArgs -split " ")) }
    "book-all" { Invoke-Uv @("run", "python", "scripts/book_all.py", "--local", "--dry-run") }
    "firms" { Invoke-Uv @("run", "python", "scripts/fetch_firms.py", "--apply-seed") }
    "check-aws" { Invoke-Uv @("run", "python", "scripts/check_aws.py") }
    "dev" { Invoke-Uv @("run", "python", "scripts/dev_server.py") }
    "dashboard" { Push-Location (Join-Path $Root "dashboard"); try { npm install; npm run dev } finally { Pop-Location } }
    "e2e" {
        Push-Location (Join-Path $Root "dashboard")
        try { if (-not $env:CLEARSKY_API_CMD -and -not (Get-Command uv -ErrorAction SilentlyContinue)) { $env:CLEARSKY_API_CMD = "python -m uv run python scripts/dev_server.py" }; npm run typecheck; npm test; npx playwright test }
        finally { Pop-Location }
    }
    default { Write-Output "targets: install lint format test cov layer build validate deploy gen-seed seed chat book-all firms check-aws dev dashboard e2e" }
}
