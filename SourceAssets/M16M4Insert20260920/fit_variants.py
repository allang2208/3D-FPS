import bpy,bmesh,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Candidate/base/A_M16_reload.blend'),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(95);bpy.context.view_layer.update()
p={b.name:b.matrix.copy() for b in r.pose.bones};W=p['WPN_root'];Wi=W.inverted();parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};local={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in rest}
r.animation_data_clear();arms=bpy.data.objects['SK_Manny_Arms_Export'];right={g.index for g in arms.vertex_groups if g.name.endswith('_r')};bm=bmesh.new();bm.from_mesh(arms.data);deform=bm.verts.layers.deform.active;bmesh.ops.delete(bm,geom=[v for v in bm.verts if sum(w for g,w in v[deform].items() if g in right)>.5],context='VERTS');bm.to_mesh(arms.data);bm.free()
for o in s.objects:
 if o.type=='MESH':o.hide_render=o.name not in ['SK_Manny_Arms_Export','M16A2_Magazine'];o.color=(.22,.40,.57,1) if o==arms else (.73,.47,.13,1)
if not s.world:s.world=bpy.data.worlds.new('FitWorld')
s.world.color=(.10,.10,.10);s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.render.resolution_x=640;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.use_compositing=False;s.render.use_sequencer=False
c=bpy.data.objects.new('FitCamera',bpy.data.cameras.new('FitCamera'));s.collection.objects.link(c);s.camera=c;c.data.type='ORTHO';c.data.ortho_scale=.24
for label,shift,angle in [('translate',(-.012,.008,-.01),0),('roll8',(-.004,.008,0),-8),('roll12',(-.004,.008,0),-12),('roll16',(0,.008,-.004),-16)]:
 pivot=Vector((0,-.15,-.04));C=Matrix.Translation(shift)@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(angle),4,'Y')@Matrix.Translation(-pivot);D=W@C@Wi
 q={n:D@m if n.endswith('_l') else m.copy() for n,m in p.items()}
 for n,m in q.items():r.pose.bones[n].matrix_basis=local[n].inverted()@(q[parents[n]].inverted()@m if parents[n] else m)
 bpy.context.view_layer.update();pts={n:r.matrix_world@q[n].translation for n in ['hand_l','index_01_l','pinky_01_l','middle_02_l']};normal=(pts['index_01_l']-pts['hand_l']).cross(pts['pinky_01_l']-pts['hand_l']).normalized();center=(pts['hand_l']+pts['middle_02_l'])/2
 c.location=center-normal*.3+Vector((.03,.015,.02));c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'fit_{label}.png');bpy.ops.render.render(write_still=True)
