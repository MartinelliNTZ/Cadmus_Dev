# Descobre a pasta do script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Sobe duas pastas
$targetDir = Resolve-Path "$scriptDir\..\.."

Write-Host "Cleaning project at $targetDir"

# ------------------------------------------------------------------
# Remove caches Python
# ------------------------------------------------------------------

Get-ChildItem -Path $targetDir -Directory -Recurse -Filter "__pycache__" |
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Get-ChildItem -Path $targetDir -Recurse -Filter "*.pyc" |
Remove-Item -Force -ErrorAction SilentlyContinue

# ------------------------------------------------------------------
# Git safe cleanup
# ------------------------------------------------------------------

Set-Location $targetDir

if (Test-Path ".git") {

    Write-Host "Running safe git cleanup..."

    # Remove objetos órfãos já compactados
    git gc --auto

    # Remove arquivos temporários internos do git
    git prune-packed

    Write-Host "Git cleanup finished."
}

Write-Host "Cleanup completed."