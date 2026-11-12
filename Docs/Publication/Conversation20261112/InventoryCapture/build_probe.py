from pathlib import Path
import json
import subprocess

here=Path(__file__).resolve().parent
game=here.parents[2]
obj=game/'Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME'
engine=Path('E:/Program Files (x86)/UE_5.8/Engine/Source')
bin=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64')
source=here/'BagCheck.cpp'
plug=here/'BagCheck'
out=plug/'Binaries/Win64'
out.mkdir(exist_ok=True,parents=True)
def call(exe,params):
    result=subprocess.run([str(bin/exe),'@'+str(params)],cwd=engine,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout.decode('mbcs',errors='replace'))
    result.check_returncode()
defs=(obj/'Definitions.FPSGAME.h').read_text().replace('"FPSGAME"', '"BagCheck"').replace('FPSGAME_API DLLEXPORT','FPSGAME_API DLLIMPORT').replace('FPSGAME_NON_ATTRIBUTED_API DLLEXPORT','FPSGAME_NON_ATTRIBUTED_API DLLIMPORT')
(here/'Definitions.h').write_text(defs)
params=(obj/'ColdSteelWeaponIconAudit.cpp.obj.rsp').read_text().splitlines()
params[0]='"'+source.as_posix()+'"'
cmd='\n'.join(params).replace((obj/'Definitions.FPSGAME.h').as_posix(),(here/'Definitions.h').as_posix()).replace((obj/'ColdSteelWeaponIconAudit.cpp').as_posix(),(here/'review').as_posix())
(here/'compile.rsp').write_text(cmd+'\n/I"'+(game/'Source/FPSGAME').as_posix()+'"\n')
if not (here/'review.obj').exists() or (here/'review.obj').stat().st_mtime < source.stat().st_mtime:
    call('cl.exe',here/'compile.rsp')
params=(obj/'UnrealEditor-FPSGAME.dll.rsp').read_text().splitlines()
flags=[s for s in params if not s.startswith(('/PDB','/OUT','/NATVIS','/DEBUG')) and not s.endswith(('.obj"','.res"'))]
flags += [s for s in params if 'SharedPCH.' in s and s.endswith('.obj"')]
flags+=['"'+(here/'review.obj').as_posix()+'"','"'+(obj/'UnrealEditor-FPSGAME.lib').as_posix()+'"','/OUT:"'+(out/'UnrealEditor-BagCheck.dll').as_posix()+'"','/DEBUG:NONE']
(here/'link.rsp').write_text('\n'.join(flags))
call('link.exe',here/'link.rsp')
manifest=json.loads((game/'Binaries/Win64/UnrealEditor.modules').read_text())
(out/'UnrealEditor.modules').write_text(json.dumps({'BuildId':manifest['BuildId'],'Modules':{'BagCheck':'UnrealEditor-BagCheck.dll'}}))
(plug/'BagCheck.uplugin').write_text(json.dumps({'FileVersion':3,'Version':1,'VersionName':'1','FriendlyName':'Inventory icon observation','EnabledByDefault':False,'CanContainContent':False,'Modules':[{'Name':'BagCheck','Type':'Runtime','LoadingPhase':'PostEngineInit'}]}))
