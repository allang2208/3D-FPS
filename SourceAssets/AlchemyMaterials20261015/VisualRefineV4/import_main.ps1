param()
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskProject='D:/FPS3D/FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPreviousSdkSkip=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch mutex unavailable; candidates preserved'}
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject") })
    if($taskEditors.Count -gt 0){throw 'Preserve active project editor; use its batch bridge instead'}
    $taskBackup=Join-Path $taskRoot 'Before/MainPreInstall'
    New-Item -ItemType Directory -Path $taskBackup -Force | Out-Null
    foreach($taskName in @('SM_Alchemy_CompoundStabilizer','SM_Alchemy_ActiveCatalyst','SM_Alchemy_BluemarrowCrystals')) {
        $taskSource=Join-Path $taskProject ("Content/Items/AlchemyMaterials20261015/V3/Meshes/$taskName.uasset")
        $taskTarget=Join-Path $taskBackup ("$taskName.uasset")
        if(-not(Test-Path -LiteralPath $taskTarget)){Copy-Item -LiteralPath $taskSource -Destination $taskTarget}
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" '-run=pythonscript' "-script=$taskRoot/Scripts/import_assets.py" '-LiveCoding=false' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$taskRoot/Receipts/main-import.log" *> "$taskRoot/Receipts/main-import-stdout.log"
    $taskExit=$LASTEXITCODE
    Write-Output "ALCHEMY_REFINEMENT_IMPORT_EXIT=$taskExit"
    Select-String -LiteralPath "$taskRoot/Receipts/main-import-stdout.log" -Pattern 'ALCHEMY_ASSET_SAVED|ALCHEMY_IMPORT_COMPLETE|Error:|Traceback' | Select-Object -Last 12
    exit $taskExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSdkSkip
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
