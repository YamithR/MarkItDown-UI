# MarkItDown-UI Windows build script (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File build-windows.ps1 [-Version 1.1.0]
param(
    [string]$Version = "1.1.0",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

Write-Host "=== MarkItDown-UI Windows Build ===" -ForegroundColor Cyan

if ($Clean) {
    Write-Host "Cleaning previous build artifacts..."
    Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
}

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install pyinstaller

Write-Host "Installing runtime dependencies..."
python -m pip install -r requirements.txt

Write-Host "Pre-downloading EasyOCR models for offline bundling..."
python -c "import easyocr; easyocr.Reader(['en'], gpu=False, model_storage_directory='assets/easyocr_models', download_enabled=True); print('EasyOCR models cached in assets/easyocr_models')"

Write-Host "Building executable with PyInstaller..."
python -m PyInstaller --noconfirm --clean markitdown-ui.spec

if (Test-Path "dist/markitdown-ui.exe") {
    $final = "dist/markitdown-ui-$Version-windows.exe"
    Copy-Item "dist/markitdown-ui.exe" $final
    Write-Host "SUCCESS: $final" -ForegroundColor Green
    Write-Host "SHA256: $((Get-FileHash $final -Algorithm SHA256).Hash)" -ForegroundColor Green
} else {
    Write-Error "Build failed: dist/markitdown-ui.exe not found"
    exit 1
}