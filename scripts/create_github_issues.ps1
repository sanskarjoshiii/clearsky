# Create GitHub issues from docs/issues/*.md (front matter: title, assignee, labels).
#
# Usage (PowerShell, repo root):
#   $env:GITHUB_TOKEN = "<token>"      # fine-grained token with Issues: Read and write on the repo
#   .\scripts\create_github_issues.ps1                 # default repo sanskarjoshiii/clearsky
#   .\scripts\create_github_issues.ps1 -DryRun         # print what would be created
#
# Assignees must be collaborators on the repo; if GitHub refuses one, the issue is created
# unassigned and a warning is printed. Issues whose title already exists (open) are skipped.
param(
    [string]$Repo = "sanskarjoshiii/clearsky",
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$token = if ($env:GITHUB_TOKEN) { $env:GITHUB_TOKEN } else { $env:GH_TOKEN }
if (-not $token -and -not $DryRun) { throw "Set `$env:GITHUB_TOKEN (Issues: read & write on $Repo) first." }
$headers = @{ Authorization = "Bearer $token"; Accept = "application/vnd.github+json"; "X-GitHub-Api-Version" = "2022-11-28" }
$api = "https://api.github.com/repos/$Repo"

function Send-Json([string]$Method, [string]$Url, $Body) {
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Depth 5))
    Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes
}

function Read-Issue([string]$Path) {
    $text = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8)
    if ($text -notmatch '(?s)^---\r?\n(.*?)\r?\n---\r?\n(.*)$') { throw "No front matter in $Path" }
    $meta = $Matches[1]; $body = $Matches[2].Trim()
    $title = if ($meta -match '(?m)^title:\s*"?(.*?)"?\s*$') { $Matches[1] } else { throw "No title in $Path" }
    $assignee = if ($meta -match '(?m)^assignee:\s*(\S+)') { $Matches[1] } else { $null }
    $labels = @()
    if ($meta -match '(?m)^labels:\s*\[(.*)\]') { $labels = $Matches[1].Split(",") | ForEach-Object { $_.Trim().Trim('"') } | Where-Object { $_ } }
    [pscustomobject]@{ Title = $title; Assignee = $assignee; Labels = $labels; Body = $body }
}

$issues = Get-ChildItem (Join-Path $root "docs\issues") -Filter *.md | Sort-Object Name | ForEach-Object { Read-Issue $_.FullName }
if ($DryRun) {
    $issues | ForEach-Object { "{0}  ->  @{1}  [{2}]" -f $_.Title, $_.Assignee, ($_.Labels -join ", ") }
    return
}

$existing = @(Invoke-RestMethod -Uri "$api/issues?state=open&per_page=100" -Headers $headers | ForEach-Object { $_.title })
$labelsNeeded = $issues | ForEach-Object { $_.Labels } | Sort-Object -Unique
foreach ($l in $labelsNeeded) {
    try { Send-Json POST "$api/labels" @{ name = $l; color = "ededed" } | Out-Null; "label created: $l" }
    catch { if ($_.Exception.Response.StatusCode.value__ -ne 422) { throw } }   # 422 = already exists
}

foreach ($i in $issues) {
    if ($existing -contains $i.Title) { "skip (already open): $($i.Title)"; continue }
    $payload = @{ title = $i.Title; body = $i.Body; labels = $i.Labels }
    if ($i.Assignee) { $payload.assignees = @($i.Assignee) }
    try {
        $created = Send-Json POST "$api/issues" $payload
    } catch {
        if ($i.Assignee -and $_.Exception.Response.StatusCode.value__ -eq 422) {
            Write-Warning "GitHub refused assignee @$($i.Assignee) (not a collaborator yet?). Creating unassigned."
            $payload.Remove("assignees")
            $created = Send-Json POST "$api/issues" $payload
        } else { throw }
    }
    "created #$($created.number): $($created.title)  ->  $($created.html_url)"
}
