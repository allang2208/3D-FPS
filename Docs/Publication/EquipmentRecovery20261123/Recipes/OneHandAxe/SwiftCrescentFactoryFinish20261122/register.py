"""Prepare the two active catalog edits and the isolated inventory render input."""
from pathlib import Path
import hashlib
import json
import os
import shutil

batch=Path(os.environ['CRESCENT_BATCH'])
project=Path(os.environ['FPSGAME_PROJECT'])
content=project/'Content'
stage=batch/'Stage'
host=batch/'Host/Content'
root='/Game/Weapons/TacticalHatchet20261101/ModulesV1/SwiftCrescentFactoryFinish'
old='M_TacticalHatchet_Head_SwiftCrescent_Leaf'
slot='M_TacticalHatchet_Head_SwiftCrescent_Leaf'
mesh='SM_TacticalHatchet_Head_SwiftCrescent_Leaf'
desc='宽月牙沿外弧露出浅银磨刃，深灰石洗钢面在短后钩下收成一道浅叶脊。'
def obj(path):
    return path+'.'+path.rsplit('/',1)[1]

def write(path,doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode('utf8'))

module='ColdSteelData/tactical-hatchet-modules.json'
shared='ColdSteelData/shared-axe-blade-options.json'
attach='ColdSteelData/AttachmentIcons20260913/blade_1_axe_swift_crescent'
inv='ColdSteelData/Icons/ue_tactical_hatchet_axe_swift_crescent'
files=[module,shared,attach+'.png',attach+'.uasset',inv+'.png',inv+'.uasset']
manifest={}
for rel in files:
    src=content/rel
    before=batch/'Before'/rel
    before.parent.mkdir(parents=True,exist_ok=True)
    if not before.exists():
        shutil.copy2(src,before)
    manifest[rel]=hashlib.sha256(before.read_bytes()).hexdigest()
write(batch/'preimages.json',manifest)
mods=json.loads((batch/'Before'/module).read_text('utf-8-sig'))
entry=mods['slots']['blade_1']['axe_swift_crescent']
if entry['material_slot_names'] != [old]:
    raise RuntimeError('Source catalog changed')
entry.update(mesh=obj(root+'/'+mesh),materials={slot:obj(root+'/Materials/'+slot)},
             appearance=desc,material_slot_names=[slot],rune_surface_revision='swift-crescent-factory-finish-uv0-20261122')
for short in ('wing','knot','peaks'):
    table=mods['slots']['blade_2']['knife_mark_'+short]['surface_materials']
    table[slot]=obj(root+'/Materials/MI_HatchetMark_SwiftCrescent_Leaf_Rune'+short.title())
write(stage/module,mods)
# Only the two needed entries enter the isolated catalog studio.
mods['slots']['blade_1']={key:mods['slots']['blade_1'][key] for key in ('factory','axe_swift_crescent')}
write(host/module,mods)
options=json.loads((batch/'Before'/shared).read_text('utf-8-sig'))
item=next(v for v in options['options'] if v['id']=='axe_swift_crescent')
item.update(description=desc,appearance=desc)
write(stage/shared,options)
