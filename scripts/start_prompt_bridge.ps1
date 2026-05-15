param(
    [string]$ConfigPath = ".\bridge.config.json"
)

$ErrorActionPreference = "SilentlyContinue"
$script:RepoRoot = Split-Path -Parent $PSScriptRoot
$script:DoneFolder = Join-Path $script:RepoRoot "prompts\done"

function Resolve-BridgePath {
    param([string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }

    return Join-Path $script:RepoRoot $PathValue
}

function Load-Config {
    $resolvedConfigPath = Resolve-BridgePath $ConfigPath
    if (Test-Path $resolvedConfigPath) {
        $config = Get-Content $resolvedConfigPath -Raw | ConvertFrom-Json
        if (
            $null -ne $config -and
            $null -ne $config.poll_seconds -and
            $null -ne $config.auto_open_vscode -and
            $null -ne $config.auto_open_prompt_file -and
            $null -ne $config.copy_to_clipboard -and
            -not [string]::IsNullOrWhiteSpace($config.prompt_folder)
        ) {
            return $config
        }
    }
    return $null
}

function Ensure-DoneFolder {
    if (-not (Test-Path $script:DoneFolder)) {
        New-Item -ItemType Directory -Path $script:DoneFolder | Out-Null
    }
}

function Open-VSCode {
    code $script:RepoRoot
}

function Open-File {
    param($file)
    code (Resolve-Path $file)
}

function Move-PromptToDone {
    param([System.IO.FileInfo]$PromptFile)

    Ensure-DoneFolder

    $destination = Join-Path $script:DoneFolder $PromptFile.Name
    if (Test-Path $destination) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $destination = Join-Path $script:DoneFolder ("{0}_{1}{2}" -f $PromptFile.BaseName, $timestamp, $PromptFile.Extension)
    }

    Move-Item -LiteralPath $PromptFile.FullName -Destination $destination
    return $destination
}

function Get-LatestPrompt($folder) {
    if (-not (Test-Path $folder)) {
        return $null
    }

    Get-ChildItem $folder -Recurse -File |
        Where-Object {
            $_.Extension -in @(".md", ".txt") -and
            $_.BaseName -notmatch "(?i)example|sample|test"
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

$config = Load-Config
if (-not $config) {
    Write-Host "bridge.config.json not found or invalid." -ForegroundColor Red
    exit 1
}

$seen = @{}
Ensure-DoneFolder

while ($true) {
    $pullOutput = git pull 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "==== GIT PULL ERROR ====" -ForegroundColor Red
        $pullOutput | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        Write-Host "========================" -ForegroundColor Red
    }

    $latest = Get-LatestPrompt (Resolve-BridgePath $config.prompt_folder)

    if ($latest -and -not $seen.ContainsKey($latest.FullName)) {
        $content = Get-Content $latest.FullName -Raw
        $seen[$latest.FullName] = $true

        Write-Host ""
        Write-Host "==== NEW PROMPT ====" -ForegroundColor Cyan
        Write-Host $content
        Write-Host "====================" -ForegroundColor Cyan
        Write-Host ""

        if ($config.copy_to_clipboard) {
            Set-Clipboard $content
        }

        if ($config.auto_open_vscode) {
            Open-VSCode
        }

        $donePath = Move-PromptToDone $latest

        if ($config.auto_open_prompt_file) {
            Open-File $donePath
        }
    }

    Start-Sleep -Seconds $config.poll_seconds
}
