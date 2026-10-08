"""Requested local tooth investigation: source and reduced mouth geometry only."""
import bpy,numpy as np,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME')
OUT=P/'SourceAssets/SpiralPillarM14Meshy20261004/TeethRemeshV4'
OUT.mkdir(parents=True,exist_ok=True)
cases={
 'source':(P/'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV15/Authoring/M14_SupportSkin_v15.blend','M14_SoftDeathMesh'),
 'reduced':(P/'SourceAssets/AlienGeometry20261006/RemeshV3/SpiralPillarM14/SpiralPillarM14_RemeshV3.blend','M14_RemeshV3'),
}
repaired='--repaired' in sys.argv
if repaired:
 cases={'repaired':(P/'SourceAssets/AlienGeometry20261006/RemeshV4Teeth/SpiralPillarM14/SpiralPillarM14_TeethRemeshV4.blend','M14_TeethRemeshV4')}
snapshots={};report={}
for key,(file,name) in cases.items():
 bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False)
 obj=bpy.data.objects[name];mesh=obj.data
 p=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',p.ravel())
 mesh.calc_loop_triangles();f=np.empty((len(mesh.loop_triangles),3),np.int32);mesh.loop_triangles.foreach_get('vertices',f.ravel())
 poly=np.empty(len(f),np.int32);mesh.loop_triangles.foreach_get('polygon_index',poly)
 center=p[f].mean(1);s=float(bpy.data.objects['M14_Rig']['source_scale'])
 # The original author uses a 17 cm x 19 cm source-space mouth ellipse.
 bottom=-.951633 # close only; exact model geometry is retained below.
 raw=np.stack([center[:,0]/s,center[:,2]/s+bottom,-center[:,1]/s],axis=1)
 radius=np.sqrt((raw[:,0]/.17)**2+((raw[:,1]+.455)/.19)**2)
 selected=(radius<1.35)&(raw[:,2]>.10)&(raw[:,1]<-.18)
 ids,remap=np.unique(f[selected],return_inverse=True)
 uv=np.empty((len(mesh.loops),2),np.float32);mesh.uv_layers.active.data.foreach_get('uv',uv.ravel())
 loops=np.empty((len(f),3),np.int32);mesh.loop_triangles.foreach_get('loops',loops.ravel())
 mi=np.asarray([m.material_index for m in mesh.polygons])[poly[selected]]
 np.savez_compressed(OUT/(key+'_mouth.npz'),p=p[ids],f=remap.reshape(-1,3),uv=uv[loops[selected]],material=mi,original_vertices=ids)
 data=bpy.data.meshes.new('DiagnosticMouth');data.from_pydata(p[ids].tolist(),[],remap.reshape(-1,3).tolist());data.update()
 data.uv_layers.new(name='UVMap').data.foreach_set('uv',uv[loops[selected]].ravel())
 for mat in mesh.materials:data.materials.append(mat)
 data.polygons.foreach_set('material_index',mi.astype(np.int32));data.polygons.foreach_set('use_smooth',np.ones(len(mi),bool))
 crop=bpy.data.objects.new('DiagnosticMouth',data);bpy.context.scene.collection.objects.link(crop)
 for other in list(bpy.data.objects):
  if other!=crop:bpy.data.objects.remove(other,do_unlink=True)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
 scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
 if scene.world is None:scene.world=bpy.data.worlds.new('DiagnosticWorld')
 scene.world.color=(.08,.08,.08)
 camera_data=bpy.data.cameras.new('LocalMouthCamera');camera=bpy.data.objects.new('LocalMouthCamera',camera_data);scene.collection.objects.link(camera)
 target=Vector((0,-.32,.785));camera.location=(.06,-2.0,.82);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=.78;scene.camera=camera
 for name,loc,energy,size in [('Key',(-1,-1.2,1.7),100,1.0),('Fill',(1,-1,.8),65,.8)]:
  light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
  ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(OUT/(key+'_mouth.png'));bpy.ops.render.render(write_still=True)
 snapshots[key]=(p[ids],remap.reshape(-1,3));report[key]=dict(mouth_triangles=int(selected.sum()),mouth_vertices=len(ids))

if repaired:
 a=np.load(OUT/'source_mouth.npz');old,oldf=a['p'],a['f'];low,lowf=snapshots['repaired']
else:old,oldf=snapshots['source'];low,lowf=snapshots['reduced']
tree=BVHTree.FromPolygons(low.tolist(),lowf.tolist(),all_triangles=True)
distance=np.asarray([tree.find_nearest(v)[3] for v in old])
report['source_to_reduced_distance_cm']={str(q):float(np.quantile(distance,q)*100) for q in (.5,.9,.95,.99,1.)}
report['source_vertices_over_5mm']=int((distance>.005).sum())
(OUT/('investigation_repaired.json' if repaired else 'investigation.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('M14_TEETH_INVESTIGATION '+json.dumps(report),flush=True)
