import json, shutil
from pathlib import Path
import tempfile
import os
P=Path(os.environ['FPSGAME_PROJECT']).resolve()
W=Path(__file__).resolve().parent
H=Path(tempfile.gettempdir())/'KaitlinWeaponContacts20261024/AuthorHost'
c=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
prefixes=('Warhammer.','Melee.','Bow.','Staff.','Kukri.','Rifle.','Pistol.','SinglePistol.','DualPistol.')
if (W/'plan.json').exists():
    paths={v for row in json.loads((W/'plan.json').read_text()).values() for v in (row['source'],row['target']) if v}
else:
    paths={v for d in (c,c['body_variants']['kaitlin']) for k,v in d['clips'].items() if k.startswith(prefixes)}
paths.update(['/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body_Skeleton',
 '/Game/Characters/KaitlinPlayer20261023/Native/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel'])
for path in paths:
    rel=Path(path.split('.')[0][6:]+'.uasset')
    dst=H/'Content'/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(P/'Content'/rel,dst)
(H/'Config').mkdir(exist_ok=True)
(H/'WeaponContactAuthor.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Plugins':[
 {'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}))
(H/'Config/DefaultEngine.ini').write_text('[/Script/PythonScriptPlugin.PythonScriptPluginSettings]\nbRemoteExecution=False\n')
print('Copied animation and skeleton inputs:',len(paths))
