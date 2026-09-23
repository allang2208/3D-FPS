import bpy,json,ast,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;F=O/'frames';S=O.parent/'SVDAttachments20260923'
tree=ast.parse((O/'inspect_geometry.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mat','verts']],type_ignores=[]),'<audit_helpers>','exec'))
bpy.ops.wm.open_mainfile(filepath=str(S/'SVD_Modular_Editable.blend'));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE');arms=bpy.data.objects['SK_Manny_Arms_Export']
for o in list(s.objects):
 if o.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(o,do_unlink=True)
blue=mat('Audit_Left',(.06,.38,.56));orange=mat('Audit_Right',(.7,.27,.07));gray=mat('Audit_Gun',(.21,.235,.255));yellow=mat('Audit_Mag',(.48,.48,.33));red=mat('Audit_Handle',(.7,.08,.07))
groups={g.index:g.name for g in arms.vertex_groups};left={v.index:sum(g.weight for g in v.groups if groups[g.group].endswith('_l'))>.5 for v in arms.data.vertices}
for o in s.objects:
 if o.type!='MESH':continue
 o.hide_render=False;o.data.materials.clear()
 if o==arms:
  o.data.materials.append(blue);o.data.materials.append(orange)
  for p in o.data.polygons:p.material_index=0 if left[p.vertices[0]] else 1
 else:
  o.data.materials.append(yellow if 'Magazine' in o.name else red if 'ChargingHandle' in o.name else gray)
  for p in o.data.polygons:p.material_index=0
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.resolution_x=720;s.render.resolution_y=620;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
s.world=bpy.data.worlds.new('AuditWorld');s.world.use_nodes=True;ns=s.world.node_tree.nodes;ns.clear();bg=ns.new('ShaderNodeBackground');wo=ns.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.5,.5,.5,1);bg.inputs[1].default_value=.7
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0;s.view_settings.gamma=1;s.render.use_compositing=False;s.render.use_sequencer=False
cam=bpy.data.objects.new('AuditCamera',bpy.data.cameras.new('AuditCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.27
light=bpy.data.objects.new('AuditLight',bpy.data.lights.new('AuditLight','AREA'));s.collection.objects.link(light);light.data.energy=12;light.data.size=.6
for clip,f,side in [('reload',180,'l'),('reload',240,'l'),('equip',94,'r')]:
 a=bpy.data.actions['A_SVD_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update()
 point=lambda n:(r.matrix_world@r.pose.bones[n+'_'+side].matrix).translation
 wrist=point('hand');index=point('index_01');pinky=point('pinky_01');direction=((index+pinky)*.5-wrist).normalized();normal=(index-wrist).cross(pinky-wrist).normalized()
 target=bpy.data.objects['SM_SVD_Magazine' if side=='l' else 'SM_SVD_ChargingHandle'];vs,_=verts(target);center=sum(vs,Vector())/len(vs)
 center=(center+wrist+index+pinky)*.25
 for sign in [-1,1]:
  cam.location=center+normal*(.6*sign)+direction*.14;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();light.location=cam.location+direction*.15;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(F/f'palm_{clip}_{f}_{sign}.png');bpy.ops.render.render(write_still=True)
print('SVD_AUDIT_PALM_DONE',flush=True)
