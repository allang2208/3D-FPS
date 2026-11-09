"""Close views of current native idle contacts for separating pre-existing grip fit."""
from pathlib import Path
import bpy,json,numpy as np
from mathutils import Vector,Quaternion
r=Path(__file__).resolve().parent;out=r/'grip_close';out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.world=bpy.data.worlds.new('Review');s.world.color=(.08,.08,.08)
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
skin=material('skin',(.65,.4,.25));steel=material('steel',(.13,.22,.31))
for family in ['base','vertical','canted','prism','angled']:
 folder=r/'delivered'/f'30_normal_{family}_left';j=json.loads((folder/'review.json').read_text());meta=json.loads((folder/'geometry.json').read_text());row=j['frames'][-1];stem=folder/Path(row['file']).stem
 for ob in list(s.objects):bpy.data.objects.remove(ob,do_unlink=True)
 v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);m=np.fromfile(stem.with_suffix('.materials'),np.uint32);dom=np.fromfile(folder/'dominant.bin',np.uint32)
 hand=np.array([n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky')) for n in meta['bones']])[dom];hf=f[hand[f].all(1)];center=v[np.unique(hf)].mean(0)
 def mesh(name,points,faces,mat):
  ids,remap=np.unique(faces,return_inverse=True);d=bpy.data.meshes.new(name);d.from_pydata(points[ids].tolist(),[],remap.reshape(-1,3).tolist());d.materials.append(mat);ob=bpy.data.objects.new(name,d);s.collection.objects.link(ob)
 mesh('left_hand',v,hf,skin)
 for slot in ['M249_Factory_Handguard','M249_Factory_Foregrip']:
  mi=meta['slots'].index(slot)
  if mi in row['visible_materials']:mesh(slot,v,f[m==mi],steel)
 for p in folder.glob(stem.name+'_*'+family+'.vertices'):
  mesh(p.stem,np.fromfile(p,np.float32).reshape(-1,3),np.fromfile(p.with_suffix('.indices'),np.uint32).reshape(-1,3),steel)
 raw=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+j['bone_count']*7);pose=raw[-1,4:].reshape(-1,7);q=pose[meta['bones'].index('WPN_root'),3:];spin=Quaternion((float(q[3]),*map(float,q[:3])))
 cam=bpy.data.cameras.new('camera');ob=bpy.data.objects.new('camera',cam);s.collection.objects.link(ob);ob.location=Vector(center)+spin@Vector((26,5,12));ob.rotation_euler=(Vector(center)-ob.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=19;s.camera=ob;s.render.filepath=str(out/(family+'.png'));bpy.ops.render.render(write_still=True)
