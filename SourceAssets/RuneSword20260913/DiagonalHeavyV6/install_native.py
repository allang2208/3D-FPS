"""Select only this build's three coherent modules; preserve other manifest entries."""
import json,shutil
from pathlib import Path
P=Path(__file__).parent;project=P.parents[2];suffix='49146'
for relative,keys,label in [('Binaries/Win64/UnrealEditor.modules',['FPSGAME'],'FPSGAME'),
    ('Plugins/AutoFootstep/Binaries/Win64/UnrealEditor.modules',['AutoFootstep','AutoFootstepEditor'],'AutoFootstep')]:
    path=project/relative
    for key in keys:
        filename='UnrealEditor-'+key+'-'+suffix+'.dll'
        if not (path.parent/filename).is_file():raise FileNotFoundError(path.parent/filename)
    doc=json.loads(path.read_text(encoding='utf-8-sig'))
    prior=P/'Before'/('UnrealEditor.modules.'+label+'.json')
    if not prior.exists():shutil.copy2(path,prior)
    for key in keys:doc['Modules'][key]='UnrealEditor-'+key+'-'+suffix+'.dll'
    path.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print('RUNESWORD_V6_NATIVE_INSTALLED '+suffix)
