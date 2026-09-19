"""Render isolated current accessory geometry; never alter original scenes or game meshes."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parent/'AttachmentIconAudit20260914'));sys.path.insert(0,str(P))
from icon_geometry import open_source,level_frame,filter_mesh
from materials import restore_runtime_finish
M=json.loads((P/'render_manifest.json').read_text());O=P/'Icons';O.mkdir(exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
rows=[r for r in M['renders'] if not args or r['key'] in args]
bind_frame=None
def m4_frame():
 global bind_frame
 if bind_frame is None:
  reference=json.loads((P/'frame_reference.json').read_text());rear=Matrix(reference['rear_sight_matrix']);front=Matrix(reference['front_sight_matrix'])
  z=rear.to_3x3().col[2].normalized();f=front.translation-rear.translation;f-=z*f.dot(z);f.normalize();x=-f;y=z.cross(x).normalized();z=x.cross(y).normalized();bind_frame=Matrix(((*x,0),(*y,0),(*z,0),(0,0,0,1)))
 return bind_frame

def frame_for(row):
 if row['frame']=='measured':return Matrix(row['matrix'])
 if row['frame']=='rig':return level_frame(bpy.data.objects[row['rig']])
 if row['frame']=='root':
  rig=bpy.data.objects[row['rig']]
  return Matrix.Rotation(-math.pi/2,4,'Z')@(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
 if row['frame']=='m4_bind':return m4_frame()
 if row['frame']=='fit':return Matrix.Rotation(math.pi,4,'Z')@Matrix(json.loads(Path(row['fit']).read_text())['grip_matrix']).inverted()
 return Matrix.Rotation({'X':math.pi,'Y':math.pi/2,'-Y':-math.pi/2,'none':0}[row['frame']],4,'Z')

def m4_finish(ob,key):
 # Same receiver coating source / UV as the current attachment finish variants.
 for i,old in enumerate(ob.data.materials):
  if not old:continue
  label=old.name.lower()
  target=('fastener' in label if 'drum' in key else 'saddle' in label if 'handstop' in key else 'body' in label or 'holosight' in label)
  if not target:continue
  mat=old.copy();ob.data.materials[i]=mat;mat.use_nodes=True
  bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if not bs:continue
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P.parent/'WeaponAttachmentFinish20260913/Textures/T_M4_Receiver_BaseColor.png'),check_existing=True)
  uv=mat.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='ReceiverFinishPhysicalUV';mat.node_tree.links.new(uv.outputs['UV'],tex.inputs['Vector']);mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
  for pin,value in [('Metallic',.8),('Roughness',.38)]:
   for link in list(bs.inputs[pin].links):mat.node_tree.links.remove(link)
   bs.inputs[pin].default_value=value

def empty_state():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 mat=bpy.data.materials.new('Neutral empty state');mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.42,.48,.54,1);bs.inputs['Metallic'].default_value=.1;bs.inputs['Roughness'].default_value=.55
 bpy.ops.mesh.primitive_torus_add(major_radius=.65,minor_radius=.055,major_segments=96,minor_segments=12,rotation=(math.pi/2,0,0));ring=bpy.context.object;ring.name='EmptyStateRing';ring.data.materials.append(mat)
 bpy.ops.mesh.primitive_cube_add(size=1);bar=bpy.context.object;bar.name='EmptyStateMinus';bar.scale=(.66,.09,.08);bar.data.materials.append(mat)
 return [ring,bar]

for row in rows:
 key=row['key'];print('ICON_BEGIN',key,flush=True)
 if row['source']=='state:empty':obs=empty_state()
 else:
  open_source(row['source'])
  # Raw model vertices are already authored in bind/world or a recorded fitting frame.
  for rig in [o for o in bpy.data.objects if o.type=='ARMATURE']:rig.data.pose_position='REST'
  bpy.context.view_layer.update();frame=frame_for(row);obs=[]
  for name in row['objects']:
   original=bpy.data.objects[name];mesh=original.data.copy()
   for i,slot in enumerate(original.material_slots):mesh.materials[i]=slot.material
   filter_mesh(mesh,row.get('selectors',{}).get(name))
   transform=frame@Matrix.Translation(Vector(row.get('offsets',{}).get(name,[0,0,0])))@original.matrix_world
   mesh.transform(transform);mesh.update()
   ob=bpy.data.objects.new('Icon_'+name,mesh);bpy.context.scene.collection.objects.link(ob);obs.append(ob)
   if row.get('finish')=='M4':m4_finish(ob,key)
   restore_runtime_finish(ob,row,P)
  for ob in list(bpy.data.objects):
   if ob not in obs:bpy.data.objects.remove(ob,do_unlink=True)
 for ob in obs:ob.hide_render=False;ob.hide_set(False)
 bpy.context.view_layer.update()
 pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 if not pts:raise RuntimeError('Empty model '+key)
 lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
 center=(lo+hi)*.5;scale=2/max(hi.x-lo.x,hi.z-lo.z)
 for o in obs:o.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(-center)@o.matrix_world
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
 for layer in s.view_layers:
  layer.material_override=None
 try:
  prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
  for device in prefs.devices:device.use=device.type=='OPTIX'
  if any(d.use for d in prefs.devices):s.cycles.device='GPU'
 except Exception as err:print('CYCLES_CPU_FALLBACK',str(err),flush=True)
 s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100
 s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA';s.render.image_settings.color_depth='8';s.render.use_compositing=False;s.render.use_sequencer=False;s.render.use_border=False
 s.view_settings.view_transform='AgX';s.view_settings.exposure=.35
 s.world=bpy.data.worlds.new('AcceptedAttachmentIconStudio');s.world.use_nodes=True
 bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.36,.36,.36,1);bg.inputs[1].default_value=.55
 for loc,energy,size in [((-1.5,-3,3),700,4),((2,1.5,2.5),950,3),((-3,-1,-.5),180,2),((0,-4,.2),110,3)]:
  bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=(0,-5,0));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.36;s.camera=cam
 s.render.filepath=str(O/(key+'.png'));bpy.data.orphans_purge(do_recursive=True)
 missing=[]
 for im in bpy.data.images:
  if im.source=='FILE' and im.users and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists():missing.append(im.filepath)
 if missing:raise RuntimeError('Unresolved source textures '+key+': '+str(missing))
 bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/(key+'.blend')))
 bpy.ops.render.render(write_still=True)
 (O/(key+'.json')).write_text(json.dumps(dict(row,front='left (-X)',up='+Z',projection='orthographic horizontal side, camera looking +Y',size=[1024,1024],transparent=True,source_bounds=[list(lo),list(hi)],triangles=sum(sum(len(f.vertices)-2 for f in o.data.polygons) for o in obs),material_note='Real source textures retained. Receiver coating in Blender approximates UE Phong conversion using the same coating source.' if row.get('finish') else 'Real source materials retained.'),ensure_ascii=False,indent=2),encoding='utf-8')
 print('ICON_DONE',key,flush=True)
print('ICONS_COMPLETE',len(rows),flush=True)
