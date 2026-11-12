param([ValidateSet('native','geometry')][string]$Mode='native',[string]$Label='',[string]$Manifest='manifest_geometry.json')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if(!$Label){$Label=$Mode}
if($Label -notmatch '^[a-z_]+$'){throw 'Invalid output label'}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'Existing UE batch remains busy'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if($busy.Count){throw 'Existing UE or build process retained'}
    if(Test-Path -LiteralPath "$PSScriptRoot/$Label"){throw 'Output already exists'}
    $arguments=@("$project/FPSGAME.uproject",'-unattended','-NoSound','-NoP4','-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',"-abslog=$PSScriptRoot/$Label.log")
    if($Mode -eq 'native'){$arguments+=@('-run=WeaponEquipCameraAudit','-M249Wrist',"-Out=$PSScriptRoot/$Label",'-NullRHI')}
    else{$arguments+=@('-run=M24HoldReview',"-M249ReloadManifest=$PSScriptRoot/$Manifest","-Output=$PSScriptRoot/$Label",'-AllowCommandletRendering','-RenderOffscreen')}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @arguments *> "$PSScriptRoot/$Label.console.log"
    $code=$LASTEXITCODE
    Get-Content -LiteralPath "$PSScriptRoot/$Label.log" -Tail 8
    if($code -ne 0){throw "M249 $Mode review exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
