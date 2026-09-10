param(
    [ValidateSet('Normandy', 'MilitaryTrench')]
    [string]$Scene = 'MilitaryTrench'
)
$ErrorActionPreference = 'Stop'
$maps = @{
    Normandy = '/Game/GameMaps/L_Normandy_FPS_Test'
    MilitaryTrench = '/Game/GameMaps/L_MilitaryTrench_FPS_Test'
}
$project = 'D:\FPS3D\FPSGAME\FPSGAME.uproject'
$engine = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$mapFile = 'D:\FPS3D\FPSGAME\Content\' + $maps[$Scene].Substring(6).Replace('/', '\') + '.umap'
if (-not (Test-Path -LiteralPath $mapFile)) { throw "Test map not found: $mapFile" }
Start-Process -FilePath $engine -ArgumentList "`"$project`" $($maps[$Scene]) -game -windowed -ResX=1280 -ResY=720 -nosplash -abslog=`"D:\FPS3D\FPSGAME\Saved\SceneTests\$Scene-runtime.log`""
