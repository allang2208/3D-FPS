import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;V=O.parents[1]/'VerticalForegrip20260911'
# Read the generated candidate and recover the broad radial profile along its principal body axis.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O.parent/'canted_grip_raw_00002_.glb'));raw=next(o for o in bpy.context.scene.objects if o.type=='MESH');v=np.array([tuple(raw.matrix_world@p.co) for p in raw.data.vertices]);body=v[v[:,2]<.18];center=body.mean(0);e,Q=np.linalg.eigh(np.cov(body.T));axis=Q[:,-1];axis*=1 if axis[2]>0 else -1;t=(body-center)@axis;perp=body-center-t[:,None]*axis;radii=np.linalg.norm(perp,axis=1);profile=[]
for t0 in np.linspace(np.quantile(t,.10),np.quantile(t,.90),30):
 b=radii[abs(t-t0)<.025];profile.append(float(np.median(b)) if len(b) else .13)
profile=np.convolve(np.pad(profile,(2,2),mode='edge'),np.ones(5)/5,'valid');profile/=np.median(profile)
# Clean editable retopology follows the concept mounting surface, with generated broad body variation.
bpy.ops.wm.open_mainfile(filepath=str(V/'Compact75/M4_Vertical_Fitted.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];s.frame_set(0);bpy.context.view_layer.update();f=json.loads((V/'Compact75/fit_final.json').read_text());G=Matrix(f['grip_matrix']);root=r.pose.bones['WPN_root'].matrix.copy();ob=next(o for o in s.objects if o.name.startswith('VG_'));ob.name='CG_GeneratedProfile_Refined';world=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=world
pivot=Vector((0,0,-.014));R=Matrix.Rotation(math.radians(45),4,'X');T=Matrix.Translation(pivot)@R@Matrix.Translation(-pivot);deltas=[]
for vert in ob.data.vertices:
 p=G.inverted()@world@vert.co
 if -.090<p.z<-.022:
  a=float(np.interp((p.z+.090)/.068,np.linspace(0,1,len(profile)),profile));rad=math.hypot(p.x,p.y);dr=max(-.0003,min(0,(a-1)*.003));q=1+dr/max(rad,1e-6);p.x*=q;p.y*=q;deltas.append(dr)
 if p.z<-.014:p=T@p
 vert.co=world.inverted()@G@p
H=G@T@G.inverted()@Matrix(f['hand_matrix']) if 'hand_matrix' in f else G@T@G.inverted()@root@Matrix(f['hand_in_root'])
f['hand_matrix']=[list(row) for row in H];f['hand_in_root']=[list(row) for row in root.inverted()@H];f['release_vector']=list(R.to_3x3()@Vector(f['release_vector']));f['cant_degrees']=45
(O/'fit_final.json').write_text(json.dumps(f,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Canted_Fitted.blend'))
# Current M4 atlas material paths fixed for standalone author rendering.
for mat in ob.data.materials:
 if mat and mat.use_nodes:
  for n in mat.node_tree.nodes:
   if n.type=='TEX_IMAGE' and n.image:
    p=Path('D:/FPS3D/FPSGAME/Content/M4NoSkel.fbm')/Path(n.image.filepath.replace('\\','/')).name
    if p.exists():n.image.filepath=str(p);n.image.reload()
mesh=ob.data.copy();static=bpy.data.objects.new('SM_CantedForegrip',mesh);s.collection.objects.link(static)
for vert in mesh.vertices:vert.co=G.inverted()@world@vert.co+Vector((0,0,.0007))
bpy.ops.object.select_all(action='DESELECT');static.select_set(True);bpy.context.view_layer.objects.active=static
bpy.ops.export_scene.fbx(filepath=str(O/'SM_CantedForegrip.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',path_mode='COPY',embed_textures=True)
mesh.calc_loop_triangles();(O/'model_report.json').write_text(json.dumps({'triangles':len(mesh.loop_triangles),'cant_degrees':45,'generated_source':'canted_grip_raw_00002_.glb','method':'Generated broad radial profile transferred to clean concept topology; mount and rings cleaned; exact left cant; maximum inward profile change 0.3mm in game asset','radial_delta_range_m':[min(deltas),max(deltas)],'dimensions_m':list(static.dimensions)},indent=2))
