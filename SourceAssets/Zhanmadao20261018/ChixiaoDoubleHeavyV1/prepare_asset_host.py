"""Read current motion sources in an isolated host; never alter loaded game assets."""
import json, re, shutil
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
H=P/'AssetHost'
body=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text('utf-8-sig'))
clips={
 'StandardHeavy':'/Game/Weapons/AzureRunesword20260913/A_RuneSword_HeavyRelease',
 'LongGripHeavy':'/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_HeavyRelease',
 'StandardUpper':'/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard',
 'LongGripUpper':'/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip',
 'BodyHeavy':body['clips']['Melee.FullBody.HeavyRelease'],
 'BodyUpper':body['clips']['Melee.FullBody.Uppercut']}
pending=[v.split('.')[0] for v in clips.values()]
copied={}
while pending:
    package=pending.pop()
    if package in copied or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+',package):continue
    rel=Path(package[6:]).with_suffix('.uasset')
    source=ROOT/'Content'/rel
    if not source.exists():continue
    target=H/'Content'/rel;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target);copied[package]=str(source)
    for suffix in ('.uexp','.ubulk','.uptnl'):
        if source.with_suffix(suffix).exists():shutil.copy2(source.with_suffix(suffix),target.with_suffix(suffix))
    pending.extend(v.decode('ascii').split('.')[0] for v in re.findall(rb'/Game/[A-Za-z0-9_/\.]+',source.read_bytes()))
(H/'Config').mkdir(exist_ok=True)
(H/'AssetHost.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
 {'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}),encoding='utf-8')
(H/'Config/DefaultEngine.ini').write_text('[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n',encoding='utf-8')
(P/'source_paths.json').write_text(json.dumps(clips,indent=2),encoding='utf-8')
(P/'asset_host_sources.json').write_text(json.dumps(copied,indent=2),encoding='utf-8')
print('CHIXIAO_MOTION_HOST_READY',len(copied),flush=True)
