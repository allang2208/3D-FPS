"""Publish only the fitted wrist-glove routes; preserve every equipment ID."""
import json,sys,os,uuid,hashlib,shutil,ast
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';C=R/'CuffRepairR1';D=P/'Content/ColdSteelData'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_publish.py').read_text(encoding='utf-8'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transaction'],type_ignores=[]),'wrist_glove_field_release','exec'))
manifest=read(C/'gloves-authored.json');saved=read(R/'saved.json');current=read(D/'modular_outfits.json');mapping={}
for row in manifest['rows']:
    record=saved['wear'].get(row['asset'],{})
    if record.get('sha256')!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():raise RuntimeError('Unsaved wrist glove '+row['rig'])
    disk=P/'Content'/(row['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(disk.read_bytes()).hexdigest()!=row['original_sha256']:raise RuntimeError('Original glove changed during production '+row['rig'])
    mapping[row['rig']]=(row['source'],record['asset'])
edits=[]
for prefix in [['items'],['body_variants','kaitlin','items']]:
    items=current
    for key in prefix:items=items[key]
    for rig,(old,new) in mapping.items():
        meshes=items['ue_modern_tactical_gloves']['rig_meshes']
        if rig not in meshes:continue
        if meshes[rig] not in [old,new]:raise RuntimeError('Conflicting current glove route '+rig)
        edits.append((prefix+['ue_modern_tactical_gloves','rig_meshes',rig],new))
transaction(D/'modular_outfits.json',edits);(C/'gloves-published.json').write_text(json.dumps(dict(completed=True,assets=len(mapping),edited_routes=len(edits),inventory_granted=False,gameplay_tested=False),indent=2),encoding='utf-8');print('NATIVE_WRIST_GLOVES_PUBLISHED',len(mapping),flush=True)
