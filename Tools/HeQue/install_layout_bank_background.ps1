param([switch]$ContinueValidation)
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$layoutRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\DungeonE2E\Records'
$layoutMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$layoutHeld=$false
try {
    while(-not $layoutHeld) {
        try{$layoutHeld=$layoutMutex.WaitOne(5000)}catch [Threading.AbandonedMutexException]{$layoutHeld=$true}
    }
    while($true) {
        $layoutBusy=@(Get-CimInstance Win32_Process | Where-Object {
            # A Game executable build does not replace the Editor module read here.
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject')
        })
        if(-not $layoutBusy.Count){break}
        Start-Sleep -Seconds 3
    }
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'}){throw 'Editor reopened; preserve loaded assets.'}
    Write-Output 'LAYOUT_BANK_INSTALL_STARTED'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript -script=D:\FPS3D\FPSGAME\Tools\HeQue\install_validated_layout_bank.py -nullrhi -unattended -nop4 -nosplash "-abslog=$layoutRoot\layout-bank-install.log" *> "$layoutRoot\layout-bank-install-stdout.log"
    Write-Output "LAYOUT_BANK_INSTALL_EXIT=$LASTEXITCODE"
    if($LASTEXITCODE -ne 0){throw 'Layout bank install failed; inspect the scoped logs.'}
    Get-Content -LiteralPath "$layoutRoot\layout-bank-install.json"
    if($ContinueValidation){& "$PSScriptRoot\run_dungeon_validation.ps1"}
} finally {
    if($layoutHeld){$layoutMutex.ReleaseMutex()}
    $layoutMutex.Dispose()
}
