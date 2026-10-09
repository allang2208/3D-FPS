"""Assemble actual existing FBX geometry in new editable scene, no re-export of props.
Original UE identities, UV layers, vertex colours and pivots remain unchanged.
"""
import bpy,json,re,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';B=ROOT/'References/ReuseBundle';CFG=json.loads((ROOT/'Config/scene.json').read_text());HAND=json.loads((B/'HANDOFF.json').read_text());assets={i['name']:i for i in HAND['assets']}
bpy.ops.wm.open_mainfile(filepath=str(OUT/'FailedPowerCenter_ThreeRooms_Source.blend'))
# Replace only our empty reference anchors, never any geometry from original assets.
old=bpy.data.collections.get('Required_Existing_Asset_Anchors')
if old:
 for o in list(old.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.collections.remove(old)
protos=bpy.data.collections.new('Original_Reusable_Asset_Masters');bpy.context.scene.collection.children.link(protos)
with bpy.data.libraries.load(str(OUT/'Reused_Original_Assets.blend'),link=False) as (src,dst):dst.objects=[name for name in src.objects if name in assets or name.startswith(('UCX_','UBX_','USP_','UCP_'))]
lookup={}
for obj in dst.objects:
 if obj is None:continue
 protos.objects.link(obj)
 if obj.name in assets:lookup[obj.name]=obj
 obj.hide_render=True;obj.hide_viewport=True
# Shared image/material nodes are reused by path, not copied into one texture per prop.
materials_by_ue={m.get('ue_material_path'):m for m in bpy.data.materials if m.get('ue_material_path')}
preview_assumptions=[]
def image_node(mat,path,noncolor=False):
 im=bpy.data.images.load(str(path),check_existing=True)
 if noncolor:im.colorspace_settings.name='Non-Color'
 n=mat.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;return n

def bind_pbr(mat,base=None,normal=None,orm=None,rough=None,directx=False):
 mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');links=mat.node_tree.links
 if base:n=image_node(mat,B/base);links.new(n.outputs['Color'],bs.inputs['Base Color'])
 if rough:n=image_node(mat,B/rough,True);links.new(n.outputs['Color'],bs.inputs['Roughness'])
 if orm:
  n=image_node(mat,B/orm,True);sep=mat.node_tree.nodes.new('ShaderNodeSeparateColor');links.new(n.outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 if normal:
  n=image_node(mat,B/normal,True);out=n.outputs['Color']
  if directx:
   sep=mat.node_tree.nodes.new('ShaderNodeSeparateColor');combine=mat.node_tree.nodes.new('ShaderNodeCombineColor');inv=mat.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
   links.new(out,sep.inputs['Color']);links.new(sep.outputs['Red'],combine.inputs['Red']);links.new(sep.outputs['Green'],inv.inputs[1]);links.new(inv.outputs[0],combine.inputs['Green']);links.new(sep.outputs['Blue'],combine.inputs['Blue']);out=combine.outputs['Color']
  nrm=mat.node_tree.nodes.new('ShaderNodeNormalMap');links.new(out,nrm.inputs['Color']);links.new(nrm.outputs['Normal'],bs.inputs['Normal'])

def preview_mat(path,slot):
 key=path.split('.')[0] if path else 'unused_'+slot
 if key in materials_by_ue:return materials_by_ue[key]
 m=bpy.data.materials.new('REF_'+slot);m.use_nodes=True;m['ue_material_path']=key;m['source_preview_only']=True
 bs=m.node_tree.nodes.get('Principled BSDF');color=(.18,.22,.19);rough=.64;metal=.10
 lower=slot.lower()
 for match,c,r,me in [('wood',(.24,.17,.095),.74,0),('steel',(.43,.46,.45),.38,1),('charcoal',(.035,.041,.035),.86,.10),('paper',(.65,.59,.43),.85,0),('canvas',(.29,.31,.20),.95,0),('gray',(.31,.33,.28),.65,.10),('green',(.13,.19,.145),.66,.1),('rubber',(.018,.020,.018),.9,0),('filter',(.29,.25,.16),.9,0),('ceramic',(.70,.68,.57),.4,0),('lampglass',(.78,.79,.68),.3,0)]:
  if match in lower:color,rough,metal=c,r,me
 bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;m.diffuse_color=(*color,1)
 if 'LampGlass' in slot:
  bs.inputs['Emission Color'].default_value=(.83,.9,.83,1);bs.inputs['Emission Strength'].default_value=2.0
 if slot=='FacilityProp_Atlas':
  root='SourceAssets/DungeonFacilityPropPolish20260928/Authored/Textures/T_FacilityProp_';bind_pbr(m,root+'BaseColor.png',root+'NormalGL.png',root+'ORM.png')
 elif slot=='ArchiveEquipment_Atlas':
  root='SourceAssets/DungeonDataArchive20260930/EquipmentRefine20260930/Authored/Textures/T_ArchiveEquipment_';bind_pbr(m,root+'BaseColor.png',root+'NormalGL.png',root+'ORM.png')
 elif slot in ('V2_TileGlazeAtlas','V2_TileCeramicCore'):
  stem=slot.removeprefix('V2_');root='SourceAssets/DungeonAtmosphereV2_20260921/Authored/TilePolish/Textures/'+stem+'_';bind_pbr(m,root+'BaseColor.png',root+'Normal.png',rough=root+'Roughness.png')
 elif slot=='V2_CeramicFractureCore':
  root='SourceAssets/DungeonTileFracture20260922/Authored/Textures/CeramicFracture_';bind_pbr(m,root+'BaseColor.png',root+'Normal.png',rough=root+'Roughness.png')
 elif slot in ('V2_WallReliefFinish','V2_WallReliefBed','V2_TileMortar'):
  root='SourceAssets/DungeonWallUpgrade20260924/Authored/Textures/Mortar_';bind_pbr(m,root+'BaseColor.png',root+'Normal.png',root+'ORM.png',directx=True)
 elif slot=='RS_Labels':bind_pbr(m,'SourceAssets/IncineratorContainers20261003/Authored/T_Treatment_Labels.png')
 else:
  m['preview_approximation']='Colour/roughness proxy; UE keeps original existing material unchanged.';preview_assumptions.append(key)
 materials_by_ue[key]=m;return m
for name,obj in lookup.items():
 a=assets[name];mapping=a.get('materials',{a.get('slot','Material'):a.get('material','')})
 for i,slot in enumerate(obj.data.materials):
  clean=re.sub(r'\.\d{3}$','',slot.name);path=mapping.get(clean)
  # Empty TileMortar slot has zero faces in source. Preserve it without inventing a UE path.
  used=sum(p.material_index==i for p in obj.data.polygons)
  if path is None and used:raise RuntimeError('Missing original used slot mapping '+name+':'+clean)
  obj.data.materials[i]=preview_mat(path,clean)
# Preserve an unlinked mesh master; only linked instances are visible in scene.
col=bpy.data.collections.new('Reused_Existing_Props_and_Original_Tiles');bpy.context.scene.collection.children.link(col)
placed=[]
for room in CFG['rooms']+CFG['connectors']:
 for p in room.get('reused_parts',[]):
  if p['source_asset_id'] not in lookup:continue  # revision supplement owns these originals
  source=lookup[p['source_asset_id']];obj=source.copy();obj.data=source.data;obj.name=room['id']+'_'+p['id'];col.objects.link(obj);obj.hide_render=False;obj.hide_viewport=False;obj.location=[room['origin_m'][k]+p['position_m'][k] for k in range(3)];obj.rotation_euler=(0,0,math.radians(p.get('yaw_deg',0)));obj['room_id']=room['id'];obj['ue_asset_reference']=p['mesh'];obj['container_id']=p.get('container_id','');obj['reuse_method']='Original unscaled source mesh instance'
  if p.get('materials'):
   obj.data=obj.data.copy()
   for i,path in enumerate(p['materials']):
    key=path.split('.')[0]
    if key not in materials_by_ue:raise RuntimeError('Missing explicit source override material '+key)
    obj.data.materials[i]=materials_by_ue[key]
  placed.append(dict(id=p['id'],room=room['id'],asset=p['mesh'],position_m=list(obj.location),yaw_blender_deg=p.get('yaw_deg',0),source_vertices=len(obj.data.vertices),source_triangles=sum(len(x.vertices)-2 for x in obj.data.polygons)))
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
scene=bpy.context.scene;scene['required_existing_geometry_integrated']=True;scene['source_reuse_head']='2f3a60fa';scene['source_preview_material_caveat']='Original atlas and ceramic PBR retained; unprovided existing shaders remain explicit preview proxies, never replace UE originals.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FailedPowerCenter_ThreeRooms_Source.blend'))
receipt=dict(stage='original_geometry_integrated',blender_version=bpy.app.version_string,source_library_file_id='libfile_e8dc0a6713f88191a4055ae86cf9e3bd',source_archive_sha256='56aaf6a0f4cc3310d2804a38584aae7de1693a6464a99dec555c644ec3e84626',unique_original_meshes=len(lookup),original_mesh_instances=len(placed),placements=placed,unprovided_shader_preview_proxies=sorted(set(preview_assumptions)),tests_run=False,rendered=False,ue_imported=False)
(ROOT/'Receipts/reuse-assembly.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_ORIGINAL_ASSETS_ASSEMBLED',len(placed),'instances from',len(lookup),'original meshes',flush=True)
