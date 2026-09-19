"""Select the coherent modules produced by this revision's necessary build."""
import json,shutil
from pathlib import Path
P=Path(__file__).parent;project=P.parents[2];suffix=(P/'build_suffix.txt').read_text(encoding='utf-8-sig').strip()
backup=P/'Before';backup.mkdir(exist_ok=True)
for relative,keys,label in [('Binaries/Win64/UnrealEditor.modules',['FPSGAME'],'FPSGAME'),
    ('Plugins/AutoFootstep/Binaries/Win64/UnrealEditor.modules',['AutoFootstep','AutoFootstepEditor'],'AutoFootstep')]:
    path=project/relative;prior=backup/('UnrealEditor.modules.'+label+'.json')
    if not prior.exists():shutil.copy2(path,prior)
    doc=json.loads(path.read_text(encoding='utf-8-sig'))
    for key in keys:doc['Modules'][key]='UnrealEditor-'+key+'-'+suffix+'.dll'
    path.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print('Installed rune sword native modules '+suffix)
