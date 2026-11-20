param(
    [switch]$Continue,
    [Nullable[int]]$Seed,
    [ValidateSet(1,2,3)][int]$Gen=3
)
$ErrorActionPreference='Stop'
if($Continue -and $null -ne $Seed){throw '-Continue loads the saved world; do not combine it with -Seed.'}
if($Continue -and $PSBoundParameters.ContainsKey('Gen')){throw '-Continue uses the version stored in the save; do not combine it with -Gen.'}
$worldSave='D:/FPS3D/FPSGAME/Saved/SaveGames/TemperateHills_World.sav'
if($Continue -and -not (Test-Path -LiteralPath $worldSave)){throw '-Continue found no TemperateHills_World.sav; run a new world without -Continue first.'}
$engine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$project='D:/FPS3D/FPSGAME/FPSGAME.uproject'
$map='/Game/GameMaps/L_TemperateHills_Initial'
if($Continue){$map+='?HillsContinue'}
if(-not (Test-Path -LiteralPath 'D:/FPS3D/FPSGAME/Content/GameMaps/L_TemperateHills_Initial.umap')){throw 'Build the initial hills map with build_temperate_hills.py first.'}
$argsList=@('"'+$project+'"',$map,'-game','-multiprocess','-windowed','-ResX=1600','-ResY=900','-nosplash','-ColdSteelProfile=TemperateHillsStudy','-abslog="D:/FPS3D/FPSGAME/Saved/TemperateHills-play.log"')
if($null -ne $Seed){$argsList+='-HillsSeed='+$Seed}
elseif(-not $Continue){$argsList+='-HillsNewWorld'}
if(-not $Continue){$argsList+='-HillsGen='+$Gen}
# This launcher intentionally opens the interactive test game requested by the user.
Start-Process -FilePath $engine -ArgumentList ($argsList -join ' ')
