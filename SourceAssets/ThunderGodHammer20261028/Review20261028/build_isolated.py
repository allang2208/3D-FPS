"""Compile the targeted diagnostic into a private DLL, preserving the editor's loaded binary."""
import json,re,shutil,subprocess,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parent.parents[1]
I=ROOT/'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME'
HOST=P/'Host';BIN=HOST/'Binaries/Win64';BIN.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'FPSGAME.uproject',HOST/'FPSGAME.uproject')
shutil.copy2(ROOT/'Binaries/Win64/UnrealEditor.modules',BIN/'UnrealEditor.modules')
shutil.copytree(ROOT/'Config',HOST/'Config',dirs_exist_ok=True)
sources={'WarhammerModificationAuditCommandlet.cpp':'Production','ProductionStormDriveLightning.cpp':'Production','MeleeRuneVisual.cpp':'Weapons'}
stems=list(sources)
for stem in stems:
    compile_rsp=(I/(stem+'.obj.rsp')).read_text(encoding='utf-8-sig')
    for suffix in ('.obj','.sarif','.dep.json'):
        compile_rsp=compile_rsp.replace((I/(stem+suffix)).as_posix(),(P/(stem+suffix)).as_posix())
    (P/(stem+'.compile.rsp')).write_text(compile_rsp,encoding='utf-8')
link_rsp=(I/'UnrealEditor-FPSGAME.dll.rsp').read_text(encoding='utf-8-sig')
for stem in stems:
    old_obj=(I/(stem+'.obj')).as_posix();new_obj=(P/(stem+'.obj')).as_posix()
    if old_obj not in link_rsp:raise RuntimeError('Object is not independently linked: '+stem)
    link_rsp=link_rsp.replace(old_obj,new_obj)
link_rsp=re.sub(r'^/(OUT|PDB|IMPLIB):"[^"]+"',lambda m:'/'+m[1]+':"'+(BIN/('UnrealEditor-FPSGAME.'+{'OUT':'dll','PDB':'pdb','IMPLIB':'lib'}[m[1]])).as_posix()+'"',link_rsp,flags=re.M)
if not re.search(r'^/IMPLIB:',link_rsp,re.M):link_rsp+='\n/IMPLIB:"'+(BIN/'UnrealEditor-FPSGAME.lib').as_posix()+'"\n'
(P/'link.rsp').write_text(link_rsp,encoding='utf-8')
batch='@echo off\r\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" -vcvars_ver=14.44\r\n'
batch+='cd /d "E:\\Program Files (x86)\\UE_5.8\\Engine\\Source"\r\n'
for stem in stems:
    batch+='cl.exe @"'+str(P/(stem+'.compile.rsp'))+'"\r\nif errorlevel 1 exit /b %errorlevel%\r\n'
batch+='link.exe @"'+str(P/'link.rsp')+'"\r\nexit /b %errorlevel%\r\n'
(P/'build-isolated.cmd').write_text(batch,encoding='ascii')
with (P/'build-isolated.log').open('w',encoding='utf-8') as log:
    result=subprocess.run(['cmd.exe','/c',str(P/'build-isolated.cmd')],stdout=log,stderr=subprocess.STDOUT)
receipt={'exit_code':result.returncode,'source_sha256':{s:hashlib.sha256((ROOT/'Source/FPSGAME'/sources[s]/s).read_bytes()).hexdigest() for s in stems},
    'build':'Compile diagnostic, StormDrive and rune fixes; link against current production object set into private output DLL',
    'shared_binary_modified':False,'host':str(HOST)}
if result.returncode==0:receipt['dll_sha256']=hashlib.sha256((BIN/'UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest()
(P/'isolated-build.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ISOLATED_DIAGNOSTIC_BUILD exit='+str(result.returncode))
raise SystemExit(result.returncode)
