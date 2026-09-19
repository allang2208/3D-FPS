import bpy,json
from pathlib import Path
O=Path(__file__).parent;report={}
for variant in ['prism','angled']:
 for path in sorted((O/variant).glob('*.blend')):
  bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
  clip=path.stem.removeprefix('A_AKM_'+variant+'_');out=bpy.data.actions[path.stem];base=bpy.data.actions['AKM_EquipCharge' if clip=='equip' else 'AKM_Native_'+clip.replace('drum_','')]
  end=s.frame_end;old={};worst=0.;contact=0.;joint=0.
  r.animation_data.action=base;r.animation_data.action_slot=base.slots[0]
  for f in range(end+1):
   s.frame_set(f);old[f]={b.name:(b.matrix.copy(),b.location.copy(),b.scale.copy()) for b in r.pose.bones}
  r.animation_data.action=out;r.animation_data.action_slot=out.slots[0]
  for f in range(end+1):
   s.frame_set(f)
   for b in r.pose.bones:
    m,l,z=old[f][b.name];delta=max(abs(b.matrix[i][j]-m[i][j]) for i in range(4) for j in range(4))
    if not b.name.endswith('_l'):worst=max(worst,delta)
    if 'reload' in clip and 42<=f<=end-48:contact=max(contact,delta)
    if b.name.endswith('_l') and b.name!='clavicle_l':joint=max(joint,(b.location-l).length,(b.scale-z).length)
  report[path.stem]={'frames':end,'non_left_matrix_error':worst,'original_reload_contact_error':contact,'joint_translation_scale_error':joint}
  assert worst<.0001 and contact<.0001 and joint<.0001,report[path.stem]
  if variant=='angled':
   with bpy.data.libraries.load(str(O/'AKM_Attachments_Editable.blend')) as (src,dst):dst.objects=['SM_AKM_angled']
   updated=dst.objects[0];bpy.data.objects['SM_AKM_angled'].data=updated.data;bpy.data.objects.remove(updated,do_unlink=True)
   s.frame_set(end);bpy.ops.wm.save_as_mainfile(filepath=str(path))
  print('SOURCE_CHECK',path.stem,flush=True)
(O/'source_validation.json').write_text(json.dumps(report,indent=2));print('AKM_SOURCE_VALIDATION_PASS',flush=True)
