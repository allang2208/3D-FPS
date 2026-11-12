$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$previous=Join-Path $PSScriptRoot '../Wrist34'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'Existing UE batch retained'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"){throw 'Existing editor retained'}
    & "$root/Tools/Build/Build-Editor.ps1" *> "$PSScriptRoot/build.console.log"
    if(-not $? -or $LASTEXITCODE -ne 0){throw 'Editor build failed'}
    & "$previous/run.ps1" -Script '../Wrist35/install.py'
    & "$previous/run-native.ps1" -Mode geometry -Label 'visual_wrist_closeup' -Manifest 'VisualReview/manifest_wrist_closeup.json'
    & "$previous/VisualReview/run.ps1" -SkipBuild -PrismOnly
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
