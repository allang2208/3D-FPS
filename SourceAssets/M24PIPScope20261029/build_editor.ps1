param([switch]$CompileOnly)
$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$m24Held=$false
try {
    Write-Output 'Waiting for the existing UE batch mutex.'
    try {$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}
    catch [Threading.AbandonedMutexException] {$m24Held=$true}
    if(-not $m24Held){throw 'UE batch remains occupied. No process was stopped.'}
    if($CompileOnly){
        # Compile into task-owned files while an editor is open. Do not link or
        # publish mixed old/new class layouts; the full UBT build is still required.
        $m24Module="$m24Root/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME"
        $m24Stage=Join-Path $PSScriptRoot 'Staging'
        [IO.Directory]::CreateDirectory($m24Stage) | Out-Null
        $m24Stage=$m24Stage.Replace('\','/')
        Push-Location -LiteralPath 'E:/Program Files (x86)/UE_5.8/Engine/Source'
        try {
            foreach($m24Unit in @('LPVOScopeWidget.cpp','M24ScopeDrawing.cpp','M4GunsmithVisual.cpp','ScopeOpticalPresentation.cpp')){
                $m24Response=[IO.File]::ReadAllText("$m24Module/$m24Unit.obj.rsp")
                foreach($m24Suffix in @('obj','sarif','dep.json')){
                    $m24Response=$m24Response.Replace("$m24Module/$m24Unit.$m24Suffix","$m24Stage/$m24Unit.$m24Suffix")
                }
                [IO.File]::WriteAllText("$m24Stage/$m24Unit.rsp",$m24Response)
                & 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/cl.exe' "@$m24Stage/$m24Unit.rsp" *> "$m24Stage/compile-$m24Unit.log"
                if($LASTEXITCODE -ne 0){throw "Compile failed: $m24Unit. See $m24Stage/compile-$m24Unit.log"}
                Write-Output "Compiled staged object: $m24Unit"
            }
        } finally {Pop-Location}
        Write-Output 'Source objects staged only. Complete UBT build and DLL publication remain pending.'
        return
    }
    $m24Editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($m24Editors.Count){throw 'Save and close the FPSGAME editor before replacing its modules. No editor was stopped.'}
    $m24Log=Join-Path $PSScriptRoot ('build-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    # UHT and the complete normal dependency graph must process the widget layout change.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$m24Root/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 "-Log=$m24Log"
    if($LASTEXITCODE -ne 0){throw "Editor build failed: $LASTEXITCODE. Log: $m24Log"}
    @{target='FPSGAMEEditor';mode='full-ubt-dependency-graph';exit_code=0;completed=(Get-Date).ToString('o');published=$true;runtime_tested=$false;log=$m24Log;dll="$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll"} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
    Write-Output 'M24 optical scene built into the normal Editor DLL. No editor or game launched.'
} finally {
    if($m24Held){$m24Gate.ReleaseMutex()}
    $m24Gate.Dispose()
}
