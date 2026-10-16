"""Freeze an independent native test host while the main editor remains in use."""
from pathlib import Path
import shutil,json,hashlib,datetime
O=Path(__file__).parent;P=O.parents[1];I=Path('D:/FPS3D/ShotgunAttachmentAudit20261016')
I.mkdir(exist_ok=True)
if (I/'Source').exists():raise RuntimeError('Preserve existing audit source snapshot')
shutil.copy2(P/'FPSGAME.uproject',I/'FPSGAME.uproject')
for name in ('Source','Config'):
    shutil.copytree(P/name,I/name)
for plugin in ('AutoFootstep','ColdSteelNet','VoxelFree'):
    shutil.copytree(P/'Plugins'/plugin,I/'Plugins'/plugin,
        ignore=shutil.ignore_patterns('Binaries','Intermediate','Saved','Content','.git'))
owned=['Source/FPSGAME/FPSGAMECharacter.h','Source/FPSGAME/FPSGAMECharacterProfile.cpp',
    'Source/FPSGAME/Weapons/M4MuzzleVisual.cpp','Source/FPSGAME/Multiplayer/ColdSteelSuper90Authority.cpp',
    'Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp','Source/FPSGAME/Weapons/ShotgunAttachmentAuditCommandlet.cpp',
    'Source/FPSGAME/Weapons/ShotgunWireAudit.cpp','Source/FPSGAME/Weapons/ShotgunWireAudit.h']
rows={name:hashlib.sha256((I/name).read_bytes()).hexdigest() for name in owned}
(O/'isolated_snapshot.json').write_text(json.dumps({'project':str(I),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_hashes':rows,'shared_content':str(P/'Content'),'main_editor_modified':False},indent=2),encoding='utf-8')
authority=(O/'run_authority.ps1').read_text(encoding='utf-8-sig').replace("'D:/FPS3D/FPSGAME/FPSGAME.uproject'","'D:/FPS3D/ShotgunAttachmentAudit20261016/FPSGAME.uproject'")
(O/'run_isolated_authority.ps1').write_text(authority,encoding='utf-8-sig')
wire=(O/'run_wire.ps1').read_text(encoding='utf-8-sig').replace('D:/FPS3D/FPSGAME/FPSGAME.uproject','D:/FPS3D/ShotgunAttachmentAudit20261016/FPSGAME.uproject')
(O/'run_isolated_wire.ps1').write_text(wire,encoding='utf-8-sig')
build=r'''$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/Super90AttachmentAudit20261016'
$deadline=[DateTime]::UtcNow.AddMinutes(30)
while([DateTime]::UtcNow -lt $deadline){
    $busy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe'") | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}
    if(-not $busy){break}
    $observed=Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue
    if($observed){[void]$observed.WaitForExit(10000)}
}
if($busy){exit 75}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/ShotgunAttachmentAudit20261016/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=3 "-Log=$taskRoot/isolated_editor_build.log"
$code=$LASTEXITCODE
@{exitCode=$code;target='FPSGAMEEditor Win64 Development';project='D:/FPS3D/ShotgunAttachmentAudit20261016/FPSGAME.uproject'} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/isolated_build_receipt.json" -Encoding utf8
exit $code
'''
(O/'build_isolated.ps1').write_text(build,encoding='utf-8-sig')
print('ISOLATED_SHOTGUN_SOURCE_SNAPSHOT_READY')
