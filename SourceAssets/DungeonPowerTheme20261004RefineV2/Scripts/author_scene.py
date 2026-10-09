"""Build editable new architecture/heroes and export portable FBX in background.
No rendering, UE, gameplay generation or acceptance tests. Existing asset files
are loaded only when portable References/reuse-assets.json becomes available.
"""
import bpy,bmesh,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/'Scripts';OUT=ROOT/'Authored';sys.path.insert(0,str(SCRIPT))
import geometry as g
from architecture import architecture
from machinery import build_generator
from refined_core import build_core
from refined_console import build_console
CFG=json.loads((ROOT/'Config/scene.json').read_text('utf8'));MATDEF=json.loads((ROOT/'Config/materials.json').read_text('utf8'));ATLAS=json.loads((OUT/'atlas.json').read_text('utf8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.world=bpy.data.worlds.new('PowerCenter_WorkingWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.08,.09,.085,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.3
MATS={}
for role,m in MATDEF.items():
 mat=bpy.data.materials.new('PW_'+role);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*m['basecolor_linear'],1);bs.inputs['Roughness'].default_value=m['roughness'];bs.inputs['Metallic'].default_value=m['metallic'];mat.diffuse_color=(*m['basecolor_linear'],1)
 mat['ue_material_path']=m.get('existing_ue_path',CFG['ue_base']+'/Materials/M_Power_'+role);mat['material_role']=role
 textures=m.get('textures',{});texture_nodes={};normal_color_source=None
 for key,path in textures.items():
  convention=path.get('normal_convention') if isinstance(path,dict) else None
  if isinstance(path,dict):path=path['path']
  p=ROOT/path
  if not p.exists():raise FileNotFoundError('Required authored texture '+str(p))
  im=bpy.data.images.load(str(p),check_existing=True);node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;node.label=key;texture_nodes[key]=node
  if key=='basecolor':mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
  elif key=='normal':
   im.colorspace_settings.name='Non-Color';normal_color_source=node.outputs['Color']
   if convention=='DirectX':
    split=mat.node_tree.nodes.new('ShaderNodeSeparateColor');combine=mat.node_tree.nodes.new('ShaderNodeCombineColor');inv=mat.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;mat.node_tree.links.new(normal_color_source,split.inputs['Color']);mat.node_tree.links.new(split.outputs['Red'],combine.inputs['Red']);mat.node_tree.links.new(split.outputs['Green'],inv.inputs[1]);mat.node_tree.links.new(inv.outputs[0],combine.inputs['Green']);mat.node_tree.links.new(split.outputs['Blue'],combine.inputs['Blue']);normal_color_source=combine.outputs['Color']
   normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(normal_color_source,normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
  elif key=='orm':
   im.colorspace_settings.name='Non-Color';sep=mat.node_tree.nodes.new('ShaderNodeSeparateColor');mat.node_tree.links.new(node.outputs['Color'],sep.inputs['Color']);mat.node_tree.links.new(sep.outputs['Green'],bs.inputs['Roughness']);mat.node_tree.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 if 'labeloverlay' in texture_nodes:
  overlay=texture_nodes['labeloverlay'];mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mat.node_tree.links.new(overlay.outputs['Alpha'],mix.inputs[0]);mat.node_tree.links.new(texture_nodes['basecolor'].outputs['Color'],mix.inputs[1]);mat.node_tree.links.new(overlay.outputs['Color'],mix.inputs[2]);mat.node_tree.links.new(mix.outputs['Color'],bs.inputs['Base Color'])
  if 'normal' in texture_nodes:
   flat=mat.node_tree.nodes.new('ShaderNodeMixRGB');mat.node_tree.links.new(overlay.outputs['Alpha'],flat.inputs[0]);mat.node_tree.links.new(normal_color_source,flat.inputs[1]);flat.inputs[2].default_value=(.5,.5,1,1);mat.node_tree.links.new(flat.outputs['Color'],normal.inputs['Color'])
 if m.get('emissive_strength',0)>0:
  bs.inputs['Emission Strength'].default_value=m['emissive_strength']
  if m.get('emissive_from_basecolor') and bs.inputs['Base Color'].is_linked:mat.node_tree.links.new(bs.inputs['Base Color'].links[0].from_socket,bs.inputs['Emission Color'])
 MATS[role]=mat
 if role in CFG.get('required_material_roles',[]):mat.use_fake_user=True
architecture(g,CFG,ATLAS)
g.ROOM='GeneratorPrototype';build_generator(g)
g.ROOM='StoragePrototype';build_core(g,atlas=ATLAS,scale=1.65)
g.ROOM='ConsolePrototype';build_console(g,ATLAS)
# Store originals in metre-space, grouped by functional/collision ownership.
origins={r['id']:r['origin_m'] for r in CFG['rooms']+CFG['connectors']}
hero_specs={'GeneratorPrototype':dict(name='SM_Power_Generator',display=[28,-4.25,.28]),'StoragePrototype':dict(name='SM_Power_Accumulator',display=[origins['AccumulatorControl'][0],0,.20]),'ConsolePrototype':dict(name='SM_Power_ControlConsole_Refined',display=[25.40,10.04,2.4])}
# Machinery functions use one production group. Combine all groups if an author
# uses additional small-part groups; materials are captured before slot reorder.
for room in hero_specs:
 keys=[k for k in g.G if k[0]==room]
 if len(keys)>1:
  merged=dict(v=[],f=[],m=[],uv=[],smooth=[]);hulls=[]
  for key in keys:
   src=g.G.pop(key);off=len(merged['v']);merged['v'].extend(src['v']);merged['f'].extend(tuple(off+i for i in f) for f in src['f'])
   for field in ('m','uv','smooth'):merged[field].extend(src[field])
   hulls.extend(g.C.pop(key,[]))
  g.G[(room,'Machine')]=merged;g.C[(room,'Machine')]=hulls
record=[];created={};collection=bpy.data.collections.new('New_Authored_Architecture');scene.collection.children.link(collection)
collcol=bpy.data.collections.new('UCX_Authoring_Hulls');scene.collection.children.link(collcol)
for (room,kind),data in g.G.items():
 if not data['f']:continue
 name=hero_specs[room]['name'] if room in hero_specs else 'SM_Power_'+room+'_'+kind
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);names=list(dict.fromkeys(data['m']))
 for role in names:mesh.materials.append(MATS[role])
 uv=mesh.uv_layers.new(name='UVMap');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
 # Creating a corner attribute reallocates mesh custom data. Reacquire the UV
 # layer afterwards so atlas coordinates are written into the current buffer.
 uv=mesh.uv_layers['UVMap']
 for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
  face.material_index=names.index(role);face.use_smooth=smooth
  dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))];scale=MATDEF[role].get('uv_meters_override',MATDEF[role].get('uv_meters',1.0))
  for ci,li in enumerate(face.loop_indices):
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[ci] if coords else (p[dims[0]]/scale,p[dims[1]]/scale)
   wear=.035+.14*math.exp(-max(0,p.z)/.23);age.data[li].color=(wear,0,0,1)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 if kind not in ('Signs','Markings'):
  bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.dissolve_degenerate(bm,dist=.000005,edges=list(bm.edges));bm.to_mesh(mesh);bm.free()
 if kind in ('Structure','FloorFinish','RoofFrame','Machine','Trim','GalleryDeck','ControlRoom','Equipment','DadoBacking'):
  bevel=obj.modifiers.new('Fabricated edge radii','BEVEL');bevel.width=.006 if kind in ('Structure','Machine') else .003;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35);bevel.use_clamp_overlap=True;bevel.harden_normals=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
  normal=obj.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=40;bpy.ops.object.modifier_apply(modifier=normal.name)
 tri=obj.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
 mesh=obj.data;uv=mesh.uv_layers.active.data
 # Tangent-space production guard: repair degenerate planar UV islands before export.
 for face in mesh.polygons:
  ids=list(face.loop_indices);a,b,c=[uv[i].uv.copy() for i in ids]
  if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1.e-12:
   dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
   for li in ids:p=mesh.vertices[mesh.loops[li].vertex_index].co;uv[li].uv=(p[dims[0]],p[dims[1]])
 cos=[]
 for index,(vs,fs) in enumerate(g.C.get((room,kind),[])):
  cm=bpy.data.meshes.new('UCX_'+name+'_%03d'%index);cm.from_pydata(vs,[],fs);cm.update();co=bpy.data.objects.new(cm.name,cm);collcol.objects.link(co);co.select_set(True);cos.append(co)
  bm=bmesh.new();bm.from_mesh(cm);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cm);bm.free()
 mesh.update()
 fbx=OUT/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
 bounds={'min':[min(v.co[k] for v in mesh.vertices) for k in range(3)],'max':[max(v.co[k] for v in mesh.vertices) for k in range(3)]}
 slot_polys={str(slot.name):sum(p.material_index==i for p in mesh.polygons) for i,slot in enumerate(mesh.materials)}
 proto=room in hero_specs;placement=hero_specs[room]['display'] if proto else origins[room]
 obj.location=placement;obj['room_id']=room;obj['asset_role']=kind;obj['source_units']='metres';obj['ue_path']=CFG['ue_base']+'/Meshes/'+name
 obj['guardrail_drop']=(kind=='Rails');obj['approved_existing_asset']=False;created[name]=obj
 for co in cos:co.location=placement;co.hide_render=True;co.hide_viewport=True
 record.append(dict(name=name,room_id=room,kind=kind,fbx=fbx.relative_to(ROOT).as_posix(),materials={'PW_'+role:role for role in names},triangles=len(mesh.polygons),vertices=len(mesh.vertices),material_slot_triangles=slot_polys,collision=bool(cos),guardrail_drop=kind=='Rails',nanite=kind not in ('Signs','Markings','Hardware','Cablework','Hangers'),simple_collision_hulls=len(cos),placement_m=placement if not proto else [0,0,0],bounds_local_m=bounds,prototype=proto,cast_shadow=kind not in ('Markings','Signs','Hardware','Hangers','FloorFinish'),source_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest()))
 print('POWER_FBX_AUTHORED',name,len(mesh.polygons),len(cos),flush=True)
# Assemble additional instances of new prototypes without reauthoring geometry.
for room in CFG['rooms']:
 for part in room.get('authored_parts',[]):
  name=part['mesh'].split('/')[-1].split('.')[0];source=created[name];p=part['position_m'];world=[room['origin_m'][k]+p[k] for k in range(3)]
  if all(abs(source.location[k]-world[k])<1e-6 for k in range(3)):continue
  dup=source.copy();dup.data=source.data;dup.name=part['id'];collection.objects.link(dup);dup.location=world;dup.rotation_euler.z=math.radians(part.get('yaw_deg',0));dup['instance_of']=name
# Config lights are editor/source assembly only, finite and non-animated.
lightcol=bpy.data.collections.new('Source_Lighting_Not_Rendered');scene.collection.children.link(lightcol)
for room in CFG['rooms']+CFG['connectors']:
 for entry in room.get('lights',[]):
  data=bpy.data.lights.new(room['id']+'_'+entry['id'],'POINT');data.energy=entry['lumens']*.012;data.color=entry['tint'];data.shadow_soft_size=.23;obj=bpy.data.objects.new(data.name,data);lightcol.objects.link(obj);obj.location=[room['origin_m'][k]+entry['position_m'][k] for k in range(3)];obj['source_lumens']=entry['lumens'];obj['role']=entry['role']
# Placeholder anchors represent required reuse references, not fake prop meshes.
anchorcol=bpy.data.collections.new('Required_Existing_Asset_Anchors');scene.collection.children.link(anchorcol)
for room in CFG['rooms']:
 for part in room.get('reused_parts',[]):
  obj=bpy.data.objects.new(part['id'],None);anchorcol.objects.link(obj);obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.25;obj.location=[room['origin_m'][k]+part['position_m'][k] for k in range(3)];obj.rotation_euler.z=math.radians(part.get('yaw_deg',0));obj['ue_asset_reference']=part['mesh'];obj['awaiting_portable_geometry']=True
# Source camera bookmarks are saved for the user's own inspection; never rendered here.
for name,pos,target in [('Gallery',(-6,-2,1.65),(4,1,2)),('GeneratorHall',(18,-1,1.65),(28,3,2.2)),('Accumulator',(origins['AccumulatorControl'][0]-14,-7,1.65),(origins['AccumulatorControl'][0],0,3.5))]:
 data=bpy.data.cameras.new('View_'+name);ob=bpy.data.objects.new(data.name,data);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();data.lens=22
scene['project']='FPSGAME Power Theme subject';scene['tests_run']=False;scene['rendered']=False;scene['ue_imported']=False;scene['revision']=CFG['revision'];scene['style']='Existing industrial PBR materials reused by reference; portable maps pending if not yet integrated.'
manifest=dict(revision=CFG['revision'],blender_version=bpy.app.version_string,source_units='metres',coordinates='Blender (x,y,z) -> Unreal (100*x,-100*y,100*z)',objects=record,tests_run=False,rendered=False,ue_imported=False,random_pool_registered=False,required_existing_assets=sorted({p['mesh'] for r in CFG['rooms'] for p in r.get('reused_parts',[])}))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
# Pack only already-present source images; all geometry remains editable.
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FailedPowerCenter_ThreeRooms_Source.blend'))
receipt=dict(stage='new_geometry_authored',revision=CFG['revision'],blender_version=bpy.app.version_string,source_blend='Authored/FailedPowerCenter_ThreeRooms_Source.blend',fbx_count=len(record),source_triangles=sum(o['triangles'] for o in record),collision_hulls=sum(o['simple_collision_hulls'] for o in record),tests_run=False,rendered=False,ue_imported=False,ue_map_saved=False,reused_geometry_integrated=False)
(ROOT/'Receipts/authoring.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');print('POWER_AUTHORING_COMPLETE',json.dumps(receipt),flush=True)
