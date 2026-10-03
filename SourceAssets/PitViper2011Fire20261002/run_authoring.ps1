$ErrorActionPreference = 'Stop'
foreach ($taskFireSide in @('single', 'r', 'l')) {
    $taskFireLog = Join-Path $PSScriptRoot ("author_" + $taskFireSide + '.log')
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --python (Join-Path $PSScriptRoot 'author_fire.py') -- $taskFireSide *> $taskFireLog
    if ($LASTEXITCODE -ne 0) { throw "Fire animation authoring failed: $taskFireSide. Log: $taskFireLog" }
    Write-Output "PIT_VIPER_FIRE_SOURCE_SAVED $taskFireSide"
}
