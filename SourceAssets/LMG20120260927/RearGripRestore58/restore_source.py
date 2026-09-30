"""Recover original UV-matched donor surfaces, before G43/J44 deformation."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent.parent
catalog=json.loads((S/'A762Meshy20260920/Accessories05/sources.json').read_text())['meshes']
pkm=Matrix(json.loads((S/'PKMLowpoly20260922/Accessories14/authoring.json').read_text())['rear_grip_transform'])
a22=json.loads((O.parent/'Accessories22/geometry.json').read_text())['meshes']
report={};bpy.context.preferences.filepaths.save_version=0
for key,variant in {'stable':'stable_antislip_reargrip','balanced':'balanced_reargrip','phantom':'phantom_reargrip'}.items():
 info=catalog[variant]
 source=str(S/{'stable':'StableAntiSlipRearGrip20260913/seed_91727/textured_master_00001_.glb','balanced':'BalancedRearGrip20260913/seed_91703/textured_master_00001_.glb','phantom':'PhantomRearGripMultiview_20260913/seed_91627/textured_master_00001_.glb'}[key])
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=source)
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_'))]
 ob=max(meshes,key=lambda o:len(o.data.polygons))
 for q in meshes:
  if q!=ob:bpy.data.objects.remove(q,do_unlink=True)
 me=ob.data;initial=Matrix.Rotation(-math.pi/2,4,'Z')@ob.matrix_world
 if key=='stable':fit=Matrix(json.loads((S/'StableAntiSlipRearGrip20260913/Selected91727/authoring.json').read_text())['AKM']['transform'])
 elif key=='phantom':fit=Matrix(json.loads((S/'PhantomRearGripIntegration20260913/authoring.json').read_text())['fits']['AKM']['root_space_metres'])
 else:
  with bpy.data.libraries.load(str(S/'PhantomRearGripSeamFit20260913/AKM_Assembly_Editable.blend'),link=False) as (a,b):b.objects=['FactoryMountReference']
  ref=b.objects[0];vv=[initial@v.co for v in me.vertices];ff=[ref.matrix_world@v.co for v in ref.data.vertices]
  sl=Vector([min(v[i] for v in vv) for i in range(3)]);sh=Vector([max(v[i] for v in vv) for i in range(3)]);tl=Vector([min(v[i] for v in ff) for i in range(3)]);th=Vector([max(v[i] for v in ff) for i in range(3)])
  head=[v for v in vv if v.y<sl.y+(sh.y-sl.y)*.36 and v.z>sl.z+(sh.z-sl.z)*.60];fh=[v for v in ff if v.z>th.z-(th.z-tl.z)*.15]
  scale=(th.z-tl.z)/(sh.z-sl.z);width=(th.x-tl.x)/(sh.x-sl.x)
  fit=Matrix.Translation(((tl.x+th.x)/2,(min(v.y for v in fh)+max(v.y for v in fh))*.5,th.z-.003))@Matrix.Diagonal((width,scale,scale,1))@Matrix.Translation((-(sl.x+sh.x)/2,-(min(v.y for v in head)+max(v.y for v in head))*.5,-max(v.z for v in head)))
  bpy.data.objects.remove(ref,do_unlink=True)
 xf=Matrix(a22[variant]['transform_blender'])@pkm@fit@initial
 normals=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in me.corner_normals]
 me.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);me.normals_split_custom_set(normals)
 bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table();layers=[bm.loops.layers.float.new('SourceN'+c) for c in 'xyz']
 for f in bm.faces:
  for l,li in zip(f.loops,me.polygons[f.index].loop_indices):
   for k,layer in enumerate(layers):l[layer]=normals[li][k]
 # Weld exact glTF UV splits before any local neck work. No decimation or
 # voxel reconstruction: the full textured source topology is restored.
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00000012)
 ns=[[l[layer] for layer in layers] for f in bm.faces for l in f.loops]
 bm.to_mesh(me);bm.free();me.update();me.normals_split_custom_set(ns)
 v=np.array([v.co[:] for v in me.vertices]);sections=[]
 for z in [-.09,-.075,-.06,-.045,-.03,-.02,-.015,-.01,0]:
  band=v[abs(v[:,2]-z)<.0015]
  if len(band):sections.append({'z':z,'min':band.min(0).tolist(),'max':band.max(0).tolist(),'center':((np.quantile(band,.04,axis=0)+np.quantile(band,.96,axis=0))*.5).tolist()})
 out=O/('Original_'+key+'.blend');ob.name='Original_'+key;bpy.ops.wm.save_as_mainfile(filepath=str(out))
 report[key]={'variant':variant,'source':source,'material':info['materials'][0],'source_transform':[list(r) for r in xf],'vertices':len(me.vertices),'faces':len(me.polygons),'uv_layers':[l.name for l in me.uv_layers],'bounds':[v.min(0).tolist(),v.max(0).tolist()],'sections':sections,'restored_blend':str(out),'whole_grip_remesh':False,'decimated':False}
 print('R58_ORIGINAL_RECOVERED',key,len(me.polygons),flush=True)
(O/'originals.json').write_text(json.dumps(report,indent=2))
