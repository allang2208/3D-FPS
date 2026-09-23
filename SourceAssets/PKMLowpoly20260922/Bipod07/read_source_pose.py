import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Refinement06/PKM_Gameplay_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
a=bpy.data.actions['PKM_Game_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W=r.pose.bones['WPN_root'].matrix@fit
result={n:list(W.inverted()@r.pose.bones[n].matrix.translation) for n in ['upperarm_l','lowerarm_l','hand_l','thumb_01_l','thumb_02_l','thumb_03_l','index_01_l','middle_01_l','ring_01_l','pinky_01_l']}
(O/'old_support_source_coordinates.json').write_text(json.dumps(result,indent=2))
for ob in s.objects:
 if ob.type=='MESH':
  ob.hide_render='mechanical_bone' not in ob or ob.name.startswith('New_')
  if ob.get('source_part_id') in [65,72,127,128,129]:
   mat=bpy.data.materials.new('BipodSelection');mat.diffuse_color=(.5,.08,.01,1);mat.use_nodes=True
   mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.5,.08,.01,1)
   ob.data.materials.clear();ob.data.materials.append(mat)
s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
s.render.resolution_x=1300;s.render.resolution_y=650;s.render.resolution_percentage=100
s.world.color=(.18,.18,.18)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam);s.camera=cam
target=W@Vector((0,-.1,0));cam.location=W@Vector((1.3,-.8,.35));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.15
for name,power,position in [('Key',140,(.4,-.2,1)),('Fill',80,(-.6,0,.4))]:
 o=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(o);o.location=W@Vector(position);o.data.energy=power;o.data.size=1.5;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(O/'bipod_parts.png');bpy.ops.render.render(write_still=True)
