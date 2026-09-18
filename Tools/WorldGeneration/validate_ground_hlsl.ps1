# Compile every dumped ground-material Custom node with the Windows SDK shader
# compiler. SM5 via fxc and SM6 via dxc, because UE 5.8 ships both feature levels.
$ErrorActionPreference = 'Continue'
$bin = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64'
$fxc = Join-Path $bin 'fxc.exe'
$dxc = Join-Path $bin 'dxc.exe'
$hlsl = 'D:\FPS3D\FPSGAME\Saved\GroundMaterialUpgrade20260918\hlsl'
$log = Join-Path $hlsl 'compile.log'
if (-not (Test-Path $fxc)) { Write-Output ("missing " + $fxc); exit 2 }

$results = @()
foreach ($file in Get-ChildItem -Path $hlsl -Filter *.hlsl | Sort-Object Name) {
    foreach ($target in @(@{ exe = $fxc; args = @('/nologo', '/T', 'ps_5_0'); tag = 'sm5' },
                          @{ exe = $dxc; args = @('-T', 'ps_6_0', '-Wno-ignored-attributes'); tag = 'sm6' })) {
        $out = & $target.exe @($target.args) $file.FullName 2>&1
        $code = $LASTEXITCODE
        $results += [pscustomobject]@{
            file = $file.Name
            target = $target.tag
            exit = $code
            text = ($out | Out-String).Trim()
        }
    }
}
$results | ConvertTo-Json -Depth 4 | Set-Content -Path $log -Encoding UTF8
$failed = @($results | Where-Object { $_.exit -ne 0 })
Write-Output ("checked " + $results.Count + " compiles, failures=" + $failed.Count)
foreach ($f in $failed) {
    Write-Output ("FAIL " + $f.target + " " + $f.file)
    Write-Output ($f.text -split "`n" | Select-Object -First 6 | Out-String)
}
