# PowerShell script to analyze C:\Users disk space
Write-Host "=== C:\Users Drive Space Analysis ===" -ForegroundColor Cyan

# Check total drive space
$driveInfo = Get-Volume -DriveLetter 'C'
Write-Host "Total Space: $($driveInfo.TotalCapacity / 1GB | Format -C2) GB" -ForegroundColor Yellow
Write-Host "Free Space: $($driveInfo.FreeSpace / 1GB | Format -C2) GB" -ForegroundColor Red
Write-Host "Used: $($driveInfo.TotalCapacity / 1GB | Format -C2 -A -B) GB" -ForegroundColor Red

Write-Host "`n=== Largest Users ===" -ForegroundColor Cyan

# Get all user directories and sort by size
$userDirs = Get-ChildItem 'C:\Users' -Directory | Where-Object { $_.Name -ne '$' }
$userDirs | ForEach-Object {
    $totalSize = (Get-ChildItem $_.FullName -File -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    [Math]::Round($totalSize / 1GB, 2)
} | Sort-Object -Descending | Select-Object -First 5 | ForEach-Object {
    $name = $_.FullName.Substring(12)
    $size = $_
    Write-Host "$($name): $size GB" -ForegroundColor Yellow
}

Write-Host "`n=== Largest Individual Files (in C:\Users) ===" -ForegroundColor Cyan

# Get largest files
$largeFiles = Get-ChildItem 'C:\Users' -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 1GB } | Sort-Object -Property Length -Descending
$largeFiles | Select-Object -First 10 | ForEach-Object {
    $name = $_.Name
    $size = [Math]::Round($_.Length / 1GB, 2)
    $path = $_.FullName.Substring(12)
    Write-Host "$size GB - $($name) in $path" -ForegroundColor Yellow
}

Write-Host "`n=== Top Categories by Size ===" -ForegroundColor Cyan

# Analyze specific common folders
$foldersToCheck = @('Downloads', 'Documents', 'Pictures', 'Music', 'Videos', 'Desktop', 'AppData', 'AppData\Local', 'AppData\Roaming')
foreach ($folder in $foldersToCheck) {
    $folderPath = "C:\Users\Public\${folder}" + (if ($folder -eq 'AppData' -or $folder -eq 'AppData\Local' -or $folder -eq 'AppData\Roaming') { "\Local\Temp" } else { "" })
    $folderPath = "C:\Users" + (if ($folder -eq 'AppData') { "\Public" + (if ($folder -eq 'AppData') { "" } else { (if ($folder -eq 'AppData\Local') { "\Local" } else { "\Roaming" }) } else { ""}) } else { ""})
    
    try {
        $files = Get-ChildItem -Path $folderPath -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 0 }
        if ($files.Count -gt 0) {
            $totalSize = ($files | Measure-Object -Property Length -Sum).Sum
            $sizeGB = [Math]::Round($totalSize / 1GB, 2)
            Write-Host "${folder}: $sizeGB GB" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "${folder}: Not accessible or error" -ForegroundColor Red
    }
}

Write-Host "`n=== Temporary Files Check ===" -ForegroundColor Cyan

# Check temp directories
$tempDirs = @('C:\Users\Public\Temp', 'C:\Windows\Temp', 'C:\Windows\Temp', 'C:\Users\Default\AppData\Local\Temp')
foreach ($tempDir in $tempDirs) {
    try {
        $files = Get-ChildItem -Path $tempDir -File -Recurse -ErrorAction SilentlyContinue
        $totalSize = ($files | Measure-Object -Property Length -Sum).Sum
        $sizeGB = [Math]::Round($totalSize / 1GB, 2)
        if ($sizeGB -gt 0.1) {
            Write-Host "${tempDir}: $sizeGB GB" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "${tempDir}: Not accessible or error" -ForegroundColor Red
    }
}

Write-Host "`n=== Storage Recommendations ===" -ForegroundColor Cyan
Write-Host "1. Clear Downloads folder" -ForegroundColor White
Write-Host "2. Empty Recycle Bin" -ForegroundColor White
Write-Host "3. Clean temporary files (temp directory)" -ForegroundColor White
Write-Host "4. Remove old browser cache" -ForegroundColor White
Write-Host "5. Check for duplicate photos/videos" -ForegroundColor White
Write-Host "6. Move large files to D: or E: drives" -ForegroundColor White

Write-Host "`n=== Quick Cleanup Command ===" -ForegroundColor Cyan
Write-Host "Run this to clean temp files:" -ForegroundColor Yellow
Write-Host "powerShell -Command 'Get-ChildItem C:\Windows\Temp\*.tmp | Remove-Item'" -ForegroundColor Yellow
Write-Host "powerShell -Command 'Get-ChildItem C:\Users\Temp\*.tmp | Remove-Item'" -ForegroundColor Yellow

Write-Host "`nAnalysis complete!" -ForegroundColor Green
