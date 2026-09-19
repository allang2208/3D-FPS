import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).resolve().parent;S=Path('D:/FPS3D/FPSGAME/SourceAssets')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'TacticalStock_Game_Body.blend'))
low=bpy.data.objects['TacticalStock_Game_Body'];base=low.data.copy()
report={'variants':{},'orientation':'front -X / buttpad +X, before QBZ191 root transform','runtime_tested':False}
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def receiver_finish(m,family):
 n=m.node_tree.nodes;l=m.node_tree.links;bs=next(n for n in n if n.type=='BSDF_PRINCIPLED');uv=n.new('ShaderNodeUVMap');uv.uv_map='ReceiverUV1'
 for pin in ['Base Color','Roughness','Metallic']:
  for link in list(bs.inputs[pin].links):l.remove(link)
 def sample(path,color):
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path),check_existing=True);t.image.colorspace_settings.name='sRGB' if color else 'Non-Color';t.extension='MIRROR';l.new(uv.outputs[0],t.inputs[0]);return t
 if family=='M4':
  t=sample(S/'WeaponAttachmentFinish20260913/Textures/T_M4_Receiver_BaseColor.png',True);l.new(t.outputs[0],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.38;bs.inputs['Metallic'].default_value=.8
 elif family=='AKM':
  for key,pin in [('Base_color','Base Color'),('Roughness','Roughness'),('Metallic','Metallic')]:
   t=sample(S/'AKMArmSupport20260911/Metal'/('T_AKM_Mount_'+key+'.png'),key=='Base_color');l.new(t.outputs[0],bs.inputs[pin])
 else:
  folder=S/'StableAntiSlipRearGrip20260913/Selected91727/Textures';t=sample(folder/'T_QBZ191_StableCollar_BaseColor.png',True);l.new(t.outputs[0],bs.inputs['Base Color']);t=sample(folder/'T_QBZ191_StableCollar_ORM.png',False);sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs[0],sep.inputs[0]);l.new(sep.outputs[1],bs.inputs['Roughness']);l.new(sep.outputs[2],bs.inputs['Metallic'])
for family in ['M4','AKM','QBZ191']:
 ob=bpy.data.objects.new('SM_TacticalTelescopicStock',base.copy());bpy.context.collection.objects.link(ob)
 for i,m in enumerate(list(ob.data.materials)):
  ob.data.materials[i]=m.copy();ob.data.materials[i].name=m.name+'_'+family
 receiver_finish(ob.data.materials[0],family)
 adapter=ob.data.materials[0].copy();adapter.name='TacticalStock_Adapter_'+family
 bs=next(n for n in adapter.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for link in list(bs.inputs['Normal'].links):adapter.node_tree.links.remove(link)
 leading={'M4':.007,'AKM':.0028,'QBZ191':0.}[family];body_front=leading+.005
 ob.data.transform(Matrix.Translation((body_front,0,0)))
 # A short tapered sleeve joins the measured narrow elliptical source sleeve to the gun tube.
 xs=[leading,leading+.001,leading+.0045,leading+.006]
 outer=[(.0137,.0137),(.0138,.0138),(.0101,.0125),(.0101,.0125)]
 inner=[(.0118,.0118),(.0118,.0118),(.0087,.0108),(.0087,.0108)]
 n=96;verts=[];faces=[]
 for radii in [outer,inner]:
  for x,(ry,rz) in zip(xs,radii):verts.extend([(x,ry*math.cos(i*2*math.pi/n),rz*math.sin(i*2*math.pi/n)) for i in range(n)])
 for shell in [0,1]:
  start=shell*len(xs)*n
  for row in range(len(xs)-1):
   for i in range(n):
    j=(i+1)%n;f=(start+row*n+i,start+row*n+j,start+(row+1)*n+j,start+(row+1)*n+i);faces.append(f if shell==0 else tuple(reversed(f)))
 off=len(xs)*n
 for row in [0,len(xs)-1]:
  for i in range(n):
   j=(i+1)%n;f=(row*n+i,off+row*n+i,off+row*n+j,row*n+j);faces.append(f if row==0 else tuple(reversed(f)))
 mesh=bpy.data.meshes.new('TacticalStock_MountSleeve');mesh.from_pydata(verts,[],faces);mesh.update();ring=bpy.data.objects.new('MeasuredMountSleeve',mesh);bpy.context.collection.objects.link(ring);parts=[ring]
 for f in ring.data.polygons:f.use_smooth=f.index<2*(len(xs)-1)*n
 def cube(name,loc,size):
  bpy.ops.mesh.primitive_cube_add(size=1,location=loc);a=bpy.context.object;a.name=name;a.dimensions=size;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);parts.append(a);return a
 if family=='AKM':
  a=cube('AKM_receiver_cap',(.0016,0,-.0025),(.005,.041,.038));bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.0135,depth=.015,location=(.0016,0,0),rotation=(0,math.pi/2,0));cut=bpy.context.object;active(a);mod=a.modifiers.new('Tube passage','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 if family=='QBZ191':
  frame=Matrix.Translation((.000688,.065,.0615))@Matrix.Rotation(math.pi/2,4,'Z');ob.data.transform(frame);ring.data.transform(frame)
  cube('QBZ_receiver_cap',(.000688,.0585,.0615),(.034,.014,.042));cube('QBZ_shoulder',(.000688,.0645,.0615),(.029,.006,.033))
 for a in parts:
  a.data.materials.clear();a.data.materials.append(adapter);active(a)
  if a!=ring:
   mod=a.modifiers.new('Mount edge radius','BEVEL');mod.width=.0005;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
  bm=bmesh.new();bm.from_mesh(a.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(a.data);bm.free()
  if not a.data.uv_layers:a.data.uv_layers.new(name='GeneratedUV0')
  a.data.uv_layers[0].name='GeneratedUV0'
  for f in a.data.polygons:
   axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
   for li in f.loop_indices:
    co=a.data.vertices[a.data.loops[li].vertex_index].co;a.data.uv_layers[0].data[li].uv=(co[axes[0]]/.1,co[axes[1]]/.1)
 active(ob)
 for a in parts:a.select_set(True)
 bpy.ops.object.join();uv=ob.data.uv_layers.new(name='ReceiverUV1');tile={'M4':(.12,.05),'AKM':(.12,.025),'QBZ191':(.1,.1)}[family]
 for f in ob.data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
  for li in f.loop_indices:
   co=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/tile[0],co[axes[1]]/tile[1])
 ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
 for other in bpy.context.scene.objects:
  if other!=ob:other.hide_render=True;other.hide_set(True)
 active(ob);out=P/family;out.mkdir(exist_ok=True);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'TacticalStock_Game_Editable.blend'))
 bpy.ops.export_scene.fbx(filepath=str(out/'SM_TacticalTelescopicStock.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 report['variants'][family]={'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons),'body_front_m':body_front,'mount_front_m':leading,'materials':[m.name for m in ob.data.materials],'asset':'/Game/Weapons/TacticalTelescopicStock20260914/'+family+'/SM_TacticalTelescopicStock'}
 bpy.data.objects.remove(ob,do_unlink=True);print('TACTICAL_VARIANT_EXPORTED',family,flush=True)
(P/'variants.json').write_text(json.dumps(report,indent=2))
