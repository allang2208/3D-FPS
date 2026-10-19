"""Create an isolated material-authoring host; this ribbon has no game dependencies."""
import json,re
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
H=P/'AssetHost'
(H/'Config').mkdir(parents=True,exist_ok=True)
(H/'AssetHost.uproject').write_text(json.dumps({
    'FileVersion':3,'EngineAssociation':'5.8',
    'Description':'Zhufeng cyan trail material authoring; no game module',
    'Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},
               {'Name':'EditorScriptingUtilities','Enabled':True}]},indent=2)+'\n',encoding='utf-8')
config=(ROOT/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
renderer=re.search(r'(?ms)^\[/Script/Engine.RendererSettings\]\s*\n.*?(?=^\[|\Z)',config)
(H/'Config/DefaultEngine.ini').write_text((renderer.group(0) if renderer else '')+
    '\n[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n',encoding='utf-8')
print('ZHUFENG_CYAN_HOST_READY')
