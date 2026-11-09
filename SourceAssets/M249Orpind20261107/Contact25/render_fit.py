from pathlib import Path
import bpy,runpy,pickle,numpy as np
from mathutils import Vector
r=Path(__file__).resolve().parent;s=runpy.run_path(str(r/'fit.py'),run_name='fit_module')
fits=pickle.load(open(r/'idle_fit.pkl','rb'));g=s['g'];out=r/'fit_views';out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=800;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
def material(n,c):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);return m
skinmat=material('skin',(.67,.42,.28));metal=material('metal',(.16,.28,.35))
def mesh(n,v,f,mat):
 ids,remap=np.unique(f,return_inverse=True);m=bpy.data.meshes.new(n);m.from_pydata(v[ids].tolist(),[],remap.reshape(-1,3).tolist());m.materials.append(mat);ob=bpy.data.objects.new(n,m);scene.collection.objects.link(ob)
selected=np.zeros(len(g['vertices']),bool);selected[s['skin_ids']]=True
faces=np.array(g['faces']);faces=faces[selected[faces].all(1)];lookup=np.full(len(g['vertices']),-1);lookup[s['skin_ids']]=np.arange(len(s['skin_ids']));faces=lookup[faces]
for family in fits:
 for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
 fit=s['Fit'](fits[family]['old_world'],family,stride=1);points=s['skin'](fit.pose(fits[family]['parameters']));mesh('hand',points,faces,skinmat)
 for name,p in s['data']['parts'][family].items():
  if 'side_mag' not in name:mesh(name,p['vertices'],p['faces'],metal)
 center=points.mean(0)
 for label,direction in [('front',(22,-12,14)),('back',(-22,10,10))]:
  cam=bpy.data.cameras.new('camera');ob=bpy.data.objects.new('camera',cam);scene.collection.objects.link(ob);ob.location=Vector(center)+Vector(direction);ob.rotation_euler=(Vector(center)-ob.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=21;scene.camera=ob;scene.render.filepath=str(out/(family+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
 if family in ['angled','canted']:
  for name in s['data']['parts'][family]:
   if 'side_mag' in name:continue
   one=s['Fit'](fits[family]['old_world'],family,[name],1);dep,_=one.measure(points,one.sample);print('PART_DEPTH',family,name,float(dep.max()),flush=True)
