"""Editable Blender copies of the final UE-composed animation exports."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;report={}
for variant in ['prism','angled']:
 for f in sorted((O/variant).glob('*_Runtime.fbx')):
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(f),use_anim=True,automatic_bone_orientation=False)
  rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert rigs
  bpy.ops.wm.save_as_mainfile(filepath=str(f.with_suffix('.blend')));report[f.stem]={'rigs':[r.name for r in rigs],'actions':[a.name for a in bpy.data.actions]}
assert len(report)==18;(O/'runtime_editable.json').write_text(json.dumps(report,indent=2));print('AKM_RUNTIME_EDITABLE_PASS')
