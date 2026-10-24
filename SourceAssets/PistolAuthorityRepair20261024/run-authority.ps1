param([string]$Name=('authority-'+(Get-Date -Format 'yyyyMMdd-HHmmss')),[string]$Project='D:/FPS3D/FPSGAME/SourceAssets/PistolRepair20261022/RuntimeBuilt28/FPSGAME.uproject')
$ErrorActionPreference='Stop'
$ammoGate=[Threading.Mutex]::new($false,'Local\CodexPistolReadOnly20261022')
$ammoHeld=$false
try {
    try {$ammoHeld=$ammoGate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$ammoHeld=$true}
    if(-not $ammoHeld){throw 'Isolated review is busy.'}
    if(Test-Path -LiteralPath "$PSScriptRoot/$Name.json"){throw 'Use a new evidence name.'}
    $ammoDeadline=(Get-Date).AddMinutes(20)
    while($true){
        $ammoMemory=Get-CimInstance Win32_OperatingSystem
        if($ammoMemory.FreePhysicalMemory -gt 4GB/1KB -and $ammoMemory.FreeVirtualMemory -gt 8GB/1KB){break}
        if((Get-Date) -gt $ammoDeadline){throw 'Insufficient memory for isolated authority review.'}
        Start-Sleep -Seconds 5
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $Project -run=ShotgunAttachmentAudit -PistolAmmo -unattended -nop4 -nosplash -nullrhi -nosound '-DDC=(EnginePak=InstalledEnginePak,WarmRead=(Type=FileSystem,Path=D:/FPS3D/DerivedDataCache,ReadOnly=true,DeleteUnused=false,PromptIfMissing=false),Local=(Type=FileSystem,Path=D:/FPS3D/FPSGAME/SourceAssets/PistolRepair20261022/DDC,DeleteUnused=false,PromptIfMissing=false))' '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-Output=$PSScriptRoot/$Name.json" "-abslog=$PSScriptRoot/$Name.log" *> "$PSScriptRoot/$Name-console.log"
    $ammoExit=$LASTEXITCODE
    @{exit=$ammoExit;project=$Project;finished=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/$Name-exit.json" -Encoding utf8
    Write-Output "PISTOL_AUTHORITY_EXIT=$ammoExit"
    exit $ammoExit
} finally {if($ammoHeld){$ammoGate.ReleaseMutex()};$ammoGate.Dispose()}
