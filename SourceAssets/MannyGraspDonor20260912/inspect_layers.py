import bpy,json
from pathlib import Path
O=Path(__file__).parent;out={}
for label in ['Grasp','Idle','IndexCurl','ThumbUp']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(O/'Donor'/f'A_MannequinsXR_{label}_Right.fbx'),automatic_bone_orientation=False)
 r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');a=r.animation_data.action
 for f in sorted(set([float(a.frame_range[0]),float(a.frame_range[1])])):
  bpy.context.scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
  out[label+'_'+str(f)]={'range':list(a.frame_range),'world':[list(x) for x in r.matrix_world], 'bones':{b.name:{'parent':b.parent.name if b.parent else None,'rest':[list(x) for x in b.bone.matrix_local],'pose':[list(x) for x in b.matrix],'basis':[list(x) for x in b.matrix_basis]} for b in r.pose.bones}}
(O/'donor_layers.json').write_text(json.dumps(out,indent=2))
print('DONOR_LAYERS_READY',flush=True)
