"""Targeted source view of the requested hand/magazine/well contact."""
import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;phase='Animations' if '--final' in sys.argv else 'Candidate'
for kind,frames in [('reload',[61,76,88,95,103]),('reload_empty',[43,54,70,80,88,100])]:
 bpy.ops.wm.open_mainfile(filepath=str(O/phase/'base'/('A_M16_'+kind+'.blend')),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 for o in s.objects:
  if o.type=='MESH':
   visible=o.name=='SK_Manny_Arms_Export' or o.name.startswith('M16A2_');o.hide_render=not visible
   if o.name in bpy.context.view_layer.objects:o.hide_set(not visible)
   o.color=(.22,.40,.57,1) if o.name=='SK_Manny_Arms_Export' else (.73,.47,.13,1) if 'Magazine' in o.name else (.30,.32,.34,1)
 if not s.world:s.world=bpy.data.worlds.new('ContactSourceWorld')
 s.world.color=(.10,.10,.10);s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD'
 s.render.resolution_x=720;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.use_compositing=False;s.render.use_sequencer=False
 c=bpy.data.objects.new('InsertContactCamera',bpy.data.cameras.new('InsertContactCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.50
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update();W=r.matrix_world@r.pose.bones['WPN_root'].matrix
  center=W@Vector((0,-.13,-.04));c.location=center+W.to_quaternion()@Vector((-.65,.22,.08));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{phase}_{kind}_{f}.png');bpy.ops.render.render(write_still=True)
 # Isolate the left hand: source skin group ownership, with no mesh edits saved.
 arms=bpy.data.objects['SK_Manny_Arms_Export'];right={g.index for g in arms.vertex_groups if g.name.endswith('_r')}
 import bmesh
 bm=bmesh.new();bm.from_mesh(arms.data);deform=bm.verts.layers.deform.active
 remove=[v for v in bm.verts if sum(w for g,w in v[deform].items() if g in right)>.5]
 bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(arms.data);bm.free()
 f=76 if kind=='reload' else 54;s.frame_set(f);bpy.context.view_layer.update()
 for o in s.objects:
  if o.type=='MESH':o.hide_render=o.name not in ['SK_Manny_Arms_Export','M16A2_Magazine']
 pts={n:r.matrix_world@r.pose.bones[n].matrix.translation for n in ['hand_l','index_01_l','pinky_01_l','middle_02_l']};normal=(pts['index_01_l']-pts['hand_l']).cross(pts['pinky_01_l']-pts['hand_l']).normalized();center=(pts['hand_l']+pts['middle_02_l'])/2
 c.data.ortho_scale=.25
 for sign,view in [(1,'palm'),(-1,'back')]:
  c.location=center+normal*.3*sign+Vector((.03,.015,.02));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{phase}_{kind}_{view}.png');bpy.ops.render.render(write_still=True)
print('M16_INSERT_SOURCE_VIEWS_COMPLETE',flush=True)
