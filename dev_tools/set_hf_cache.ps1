# set_hf_cache.ps1
# Sets Hugging Face cache folders for the current user.

$HFCacheRoot = "C:\s3711\.cache\huggingface"
$HFHubCache = Join-Path $HFCacheRoot "hub"

Write-Host "Creating Hugging Face cache folders..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $HFCacheRoot | Out-Null
New-Item -ItemType Directory -Force -Path $HFHubCache | Out-Null

Write-Host "Setting user environment variables..." -ForegroundColor Cyan

[Environment]::SetEnvironmentVariable("HF_HOME", $HFCacheRoot, "User")
[Environment]::SetEnvironmentVariable("HF_HUB_CACHE", $HFHubCache, "User")

Write-Host ""
Write-Host "Hugging Face cache configured:" -ForegroundColor Green
Write-Host "HF_HOME      = $HFCacheRoot"
Write-Host "HF_HUB_CACHE = $HFHubCache"
Write-Host ""
Write-Host "Close and reopen PowerShell for the changes to fully apply." -ForegroundColor Yellow
Write-Host ""

# Also set them for the current PowerShell session immediately.
$env:HF_HOME = $HFCacheRoot
$env:HF_HUB_CACHE = $HFHubCache

Write-Host "Variables also set for this current PowerShell session." -ForegroundColor Green