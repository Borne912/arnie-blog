# Requires Windows PowerShell 5.1 or PowerShell 7, Windows OpenSSH and curl.exe.
[CmdletBinding()]
param(
    [ValidateSet('check', 'install', 'https', 'report')]
    [string]$Action = 'check',
    [switch]$Direct
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$stileBundle = $PSScriptRoot

try {
    foreach ($stileCommand in @('ssh.exe', 'scp.exe')) {
        if (-not (Get-Command $stileCommand -CommandType Application -ErrorAction SilentlyContinue)) {
            throw "Missing $stileCommand. Install the Windows OpenSSH Client optional feature."
        }
    }
    if ($Action -in @('install', 'https')) {
        if (-not (Get-Command 'curl.exe' -CommandType Application -ErrorAction SilentlyContinue)) {
            throw 'Missing curl.exe. Use an up-to-date Windows 10/11 installation.'
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $stileBundle 'server.py') -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $stileBundle 'deploy-settings.json') -PathType Leaf)) {
        throw 'Extract the complete deployment ZIP before running this script.'
    }

    $stileTarget = 'BWG'
    $stileSshOptions = @()
    $stileScpOptions = @()
    if ($Direct) {
        $stileTarget = 'Borne@199.168.136.75'
        $stileSshOptions = @('-p', '2912')
        $stileScpOptions = @('-P', '2912')
    }

    $stileConfigLines = @(& ssh.exe -G @stileSshOptions $stileTarget)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to read the SSH configuration.' }
    $stileConfig = @{}
    foreach ($stileLine in $stileConfigLines) {
        if ($stileLine -match '^\s*(hostname|user|port)\s+(\S+)\s*$') {
            $stileConfig[$Matches[1].ToLowerInvariant()] = $Matches[2]
        }
    }
    if ($stileConfig['hostname'] -ne '199.168.136.75' -or
        $stileConfig['user'] -cne 'Borne' -or $stileConfig['port'] -ne '2912') {
        throw 'SSH does not resolve to the authorized VPS. Use -Direct if BWG is not configured on Windows.'
    }

    $stileSshOptions += @('-o', 'StrictHostKeyChecking=yes')
    $stileScpOptions += @('-o', 'StrictHostKeyChecking=yes')
    & ssh.exe @stileSshOptions $stileTarget 'install -d -m 0700 ~/stile-page-views-package'
    if ($LASTEXITCODE -ne 0) {
        throw 'SSH failed. First verify that you can log in from this Windows computer.'
    }

    Push-Location -LiteralPath $stileBundle
    try {
        # A relative source avoids confusing the Windows drive letter with an SCP host.
        & scp.exe -q -r @stileScpOptions '.' "${stileTarget}:stile-page-views-package/"
        if ($LASTEXITCODE -ne 0) { throw 'Uploading the deployment package failed.' }

        & ssh.exe -t @stileSshOptions $stileTarget "sudo python3 ~/stile-page-views-package/server.py $Action"
        $stileResult = $LASTEXITCODE
        & scp.exe -q @stileScpOptions "${stileTarget}:stile-page-views-package/deployment-report.json" 'deployment-report.json'
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Deployment report: $(Join-Path $stileBundle 'deployment-report.json')"
        }
        if ($stileResult -ne 0) {
            Write-Host 'Deployment is incomplete. Keep the error and report; do not switch the website API.'
            exit $stileResult
        }
    }
    finally {
        Pop-Location
    }

    if ($Action -in @('install', 'https')) {
        Write-Host 'Checking the public HTTPS API from Windows (read-only):'
        & curl.exe --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 20 `
            -H 'x-bsz-referer: https://stile.cc/' -H 'Origin: https://stile.cc' `
            'https://stats.stile.cc/api'
        if ($LASTEXITCODE -ne 0) { throw 'Public HTTPS verification failed. Keep the output and report.' }
        Write-Host ''
        Write-Host 'Please provide deployment-report.json and the HTTPS response before switching the website API.'
    }
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
