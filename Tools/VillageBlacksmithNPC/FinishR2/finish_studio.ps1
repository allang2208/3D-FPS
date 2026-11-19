$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$name='Characters/VillageBlacksmithNPC20261118'
$base="$project/SourceAssets/VillageBlacksmithNPC20261118"
$out="$base/FinishR2/Review"
$stage="$out/ShaderHost"
$mats=@('BodyOutfit/Materials/M_Smith_Apron','HeadParts/M_Smith_NativeNeck','HeadFinishR2/M_Smith_MeshyFace_R2')
$hash=@{}
foreach($mat in $mats){
    $src="$project/Content/$name/$mat.uasset"
    $dst="$stage/Content/$name/$mat.uasset"
    New-Item -ItemType Directory -Force (Split-Path -Parent $dst)|Out-Null
    $hash[$mat]=(Get-FileHash -LiteralPath $src).Hash
    Copy-Item -LiteralPath $src -Destination $dst -Force
}
foreach($rel in @('AsianMale_Jason',"$name/BodyOutfit/SurfaceR2","$name/BodyOutfit/Textures","$name/HeadParts/Textures","$name/HeadFinishR2/Textures")){
    $dst="$stage/Content/$rel"
    if(-not (Test-Path -LiteralPath $dst)){New-Item -ItemType Junction -Path $dst -Target "$project/Content/$rel" | Out-Null}
}
Copy-Item -LiteralPath "$base/FinishR2/HeadHair/Host/SmithHead.uproject" -Destination "$stage/SmithHead.uproject" -Force
New-Item -ItemType Directory -Force "$stage/Config"|Out-Null
Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Value @('[/Script/Engine.RendererSettings]','r.Substrate=True','r.Substrate.ProjectGBufferFormat=0','[/Script/WindowsTargetPlatform.WindowsTargetSettings]','DefaultGraphicsRHI=DefaultGraphicsRHI_DX12','-D3D12TargetedShaderFormats=PCD3D_SM5','+D3D12TargetedShaderFormats=PCD3D_SM6') -Encoding ascii
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$stage/SmithHead.uproject" -run=pythonscript "-script=$PSScriptRoot/studio_material_finish.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$out/studio_shader.log" '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' *> "$out/studio_shader.console.log"
if($LASTEXITCODE -ne 0){throw "Material commandlet failed $LASTEXITCODE"}
$guard=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$guard.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    foreach($mat in $mats){
        $dst="$project/Content/$name/$mat.uasset"
        if((Get-FileHash -LiteralPath $dst).Hash -ne $hash[$mat]){throw "Material updated during authoring: $mat"}
    }
    $installed=@{}
    foreach($mat in $mats){
        $src="$stage/Content/$name/$mat.uasset"
        $dst="$project/Content/$name/$mat.uasset"
        [IO.File]::Copy($src,"$dst.closeup.tmp",$true)
        [IO.File]::Move("$dst.closeup.tmp",$dst,$true)
        $installed[$mat]=(Get-FileHash -LiteralPath $dst).Hash
    }
    $installed|ConvertTo-Json|Set-Content "$out/studio_materials_installed.json" -Encoding utf8
}finally{if($held){$guard.ReleaseMutex()};$guard.Dispose()}
