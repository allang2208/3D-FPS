import json,re,shutil,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];H=P/'AssetHost'
targets=['/Game/Weapons/Zhanmadao20261018/ChixiaoDoubleHeavyV1/A_Chixiao_DoubleHeavy_'+v for v in ('Standard','LongGrip')]
pending=targets+['/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'];copied={};before={}
while pending:
    package=pending.pop().split('.')[0]
    if package in copied or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+',package):continue
    rel=Path(package[6:]).with_suffix('.uasset');source=ROOT/'Content'/rel
    if not source.exists():continue
    dest=H/'Content'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    copied[package]=str(source)
    if package in targets:before[package]=hashlib.sha256(source.read_bytes()).hexdigest()
    for suffix in ('.uexp','.ubulk','.uptnl'):
        if source.with_suffix(suffix).exists():shutil.copy2(source.with_suffix(suffix),dest.with_suffix(suffix))
    pending.extend(s.decode('ascii').split('.')[0] for s in re.findall(rb'/Game/[A-Za-z0-9_/\.]+',source.read_bytes()))
(H/'Config').mkdir(exist_ok=True)
(H/'AssetHost.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}),encoding='utf-8')
(H/'Config/DefaultEngine.ini').write_text('[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n',encoding='utf-8')
(P/'isolated-inputs.json').write_text(json.dumps({'packages':copied,'before':before},indent=2),encoding='utf-8')
print('CHIXIAO_ISOLATED_HOST_READY',len(copied))
