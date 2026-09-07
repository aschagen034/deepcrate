param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$mainPath = Join-Path $projectRoot "main.py"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Virtual-environment Python was not found: $pythonPath"
}

if (-not (Test-Path -LiteralPath $mainPath)) {
    throw "DeepCrate main.py was not found: $mainPath"
}

if ($DryRun) {
    $modeArgument = "--dry-run"
}
else {
    $modeArgument = "--yes"
}

Push-Location $projectRoot

try {
    & $pythonPath $mainPath $modeArgument

    if ($LASTEXITCODE -ne 0) {
        throw "DeepCrate exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}