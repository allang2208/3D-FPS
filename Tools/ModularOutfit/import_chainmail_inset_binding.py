"""Save isolated inset cuff assets using the current shared-sway materials."""
import json,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailInsetBinding20260929'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import import_chainmail_shared_sway as native
native.DEST='/Game/Characters/ModularOutfit20260924/ChainmailInsetBinding20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
materials=read(P/'SourceAssets/ChainmailSharedSway20260929/materials-saved.json')
group=[u.load_asset(materials[k]) for k in ['mail','steel','lining']]
if not all(group):raise RuntimeError('Missing current shared materials')
for row in read(R/'manifest.json'):
 name=row['profile'];receipt=R/'Saved'/(name+'.json')
 if receipt.exists():continue
 data=read(R/'Authored'/(name+'.json'));mask=read(Path(row['mask']))
 mesh=native.build(data,mask,group)
 native.write(receipt,dict(mesh=mesh.get_path_name(),profile=name,lods=3,changed_vertices=row['changed_vertices'],runtime_tested=False))
 print('INSET_BINDING_SAVED',name,flush=True)
print('INSET_BINDING_COMPLETE',flush=True)
