"""Produce unique engine-native packages without opening or writing the main project."""
from pathlib import Path
import json,subprocess
P=Path(__file__).resolve().parent
HOST=P/'AuthorHost';HOST.mkdir(exist_ok=True)
(HOST/'Config').mkdir(exist_ok=True)
project=HOST/'RuneBellAuthor.uproject'
project.write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
    {'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}),encoding='utf-8')
(HOST/'Config/DefaultEngine.ini').write_text('''[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
-D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6
''',encoding='utf-8')
with (P/'isolated-console.log').open('w',encoding='utf-8') as output:
    result=subprocess.run(['E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',str(project),
        '-run=pythonscript','-script='+str(P/'install_assets.py'),'-unattended','-nop4','-nosplash','-NoSound',
        '-NoLiveCoding','-RenderOffscreen','-stdout','-FullStdOutLogOutput','-abslog='+str(P/'isolated-engine.log')],stdout=output,stderr=subprocess.STDOUT)
(P/'isolated-process.json').write_text(json.dumps({'exit_code':result.returncode,'main_project_written':False,'tests_run':False}),encoding='utf-8')
if result.returncode:raise RuntimeError('Isolated asset authoring failed: '+str(result.returncode))
receipt=json.loads((P/'import_receipt.json').read_text('utf-8'))
if not receipt.get('complete') or receipt.get('rune_masks')!=2:raise RuntimeError('Incomplete asset save')
print('Isolated assets saved: '+str(len(receipt['assets'])))
