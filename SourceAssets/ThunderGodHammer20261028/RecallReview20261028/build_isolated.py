"""Relink a private validation DLL; never replace the editor's mapped module or manifest."""
import subprocess,re,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];S=P/'NativeSandbox';O=S/'Objects';B=S/'Binaries/Win64'
O.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
engine=Path('E:/Program Files (x86)/UE_5.8/Engine/Source')
toolchain=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64')
inter=R/'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME'
changed=['ProductionThunderThrow','ThunderHammerThrow','ThunderHammerRecallAuditCommandlet'];substitutions={}
for name in changed:
    old=inter/(name+'.cpp.obj');new=O/(name+'.cpp.obj');substitutions[old.as_posix()]=new.as_posix()
    text=(inter/(name+'.cpp.obj.rsp')).read_text(encoding='utf-8-sig')
    for suffix in ('.cpp.obj','.cpp.sarif','.cpp.dep.json'):
        text=text.replace((inter/(name+suffix)).as_posix(),(O/(name+suffix)).as_posix())
    rsp=O/(name+'.rsp');rsp.write_text(text,encoding='utf-8')
    with (O/(name+'.log')).open('w') as log:
        subprocess.run([str(toolchain/'cl.exe'),'@'+str(rsp)],cwd=engine,stdout=log,stderr=subprocess.STDOUT,check=True)
link=(inter/'UnrealEditor-FPSGAME.dll.rsp').read_text(encoding='utf-8-sig')
for old,new in substitutions.items():link=link.replace(old,new)
link=re.sub(r'(?m)^/(?:OUT|PDB|IMPLIB):.*\n?','',link)
link+='\n/OUT:"'+(B/'UnrealEditor-FPSGAME.dll').as_posix()+'"\n/PDB:"'+(B/'UnrealEditor-FPSGAME.pdb').as_posix()+'"\n/IMPLIB:"'+(B/'UnrealEditor-FPSGAME.lib').as_posix()+'"\n'
link=link.replace('/INCREMENTAL','/INCREMENTAL:NO') if '/INCREMENTAL:NO' not in link else link
rsp=O/'link.rsp';rsp.write_text(link,encoding='utf-8')
with (O/'link.log').open('w') as log:
    subprocess.run([str(toolchain/'link.exe'),'@'+str(rsp)],cwd=engine,stdout=log,stderr=subprocess.STDOUT,check=True)
shutil.copy2(R/'Binaries/Win64/UnrealEditor.modules',B/'UnrealEditor.modules')
(P/'isolated-build-receipt.json').write_text(json.dumps({'complete':True,'module':str(B/'UnrealEditor-FPSGAME.dll'),'compiled':changed,'main_editor_module_replaced':False},indent=2))
print('THUNDER_ISOLATED_DLL_BUILT')
