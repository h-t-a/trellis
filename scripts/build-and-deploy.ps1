<#
.SYNOPSIS
    Automated Test -> Build Single-File .pyz -> Optional Signed HTTPS Deploy pipeline for trellis-mcp ([REQ-MCP-09, REQ-TRL-20, REQ-TRL-24]).

.DESCRIPTION
    1. Runs the Trellis workspace doctor check (`python -m trellis_mcp --check`).
    2. Runs the full unit & integration test suite (`python -m unittest discover -s tests -v`).
    3. Builds the standalone 1-file bundle (`dist\trellis-mcp.pyz`).
    4. Smoke-tests `dist\trellis-mcp.pyz --version`.
    5. Optionally deploys `dist\trellis-mcp.pyz` over HTTPS via `POST /admin/deploy` using an Admin API key
       (`-ApiKey` / `$env:TRELLIS_API_KEY`) AND a separate deploy signing key
       (`-DeploySigningKey` / `$env:TRELLIS_DEPLOY_SIGNING_KEY`) when the server opts in with `--enable-remote-deploy`.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ServerUrl = "",

    [Parameter(Mandatory = $false)]
    [string]$ApiKey = "",

    [Parameter(Mandatory = $false)]
    [string]$DeploySigningKey = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $RepoRoot

try {
    Write-Host "==> [Step 1/5] Running Trellis Workspace Doctor..." -ForegroundColor Cyan
    python -m trellis_mcp --check
    if ($LASTEXITCODE -ne 0) {
        throw "Workspace doctor check failed. Fix reported issues before building."
    }

    Write-Host "`n==> [Step 2/5] Running Automated Test Suite..." -ForegroundColor Cyan
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Automated tests failed. Aborting build and deployment."
    }

    Write-Host "`n==> [Step 3/5] Building Standalone Single-File Bundle (dist\trellis-mcp.pyz)..." -ForegroundColor Cyan
    $PyzPath = Join-Path $RepoRoot "dist\trellis-mcp.pyz"
    python -m trellis_mcp --build-pyz $PyzPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $PyzPath)) {
        throw "Failed to build $PyzPath."
    }

    Write-Host "`n==> [Step 4/5] Smoke-Testing Standalone Bundle..." -ForegroundColor Cyan
    $VersionOut = python $PyzPath --version
    Write-Host "    Verified artifact: $VersionOut ($PyzPath)" -ForegroundColor Green

    if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
        Write-Host "`n==> [Step 5/5] Local build complete (no -ServerUrl provided)." -ForegroundColor Green
        Write-Host "    Artifact ready at: $PyzPath"
        Write-Host "    To upload over HTTPS when --enable-remote-deploy is enabled:"
        Write-Host "      .\scripts\build-and-deploy.ps1 -ServerUrl https://trellis.example.com -ApiKey `"<ADMIN_KEY>`" -DeploySigningKey `"<DEPLOY_SIGNING_KEY>`""
        return
    }

    if (-not $ServerUrl.StartsWith("https://", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing plaintext remote deploy URL '$ServerUrl'. Use https:// for /admin/deploy."
    }

    $ResolvedKey = if (-not [string]::IsNullOrWhiteSpace($ApiKey)) { $ApiKey.Trim() } elseif ($env:TRELLIS_API_KEY) { $env:TRELLIS_API_KEY.Trim() } else { "" }
    $ResolvedDeployKey = if (-not [string]::IsNullOrWhiteSpace($DeploySigningKey)) { $DeploySigningKey.Trim() } elseif ($env:TRELLIS_DEPLOY_SIGNING_KEY) { $env:TRELLIS_DEPLOY_SIGNING_KEY.Trim() } else { "" }

    if ([string]::IsNullOrWhiteSpace($ResolvedKey) -or [string]::IsNullOrWhiteSpace($ResolvedDeployKey)) {
        throw "Both -ApiKey (TRELLIS_API_KEY) and a separate -DeploySigningKey (TRELLIS_DEPLOY_SIGNING_KEY) are required for /admin/deploy."
    }
    if ($ResolvedKey -eq $ResolvedDeployKey) {
        throw "TRELLIS_DEPLOY_SIGNING_KEY must be distinct from TRELLIS_API_KEY ([REQ-TRL-20])."
    }

    $TargetUrl = "$($ServerUrl.TrimEnd('/'))/admin/deploy"
    Write-Host "`n==> [Step 5/5] Deploying $PyzPath to $TargetUrl..." -ForegroundColor Cyan
    $PyzBytes = [System.IO.File]::ReadAllBytes($PyzPath)
    $Hmac = [System.Security.Cryptography.HMACSHA256]::new()
    $Hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($ResolvedDeployKey)
    $Signature = ([System.BitConverter]::ToString($Hmac.ComputeHash($PyzBytes))).Replace("-", "").ToLowerInvariant()
    $Hmac.Dispose()

    $Headers = @{
        Authorization         = "Bearer $ResolvedKey"
        "X-Trellis-Signature" = $Signature
    }
    $DeployResp = Invoke-RestMethod -Uri $TargetUrl `
        -Method Post -Body $PyzBytes -ContentType "application/octet-stream" `
        -Headers $Headers -TimeoutSec 20
    Write-Host "    HTTPS Deploy Result: $($DeployResp | ConvertTo-Json -Compress)" -ForegroundColor Green
} finally {
    Pop-Location
}
