param(
    [switch]$Continue,
    [Nullable[int]]$Seed
)
$ErrorActionPreference='Stop'
$engine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$project='D:/FPS3D/FPSGAME/FPSGAME.uproject'
$map='/Game/GameMaps/L_TemperateHills_Initial'
if(-not (Test-Path -LiteralPath 'D:/FPS3D/FPSGAME/Content/GameMaps/L_TemperateHills_Initial.umap')){throw 'Build the initial hills map with build_temperate_hills.py first.'}
$argsList=@('"'+$project+'"',$map,'-game','-multiprocess','-windowed','-ResX=1600','-ResY=900','-nosplash','-ColdSteelProfile=TemperateHillsStudy','-abslog="D:/FPS3D/FPSGAME/Saved/TemperateHills-play.log"')
if($null -ne $Seed){$argsList+='-HillsSeed='+$Seed}
elseif(-not $Continue){$argsList+='-HillsNewWorld'}
# This launcher intentionally opens the interactive test game requested by the user.
Start-Process -FilePath $engine -ArgumentList ($argsList -join ' ')
