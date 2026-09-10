import bpy,bmesh,math,json,os
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).parent
SOURCE_ROOT=Path(os.environ.get('GODOT_SOURCE_ROOT','E:/3d/trash/e-drive-repositories-20260910/3d/3-dfps'))
sources={'suppressor':'akm/suppressor_01.glb','brake':'muzzle_brake/brake_01.glb','titanium_brake':'titanium_brake_candidate/titanium_brake.glb'}
report={}
def material(name,color,rough,metal):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
def tube(name,profile,mat,n=96):
 # Closed visual shell with a clear bore, retaining the original source silhouette.
 verts=[(r*math.cos(2*math.pi*i/n),y,r*math.sin(2*math.pi*i/n)) for y,r in profile for i in range(n)]
 faces=[]
 for j in range(len(profile)):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);o.data.materials.append(mat);return o
def bevel(o,width):
 bpy.context.view_layer.objects.active=o
 mod=o.modifiers.new('Machined edge radii','BEVEL');mod.width=width;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.25
 bpy.ops.object.modifier_apply(modifier=mod.name)
def light_scene(objects,key):
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1000;s.render.resolution_y=750;s.render.resolution_percentage=100
 s.world=bpy.data.worlds.new('Workshop');s.world.color=(.055,.065,.08)
 pts=[o.matrix_world@v.co for o in objects for v in o.data.vertices];lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)]);c=(lo+hi)*.5;r=max(hi-lo)
 bpy.ops.object.camera_add(location=c+Vector((r*1.6,r*1.2,r*.8)));cam=bpy.context.object;cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=r*1.4;s.camera=cam
 for pos,power in [((1,-1,2),14),((-1,1,.8),8)]:
  bpy.ops.object.light_add(type='AREA',location=c+Vector(pos)*r);o=bpy.context.object;o.data.energy=power;o.data.size=r*1.5;o.rotation_euler=(c-o.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(OUT/(key+'-upgraded.png'));bpy.ops.render.render(write_still=True)
for key,path in sources.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 shell=material('RifleMetal',(.07,.075,.07),.46,.8);dark=material('RecessMetal',(.025,.028,.027),.55,.7);accent=material('TitaniumTrim',(.22,.16,.075),.42,.8)
 parts=[]
 if key=='suppressor':
  # Rebuild the original 16-sided cylinders as a 96-sided continuous hollow body.
  parts.append(tube('ContinuousSuppressorShell',[(-.005,.017),(-.003,.018),(.020,.018),(.023,.0225),(.026,.023),(.173,.023),(.179,.0215),(.185,.0215),(.186,.020),(.186,.0055),(.177,.0055),(.171,.0185),(.025,.0185),(.019,.011),(-.005,.011)],shell))
  for y in [.035,.054,.073,.092,.111]:parts.append(tube('OriginalGripRing',[(y-.003,.0229),(y-.002,.024),(y+.002,.024),(y+.003,.0229)],shell))
  for y in [.145,.149,.153,.157]:parts.append(tube('FineMachiningRing',[(y-.0004,.02295),(y-.0002,.02325),(y+.0002,.02325),(y+.0004,.02295)],dark))
  parts.append(tube('FrontCapLip',[(.181,.0214),(.182,.022),(.184,.022),(.185,.0214)],shell))
  for o in parts:bevel(o,.00018)
 else:
  source_file=SOURCE_ROOT/'assets/models/attachments'/path
  assert source_file.is_file(), 'Set GODOT_SOURCE_ROOT to the restored Godot archive: '+str(source_file)
  bpy.ops.import_scene.gltf(filepath=str(source_file))
  parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
  for o in parts:
   o.data.transform(o.matrix_world);o.matrix_world.identity();o.parent=None
   old=o.data.materials[0].name if o.data.materials else ''
   mat=accent if key=='titanium_brake' and ('Gold' in o.name or 'Inlay' in o.name or 'Reveal' in o.name) else dark if 'Interior' in o.name or 'Channel' in o.name or 'Groove' in o.name else shell
   o.data.materials.clear();o.data.materials.append(mat)
   for face in o.data.polygons:face.material_index=0
  bpy.ops.object.select_all(action='DESELECT')
  for o in parts:o.select_set(True)
  bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;parts=[o]
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
  bevel(o,.00028 if key=='brake' else .00018)
  # Retain machined planes and all open side ports while increasing surface density.
  # Keep the source triangulation of faces containing holes. Dissolving those
  # faces into ngons can incorrectly cap the bore on FBX triangulation.
  rear=.0185 if key=='brake' else .017
  radius=.016 if key=='brake' else .018
  for y in [rear,rear+.0015]:parts.append(tube('PrecisionMountBand',[(y-.0003,radius-.00015),(y-.00015,radius+.0002),(y+.00015,radius+.0002),(y+.0003,radius-.00015)],shell))
 for o in parts:
  if o.data.has_custom_normals:
   bpy.context.view_layer.objects.active=o
   try:bpy.ops.mesh.customdata_custom_splitnormals_clear()
   except Exception:pass
  for f in o.data.polygons:f.use_smooth=True
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
  for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle(0)<.6
  bm.to_mesh(o.data);bm.free()
  if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
  # Map to one clean metal patch of the actual rifle atlas, not its UV-specific bore normals.
  for f in o.data.polygons:
   for li in f.loop_indices:
    p=o.data.vertices[o.data.loops[li].vertex_index].co
    o.data.uv_layers.active.data[li].uv=(.42+.08*(math.atan2(p.z,p.x)/(2*math.pi)+.5),.42+.10*((p.y+.01)/.21))
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SM_M4_'+key
 tris=sum(len(f.vertices)-2 for f in mesh.data.polygons)
 report[key]={'triangles':tris,'source_triangles':{'suppressor':1728,'brake':1688,'titanium_brake':9632}[key],'length_m':max(v.co.y for v in mesh.data.vertices),'materials':[m.name for m in mesh.data.materials]}
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(key+'-editable.blend')))
 bpy.ops.export_scene.fbx(filepath=str(OUT/(mesh.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
 light_scene([mesh],key)
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909/M4_FoldingSights_Editable.blend')
rig=bpy.data.objects['SK_M4_Infima'];flash=bpy.data.objects['M4_Flash Hider Unreal_Export'];points=[v.co for v in flash.data.vertices]
axis=(rig.data.bones['WPN_FrontSight'].head_local-rig.data.bones['WPN_RearSight'].head_local).normalized();muzzle=rig.data.bones['WPN_SOCKET_Muzzle'].head_local
rear=min(p.dot(axis) for p in points);end=max(p.dot(axis) for p in points)
report['fit']={'factory_length_cm':(end-rear)*100,'rear_from_socket_cm':(rear-muzzle.dot(axis))*100,'axis':list(axis),'flash_materials':[m.name for m in flash.data.materials]}
(OUT/'build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
