$ErrorActionPreference='Stop'
$taskDir='D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualPersistentLeaves20261016'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$readingFitPreviousSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    while (!$held) {
        try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(45))} catch [Threading.AbandonedMutexException] {$held=$true}
        if (!$held) {Write-Output 'Waiting for the shared UE batch.'}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/SourceAssets/PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost/PotionWorkbenchImport.uproject' '-run=pythonscript' "-script=$taskDir/import_assets.py" '-unattended' '-nop4' '-nosplash' '-AllowCommandletRendering' '-RenderOffscreen' '-nosound' "-abslog=$taskDir/import.log" *> "$taskDir/import-console.log"
    if ($LASTEXITCODE -ne 0) {throw 'Asset import failed; see import.log'}
    & 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' "$taskDir/install_assets.py"
    if ($LASTEXITCODE -ne 0) {throw 'Asset installation failed'}
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$readingFitPreviousSdk;if ($held) {$gate.ReleaseMutex()};$gate.Dispose()}
