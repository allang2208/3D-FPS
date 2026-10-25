"""Capture actual runtime donor paths and author in an isolated UE host."""
from pathlib import Path
import json,re,shutil,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[2];H=P/'AuthorHost'
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text('utf-8-sig'))
spec={'fps_normal':'/Game/Weapons/SteelWarhammer20261014/NormalComboV4/A_Warhammer_Slash1',
      'fps_upper':'/Game/Weapons/SteelWarhammer20261014/UppercutV1/A_Warhammer_Uppercut','bodies':[]}
for variant,clips in [('Default',cfg['clips']),('kaitlin',cfg['body_variants']['kaitlin']['clips'])]:
    spec['bodies'].append({'variant':variant,'normal':clips['Warhammer.FullBody.Slash1'],'upper':clips['Warhammer.FullBody.Uppercut']})
(P/'inputs.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
pending=[spec['fps_normal'],spec['fps_upper']]+[r[k] for r in spec['bodies'] for k in ('normal','upper')]
copied={}
while pending:
    package=pending.pop().split('.')[0]
    if package in copied or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+',package):continue
    rel=Path(package[6:]).with_suffix('.uasset');src=ROOT/'Content'/rel
    if not src.exists():continue
    dst=H/'Content'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);copied[package]=str(src)
    for suffix in ('.uexp','.ubulk','.uptnl'):
        if src.with_suffix(suffix).exists():shutil.copy2(src.with_suffix(suffix),dst.with_suffix(suffix))
    pending.extend(s.decode('ascii').split('.')[0] for s in re.findall(rb'/Game/[A-Za-z0-9_/\.]+',src.read_bytes()))
(H/'Config').mkdir(exist_ok=True)
project=H/'DirectReuseAuthor.uproject'
project.write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
    {'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}),encoding='utf-8')
(H/'Config/DefaultEngine.ini').write_text('[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n[/Script/Engine.RendererSettings]\nr.Substrate=True\n',encoding='utf-8')
(P/'authoring_inputs.json').write_text(json.dumps(copied,indent=2),encoding='utf-8')
with (P/'author-console.log').open('w',encoding='utf-8') as output:
    result=subprocess.run(['E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',str(project),
        '-run=pythonscript','-script='+str(P/'author.py'),'-unattended','-nop4','-nosplash','-NoSound','-NoLiveCoding',
        '-AllowCommandletRendering','-RenderOffscreen','-stdout','-FullStdOutLogOutput','-abslog='+str(P/'author-engine.log')],stdout=output,stderr=subprocess.STDOUT)
(P/'author-process.json').write_text(json.dumps({'exit_code':result.returncode,'main_project_written':False}),encoding='utf-8')
if result.returncode:raise RuntimeError('Authoring failed '+str(result.returncode))
print('Native first strike, uppercut and matching body charges saved')
