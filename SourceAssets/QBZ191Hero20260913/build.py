"""Author QBZ high/low surfaces, fresh UVs and baked PBR in Blender.

Uses supplied geometry and the existing QBZ rest/animation contracts.
No camera render, gameplay launch, or acceptance test is performed.
"""
import bpy,bmesh,json,math,zipfile,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector

O=Path(__file__).parent; S=O.parent
T=O/'Textures'; T.mkdir(exist_ok=True)
original_textures=O/'SourceTextures';original_textures.mkdir(exist_ok=True)
with zipfile.ZipFile('D:/FPS3D/qbz-191-free (1).zip') as archive:
 for entry in archive.infolist():
  if entry.filename.startswith('textures/') and entry.filename.endswith('.png'):
   (original_textures/Path(entry.filename).name).write_bytes(archive.read(entry))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191MagazineSeat20260913/QBZ191_MagazineSeat_Editable.blend'))
s=bpy.context.scene; rig=bpy.data.objects['SK_M4_Infima']; hands=bpy.data.objects['SK_Manny_Arms_Export']
root=rig.data.bones['WPN_root'].matrix_local.copy()
source_info=json.loads((S/'QBZ19120260912/components.json').read_text())[0]
components=source_info['components']; source_matrix=Matrix(source_info['matrix'])
with bpy.data.libraries.load(str(S/'QBZ19120260912/SourceInspect.blend'),link=False) as (a,b):b.objects=['QBZ']
raw=b.objects[0]
with bpy.data.libraries.load(str(S/'QBZ19120260912/QBZ191_Editable.blend'),link=False) as (a,b):b.objects=['QBZ191_Export']
bound=b.objects[0]

def collection(name):
 c=bpy.data.collections.new(name);s.collection.children.link(c);return c
ref_col=collection('QBZ_SOURCE_REFERENCE');hi_col=collection('QBZ_HIGH');low_col=collection('QBZ_LOW');cage_col=collection('QBZ_CAGE')
ref_col.objects.link(raw);raw.matrix_world=source_matrix;raw.name='QBZ_Original_OBJ_With_SplitNormals'
raw.hide_render=True;raw.hide_set(True)
bound.name='QBZ_Original_Bound_Reference';ref_col.objects.link(bound);bound.hide_render=True;bound.hide_set(True)
for ob in [bpy.data.objects['QBZ191_Export'],bpy.data.objects['QBZ191_Magazine_Export']]:
 ob.name+='_Previous'
 for c in list(ob.users_collection):c.objects.unlink(ob)
 ref_col.objects.link(ob);ob.hide_render=True;ob.hide_set(True)

rig.animation_data.action=bpy.data.actions['QBZ191_base_idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
s.frame_set(0);bpy.context.view_layer.update()
mag0=rig.pose.bones['WPN_root'].matrix.inverted()@rig.pose.bones['WPN_SOCKET_Magazine'].matrix
mag_rest=rig.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
seat_offset=Vector(json.loads((S/'QBZ191MagazineSeat20260913/authoring.json').read_text())['assembly_correction_root_m'])
seat=mag_rest@mag0.inverted()@Matrix.Translation(seat_offset)@mag0@mag_rest.inverted()
rig.data.pose_position='REST';bpy.context.view_layer.update()

def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]

def material(name,base,metal,rough,source=None,poly=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface'])
 coords=n.new('ShaderNodeTexCoord')
 noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=950 if poly else 1400
 noise.inputs['Detail'].default_value=2;l.new(coords.outputs['Object'],noise.inputs['Vector'])
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(x*.89 for x in base),1);ramp.color_ramp.elements[1].color=(*(x*1.09 for x in base),1)
 l.new(noise.outputs['Fac'],ramp.inputs[0]);base_out=ramp.outputs['Color']
 # Keep the supplied engraving/colour identity at low weight while replacing
 # the pervasive blotchy finish with authored, physically scaled materials.
 if source:
  tex=n.new('ShaderNodeTexImage');tex.image=source;tex.label='Original colour and markings reference'
  uv=n.new('ShaderNodeUVMap');uv.uv_map='SourceUV';l.new(uv.outputs['UV'],tex.inputs['Vector'])
  mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[0].default_value=.12 if poly else .18
  l.new(base_out,mix.inputs[1]);l.new(tex.outputs['Color'],mix.inputs[2]);base_out=mix.outputs[0]
 l.new(base_out,bs.inputs['Base Color'])
 mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.065 if poly else .035;l.new(noise.outputs['Fac'],mul.inputs[0])
 add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=rough;l.new(mul.outputs[0],add.inputs[0]);l.new(add.outputs[0],bs.inputs['Roughness'])
 bs.inputs['Metallic'].default_value=metal
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22 if poly else .12;bump.inputs['Distance'].default_value=.000013 if poly else .000004
 l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
 # ORM is baked as data, with a neutral occlusion channel; no moving-part AO
 # shadows are painted permanently onto the receiver or magazine.
 orm=n.new('ShaderNodeCombineColor');orm.mode='RGB';orm.inputs[0].default_value=1
 l.new(add.outputs[0],orm.inputs[1]);orm.inputs[2].default_value=metal
 m['bake_base_node']=base_out.node.name;m['bake_base_socket']=base_out.name;m['bake_orm_node']=orm.name
 m['micro_bump_node']=bump.name
 return m

images={}
for slot in raw.material_slots:
 for node in slot.material.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image:
   for original in original_textures.glob('*.png'):
    if node.image.name.startswith(original.name):
     node.image.filepath=str(original);node.image.reload();break
   key=('Magazine' if 'Magazine' in node.image.name else 'Body')+('_Normal' if '_Normal' in node.image.name else '_BaseColor' if 'BaseColor' in node.image.name else '')
   images[key]=node.image
   # Original material reference has direct, unattenuated source connections.
 for node in slot.material.node_tree.nodes:
  if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=1

materials={
 'Body':material('AUTH_QBZ_CoatedReceiver',(.025,.029,.033),.72,.30,images['Body_BaseColor']),
 'Polymer':material('AUTH_QBZ_Polymer',(.013,.015,.017),0,.49,images['Body_BaseColor'],True),
 'Magazine':material('AUTH_QBZ_MagazinePolymer',(.020,.022,.025),0,.43,images['Magazine_BaseColor'],True),
 'Steel':material('AUTH_QBZ_TreatedSteel',(.020,.023,.027),.88,.25,images['Body_BaseColor']),
 'Rail':material('AUTH_QBZ_RailFinish',(.025,.029,.033),.76,.28),
 'Sights':material('AUTH_QBZ_SightFinish',(.020,.024,.029),.72,.32),
 'SightInner':material('AUTH_QBZ_SightInner',(.006,.007,.008),.05,.72),
 'Rubber':material('AUTH_QBZ_Buttpad',(.008,.009,.010),0,.68,None,True)
}

def set_mat(ob,mat):
 ob.data.materials.clear();ob.data.materials.append(mat)
 for p in ob.data.polygons:p.material_index=0

groups={k:[] for k in ['Body','Polymer','Magazine','Steel','Rail','Sights']}
stats={'source_custom_normals':raw.data.has_custom_normals,'groups':{},'rebuilt_rails':[],'status':'authoring'}
component_for={v:i for i,c in enumerate(components) for v in c['ids']}
polys={i:[] for i in range(len(components))}
for p in raw.data.polygons:polys[component_for[p.vertices[0]]].append(p)

def component_mesh(index,name):
 ids=components[index]['ids'];imap={v:i for i,v in enumerate(ids)};ps=polys[index]
 v=[bound.data.vertices[i].co.copy() for i in ids]
 if index==93:v=[seat@x for x in v]
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],[[imap[j] for j in p.vertices] for p in ps]);me.update()
 uv=me.uv_layers.new(name='SourceUV');uv0=raw.data.uv_layers.active
 # An affine basis per rigid component carries the original split normals
 # through the same binding transform as its positions.
 basis_ids=ids if index in [85,89,93] else components[0]['ids']
 src=np.array([[*raw.data.vertices[i].co,1.] for i in basis_ids])
 dst=np.array([list(seat@bound.data.vertices[i].co if index==93 else bound.data.vertices[i].co) for i in basis_ids])
 affine=np.linalg.lstsq(src,dst,rcond=None)[0][:3,:].T
 normal_matrix=Matrix(affine.tolist()).inverted_safe().transposed()
 ns=[]
 for new,old in zip(me.polygons,ps):
  new.use_smooth=old.use_smooth
  for li,oi in zip(new.loop_indices,old.loop_indices):
   uv.data[li].uv=uv0.data[oi].uv
   ns.append((normal_matrix@raw.data.corner_normals[oi].vector).normalized())
 me.normals_split_custom_set(ns)
 ob=bpy.data.objects.new(name,me);low_col.objects.link(ob)
 ob['source_component']=index;ob['bone']='WPN_SOCKET_Magazine' if index==93 else 'WPN_Trigger' if index==85 else 'WPN_ChargingHandle' if index==89 else 'WPN_root'
 return ob

def bevel(ob,width,segments):
 mod=ob.modifiers.new('Authored edge profile','BEVEL');mod.limit_method='ANGLE';mod.angle_limit=math.radians(38)
 mod.width=width;mod.segments=segments;mod.use_clamp_overlap=True;mod.harden_normals=True
 wn=ob.modifiers.new('Planar face normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50

def bake_pair(ob,group,width=.00014,structural=True):
 high=ob.copy();high.data=ob.data.copy();high.name=ob.name+'_HIGH';hi_col.objects.link(high)
 if width:
  bevel(ob,width,2);bevel(high,width,6)
  if structural:high.modifiers.remove(high.modifiers[-1])
 # Reproject the original structural normal from its original UV and normal
 # basis onto the final low mesh; its strength is not globally flattened.
 if structural and ob.get('source_component') is not None:
  mat=high.data.materials[0].copy();high.data.materials[0]=mat
  n=mat.node_tree.nodes;l=mat.node_tree.links
  uv=n.new('ShaderNodeUVMap');uv.uv_map='SourceUV';tex=n.new('ShaderNodeTexImage')
  tex.image=images['Magazine_Normal' if group=='Magazine' else 'Body_Normal'];l.new(uv.outputs['UV'],tex.inputs['Vector'])
  normal=n.new('ShaderNodeNormalMap');normal.uv_map='SourceUV';l.new(tex.outputs['Color'],normal.inputs['Color'])
  bump=n[mat['micro_bump_node']];l.new(normal.outputs[0],bump.inputs['Normal'])
 groups[group].append((ob,high))
 return ob,high

for i in range(len(components)):
 if i in [21,22,80,81,82,94]:continue
 group='Magazine' if i==93 else 'Polymer' if i in [91,92] else 'Steel' if i in [13,16,17,18,19,20,85,89,90] or 26<=i<=79 else 'Body'
 ob=component_mesh(i,'QBZ_'+{0:'Receiver',11:'Handguard',91:'Stock',92:'PistolGrip',93:'Magazine',89:'ChargingHandle'}.get(i,'Part'+str(i)))
 set_mat(ob,materials[group])
 # Source surface cleanup is limited to the large receiver/handguard faces;
 # UV boundaries and original shape are retained in the authoring base.
 if i in [0,11]:
  bm=bmesh.new();bm.from_mesh(ob.data)
  bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(.08),verts=list(bm.verts),edges=list(bm.edges),delimit={'UV','MATERIAL','SEAM'})
  bm.to_mesh(ob.data);bm.free()
 # Distinct radii for polymer, sheet metal and the exposed receiver edges.
 width=.00032 if i==0 else .00024 if i==11 else .00030 if group in ['Polymer','Magazine'] else .00011
 bake_pair(ob,group,width)

def geometry(name,vertices,faces,col=low_col):
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for f in bm.faces:f.smooth=True
 for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(38))
 bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(name,me);col.objects.link(ob);ob['bone']='WPN_root';return ob

def prism(name,profile,ystart,yend):
 count=len(profile);v=[root@Vector((x,y,z)) for y in [ystart,yend] for x,z in profile]
 f=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]+[(j,(j+1)%count,(j+1)%count+count,j+count) for j in range(count)]
 return geometry(name,v,f)

rail_inputs=json.loads((O/'author_inputs.json').read_text())['rails']
for index,lo,hi in [(21,-.328487,-.17052),(22,-.17027,-.012373)]:
 cx=.000688
 # Cross-section follows the supplied crown/undercut envelope and keeps the
 # precise existing top installation plane. Rear/front seam remains separate.
 profile=[(cx-.0069,.085919),(cx+.0069,.085919),(cx+.0069,.0890),(cx+.010765,.0921),(cx+.010765,.094205),(cx-.010765,.094205),(cx-.010765,.0921),(cx-.0069,.0890)]
 ob=prism('QBZ_Rail_Base_'+str(index),profile,lo,hi);set_mat(ob,materials['Rail']);bake_pair(ob,'Rail',.00013,False)
 intervals=[]
 for face in rail_inputs[str(index)]:
  vv=face['v']
  if min(v[2] for v in vv)<.09645:continue
  a=max(lo,min(v[1] for v in vv));b=min(hi,max(v[1] for v in vv))
  if b-a>.0005:intervals.append((a,b))
 intervals.sort();merged=[]
 for a,b in intervals:
  if merged and a<=merged[-1][1]+.00002:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 crown=[(cx-.010765,.09407),(cx+.010765,.09407),(cx+.00733,.096473),(cx-.00733,.096473)]
 for j,(a,b) in enumerate(merged):
  ob=prism('QBZ_Rail_Tooth_'+str(index)+'_'+str(j),crown,a,b);set_mat(ob,materials['Rail']);bake_pair(ob,'Rail',.00010,False)
 stats['rebuilt_rails'].append({'component':index,'range':[lo,hi],'crown':.096473,'slots':len(merged)})

# Keep the established sight aperture, hinge position, and separate moving
# object. Only the surface finish, UVs and small hinge-head detail are added.
sight_heads=[]
for name in ['SM_QBZ191_RearSight','SM_QBZ191_FrontSight']:
 ob=bpy.data.objects[name];ob['is_static_head']=True
 for c in list(ob.users_collection):c.objects.unlink(ob)
 low_col.objects.link(ob)
 inner={i for i,m in enumerate(ob.data.materials) if m.name=='M_QBZ191_Irons_Inner'}
 old_indices=[p.material_index for p in ob.data.polygons]
 ob.data.materials.clear();ob.data.materials.append(materials['Sights']);ob.data.materials.append(materials['SightInner'])
 for p,i in zip(ob.data.polygons,old_indices):p.material_index=1 if i in inner else 0
 # Baking objects use local hinge coordinates, outside bone transforms.
 parent_state={'parent':ob.parent,'parent_type':ob.parent_type,'parent_bone':ob.parent_bone,'inverse':ob.matrix_parent_inverse.copy(),'basis':ob.matrix_basis.copy()}
 ob['saved_parent_state']='WPN_root hinge';ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 for drv in ob.animation_data.drivers if ob.animation_data else []:drv.mute=True
 ob,high=bake_pair(ob,'Sights',0,False);sight_heads.append((ob,parent_state))

# Carry the existing fixed rail feet/axles, preserving their exact contact.
previous=bpy.data.objects['QBZ191_Export_Previous']
fixed=previous.copy();fixed.data=previous.data.copy();fixed.name='QBZ_Sight_FixedMounts';low_col.objects.link(fixed)
fixed.parent=None;fixed.matrix_world=Matrix.Identity(4);fixed.modifiers.clear();fixed.hide_set(False)
allowed={i for i,m in enumerate(fixed.data.materials) if m.name in ['M_QBZ191_Irons_Machined','M_QBZ191_Irons_Inner']}
bm=bmesh.new();bm.from_mesh(fixed.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in allowed],context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(fixed.data);bm.free()
fixed['bone']='WPN_root';set_mat(fixed,materials['Sights']);bake_pair(fixed,'Sights',0,False)

def apply_geometry_modifiers(ob):
 activate([ob])
 for mod in list(ob.modifiers):
  if mod.type!='ARMATURE':bpy.ops.object.modifier_apply(modifier=mod.name)
 tri=ob.modifiers.new('Final bake triangulation','TRIANGULATE');tri.keep_custom_normals=True
 bpy.ops.object.modifier_apply(modifier=tri.name)

def image_target(name,size,data=False,normal=False):
 im=bpy.data.images.new(name,width=size,height=size,alpha=False,float_buffer=False)
 im.colorspace_settings.name='Non-Color' if data else 'sRGB'
 im.generated_color=(.5,.5,1,1) if normal else (1,.5,0,1) if data else (0,0,0,1)
 return im

def emit_mode(high,kind):
 for m in high.data.materials:
  n=m.node_tree.nodes;l=m.node_tree.links;out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
  if kind=='Normal':l.new(next(x for x in n if x.type=='BSDF_PRINCIPLED').outputs[0],out.inputs['Surface'])
  else:
   em=n.get('BAKE_EMISSION') or n.new('ShaderNodeEmission');em.name='BAKE_EMISSION'
   src=n[m['bake_base_node']].outputs[m['bake_base_socket']] if kind=='BaseColor' else n[m['bake_orm_node']].outputs[0]
   l.new(src,em.inputs['Color']);l.new(em.outputs[0],out.inputs['Surface'])

def merged_bake_geometry(objects,name,evaluated):
 copies=[];dg=bpy.context.evaluated_depsgraph_get()
 for ob in objects:
  me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg) if evaluated else ob.data.copy()
  copy=bpy.data.objects.new(name+'_part',me);s.collection.objects.link(copy);copies.append(copy)
 activate(copies);bpy.ops.object.join();copy=bpy.context.object;copy.name=name;return copy

s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=False
s.render.bake.margin=16;s.render.bake.use_selected_to_active=True;s.render.bake.use_clear=False
s.render.bake.cage_extrusion=.001;s.render.bake.max_ray_distance=.004
s.render.bake.normal_space='TANGENT';s.render.bake.normal_r='POS_X';s.render.bake.normal_g='POS_Y';s.render.bake.normal_b='POS_Z'
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for device in prefs.devices:device.use=device.type=='OPTIX'
 if any(d.use for d in prefs.devices):s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'

manifest={}; runtime=[]
for ob in s.objects:
 if ob.type=='MESH':ob.hide_render=True

for group,pairs in groups.items():
 size=4096 if group=='Body' else 2048 if group in ['Polymer','Magazine','Rail','Steel'] else 1024
 # Modifier stacks are preserved on the HIGH collection in the final source;
 # LOW receives the exact geometry used for the normal bake and export.
 for low,high in pairs:apply_geometry_modifiers(low)
 lows=[x[0] for x in pairs]
 for ob in lows:
  layer=ob.data.uv_layers.new(name='HeroUV');ob.data.uv_layers.active=layer;layer.active_render=True
 activate(lows);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.006,area_weight=.8,correct_aspect=True,scale_to_bounds=False)
 bpy.ops.uv.pack_islands(rotate=True,margin=.006);bpy.ops.object.mode_set(mode='OBJECT')
 # One low target material per mesh prevents shared source shader nodes from
 # accidentally changing the source shading while textures are being baked.
 for low,high in pairs:
  target=bpy.data.materials.new('BAKE_TARGET_'+low.name);target.use_nodes=True
  set_mat(low,target)
 maps={kind:image_target('T_QBZ_Hero_'+group+'_'+kind,size,kind!='BaseColor',kind=='Normal') for kind in ['BaseColor','ORM','Normal']}
 if group!='Sights':
  for low,high in pairs:high.hide_set(False)
  bpy.context.view_layer.update()
  bake_low=merged_bake_geometry(lows,'TEMP_BAKE_LOW',False)
  bake_high=merged_bake_geometry([x[1] for x in pairs],'TEMP_BAKE_HIGH',True)
  target=bpy.data.materials.new('BAKE_TARGET_GROUP_'+group);target.use_nodes=True;set_mat(bake_low,target)
  baking_pairs=[(bake_low,bake_high)]
  for low,high in pairs:high.hide_set(True)
 else:baking_pairs=pairs
 for kind,im in maps.items():
  for low,high in baking_pairs:
   low.hide_render=False;high.hide_render=False;high.hide_set(False)
   target=low.data.materials[0];n=target.node_tree.nodes;tex=n.get('BAKE_TARGET') or n.new('ShaderNodeTexImage');tex.name='BAKE_TARGET';tex.image=im;n.active=tex
   emit_mode(high,kind);activate([high,low]);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT')
   low.hide_render=True;high.hide_render=True;high.hide_set(True)
  # Tangent normals are exported as OpenGL from Blender; the UE texture import
  # flips green once. The image name states the convention explicitly.
  suffix='NormalGL' if kind=='Normal' else kind
  im.filepath_raw=str(T/('T_QBZ_Hero_'+group+'_'+suffix+'.png'));im.file_format='PNG';im.save()
  print('QBZ_HERO_BAKED',group,kind,flush=True)
 for low,high in pairs:emit_mode(high,'Normal')
 if group!='Sights':
  bpy.data.objects.remove(bake_low,do_unlink=True);bpy.data.objects.remove(bake_high,do_unlink=True)
 # A directly wired material for the new UV set and fresh bake.
 m=bpy.data.materials.new('M_QBZ191_Hero_'+group);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
 for kind,im in maps.items():
  tex=n.new('ShaderNodeTexImage');tex.image=im
  if kind=='BaseColor':l.new(tex.outputs[0],bs.inputs['Base Color'])
  elif kind=='Normal':normal=n.new('ShaderNodeNormalMap');normal.uv_map='HeroUV';l.new(tex.outputs[0],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
  else:
   sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs[0],sep.inputs[0]);l.new(sep.outputs[1],bs.inputs['Roughness']);l.new(sep.outputs[2],bs.inputs['Metallic'])
 for low,high in pairs:
  set_mat(low,m)
  # FBX uses the first UV channel; move final UV to UV0 and keep source UV only
  # on HIGH/reference objects, where it remains the original bake input.
  for uv in list(low.data.uv_layers):
   if uv.name!='HeroUV':low.data.uv_layers.remove(uv)
  cage=low.copy();cage.data=low.data.copy();cage.name=low.name+'_CAGE';cage_col.objects.link(cage)
  for v in cage.data.vertices:v.co+=v.normal*.001
  cage.display_type='WIRE';cage.hide_render=True;cage.hide_set(True)
  low.hide_render=False;low.hide_set(False)
  if not low.get('is_static_head'):
   bone=low.get('bone','WPN_root');low.vertex_groups.clear();low.vertex_groups.new(name=bone).add(list(range(len(low.data.vertices))),1,'REPLACE')
   low.parent=rig;low.matrix_parent_inverse=Matrix.Identity(4);low.matrix_basis=Matrix.Identity(4);low.modifiers.new('QBZ existing rig','ARMATURE').object=rig
   runtime.append(low)
 manifest[group]={'size':size,'material':m.name,'textures':{k:str(v.filepath_raw) for k,v in maps.items()},'objects':[ob.name for ob in lows]}
 stats['groups'][group]={'low_triangles':sum(len(x.data.polygons) for x in lows),'parts':len(lows)}
 (O/'textures.json').write_text(json.dumps(manifest,indent=2))

# Export heads at the local hinge origin before restoring their editor drivers.
def export(name,objects,kinds):
 activate(objects)
 bpy.ops.export_scene.fbx(filepath=str(O/(name+'.fbx')),use_selection=True,object_types=kinds,axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)

for ob,state in sight_heads:
 export(ob.name,[ob],{'MESH'})
 ob.parent=state['parent'];ob.parent_type=state['parent_type'];ob.parent_bone=state['parent_bone'];ob.matrix_parent_inverse=state['inverse'];ob.matrix_basis=state['basis']
 for drv in ob.animation_data.drivers if ob.animation_data else []:drv.mute=False
sys.path.insert(0,str(O))
from export_mesh import export_joined
export_joined(rig,hands,runtime,O)
rig.data.pose_position='POSE';s.frame_set(0)
for ob in hi_col.objects:ob.hide_render=True;ob.hide_set(True)
ref_col.hide_render=True;cage_col.hide_render=True
hands.hide_set(False);hands.hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Hero_Editable.blend'))
stats['status']='authored, texture baked and exported; no preview or runtime test'
stats['preserved']=['private rest skeleton','MagazineSeat reloads','Refined grip families','folding sight pivots','rail crown','magazine bind correction']
(O/'authoring.json').write_text(json.dumps(stats,indent=2));print('QBZ_HERO_AUTHORING_COMPLETE',flush=True)
