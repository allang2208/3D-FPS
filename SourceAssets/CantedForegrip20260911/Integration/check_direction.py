import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Canted_idle.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];s.frame_set(0);bpy.context.view_layer.update();f=json.loads((O/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root'])
print('DIRECTION', {n:list(G.inverted()@r.data.bones[n].head_local) for n in ['hand_l','hand_r','upperarm_l','upperarm_r']},flush=True)
for ob in s.objects:ob.hide_render=not(ob.name.startswith('CG_') or (ob.type=='MESH' and ob.parent==r and not ob.name.startswith('Drum')))
for label,pos in [('from_stock',(-.6,0,.02)),('from_muzzle',(.6,0,.02))]:
 focus=G@Vector((0,0,-.055));d=bpy.data.cameras.new(label);c=bpy.data.objects.new(label,d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.35;d.clip_start=.001;c.location=focus+G.to_3x3()@Vector(pos);c.rotation_euler=(focus-c.location).to_track_quat('-Z','Y').to_euler()
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100;s.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
