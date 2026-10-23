"""Author only new engine-native packages in an isolated commandlet project."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
HOST=P/'AuthorHost'
ENGINE=Path('E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
HOST.mkdir(exist_ok=True)
(HOST/'Config').mkdir(exist_ok=True)
project=HOST/'FinalTollAuthor.uproject'
project.write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
    {'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]},indent=2),encoding='utf-8')
(HOST/'Config/DefaultEngine.ini').write_text('''[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
-D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6
''',encoding='utf-8')
log=P/'import-commandlet.log'
with (P/'import-stdout.log').open('w',encoding='utf-8') as output:
    result=subprocess.run([str(ENGINE),str(project),'-run=pythonscript','-script='+str(P/'install_assets.py'),
        '-unattended','-nop4','-nosplash','-NoSound','-NoLiveCoding','-RenderOffscreen','-stdout',
        '-FullStdOutLogOutput','-abslog='+str(log)],stdout=output,stderr=subprocess.STDOUT)
if result.returncode:
    raise RuntimeError('Authoring failed '+str(result.returncode)+'; see '+str(log))
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
if not receipt.get('complete'):
    raise RuntimeError('Asset production did not finish')
installed=[]
for asset in receipt['assets']:
    package=Path(asset.removeprefix('/Game/').split('.')[0])
    source=HOST/'Content'/package
    destination=ROOT/'Content'/package.parent
    destination.mkdir(parents=True,exist_ok=True)
    for sidecar in source.parent.glob(source.name+'.*'):
        target=destination/sidecar.name
        data=sidecar.read_bytes()
        if target.exists():
            if target.read_bytes()!=data:
                raise RuntimeError('Preserve existing main-project package '+str(target))
        else:
            with target.open('xb') as output:
                output.write(data)
        installed.append({'path':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest()})
receipt.update(installed_to_main_project=True,installed_files=installed,commandlet_exit_code=result.returncode,
    authoring_mode='Isolated engine-native commandlet; new package files only',main_project_overwrites=False)
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('FINAL_TOLL_NEW_PACKAGES_INSTALLED '+json.dumps(installed,ensure_ascii=False))
