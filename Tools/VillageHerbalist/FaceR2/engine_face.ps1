param([Parameter(Mandatory=$true)][ValidateSet('before','after','publish')][string]$Stage)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$review = Join-Path $project 'Saved/HerbalistFaceReview'
$studio = Join-Path $review 'Studio'
$descriptor = Join-Path $studio 'HerbalistFace.uproject'
$commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$stamp = [Guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Path $review -Force | Out-Null
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$env:HERBALIST_FACE_STAGE = $Stage
$mutexName = if ($Stage -eq 'publish') { 'Local\CodexUeMcp-Port-8000' } else { 'Local\FPSGAME-HerbalistFaceStudio' }
$gate = [Threading.Mutex]::new($false,$mutexName)
$held = $false
try {
    try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    if ($Stage -eq 'publish') {
        $scriptFile = Join-Path $PSScriptRoot 'publish_textures.py'
        $editor = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
            $_.CommandLine -match '(?i)FPSGAME[.]uproject'
        })
        if ($editor.Count -gt 0) {
            # Call the bridge in this PowerShell instance so the named mutex is re-entrant.
            & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $scriptFile -QueueWaitSeconds 300 -OutputFile "$review/publish-$stamp.log" -MaxOutputChars 3000
        } else {
            & $commandlet "$project/FPSGAME.uproject" -run=pythonscript "-script=$scriptFile" -unattended -nosplash -nop4 -nosound -NullRHI -Multiprocess -asynctexturecompilation=0 "-abslog=$review/publish-$stamp.log" *> "$review/publish-$stamp.console.log"
        }
        if ($LASTEXITCODE -ne 0) { throw "Herbalist texture publish failed. See $review/publish-$stamp.log" }
        return
    }
    $src = Join-Path $project 'Content/Characters/VillageHerbalist'
    $dst = Join-Path $studio 'Content/Characters/VillageHerbalist'
    New-Item -ItemType Directory -Path $dst,"$studio/Config" -Force | Out-Null
    foreach ($file in (Get-ChildItem -LiteralPath $src -Recurse -File)) {
        $relative = $file.FullName.Substring($src.Length).TrimStart('\','/')
        $to = Join-Path $dst $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $to) -Force | Out-Null
        $snapshotHash = (Get-FileHash -LiteralPath $file.FullName).Hash
        [IO.File]::Copy($file.FullName, $to, $true)
        if ((Get-FileHash -LiteralPath $to).Hash -ne $snapshotHash) { throw "Package changed during studio snapshot: $relative" }
    }
    # The studio uses only verified package copies. Hold its own lock until its render finishes.
    @{FileVersion=3; EngineAssociation='5.8'; Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
        ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $descriptor -Encoding ascii
    @('[/Script/Engine.RendererSettings]','r.Substrate=True','r.Substrate.ProjectGBufferFormat=0',
      '[/Script/WindowsTargetPlatform.WindowsTargetSettings]','DefaultGraphicsRHI=DefaultGraphicsRHI_DX12',
      '-D3D12TargetedShaderFormats=PCD3D_SM5','+D3D12TargetedShaderFormats=PCD3D_SM6') |
        Set-Content -LiteralPath "$studio/Config/DefaultEngine.ini" -Encoding ascii
    & $commandlet $descriptor -run=pythonscript "-script=$PSScriptRoot/engine_face.py" -unattended -nosplash -nop4 -nosound -Multiprocess -AllowCommandletRendering -RenderOffscreen -dx12 -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$review/$Stage-$stamp.log" *> "$review/$Stage-$stamp.console.log"
    if ($LASTEXITCODE -ne 0) { throw "Portrait failed. See $review/$Stage-$stamp.log" }
    Write-Output "$review/ue-$Stage.png"
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
