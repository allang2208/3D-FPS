param([string]$Label='final',[switch]$Readback)
$ErrorActionPreference='Stop'
if($Label -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Use a simple unique label'}
$qbzRoot='D:/FPS3D/FPSGAME'
$qbzLog="$qbzRoot/SourceAssets/QBZ19120260912/runtime-$Label$(if($Readback){'-readback'}).log"
$qbzArgs=@("$qbzRoot/FPSGAME.uproject",'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation','-game','-windowed','-RenderOffscreen','-ResX=960','-ResY=540','-unattended','-nosplash','-d3d11','-QBZ191IntegrationAudit',"-QBZ191Run=$Label","-ColdSteelProfile=QBZ191IntegrationAudit_$Label",'-ExecCmds="t.MaxFPS 60"',('-abslog="'+$qbzLog+'"'))
if($Readback){$qbzArgs+='-QBZ191Readback'}
$qbzProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $qbzArgs -WindowStyle Hidden -PassThru
"QBZ validation PID $($qbzProcess.Id) log $qbzLog"
