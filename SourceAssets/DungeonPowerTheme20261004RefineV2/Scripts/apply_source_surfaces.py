"""Attach the inventoried original surface files to Blender authoring materials.
Existing UE materials remain authoritative. No replacement textures are invented.
The partial SeamMetal preview explicitly omits unavailable RustNormal/RustORM.
"""
import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];S=R/'References/Supplement';meta=json.loads((S/'SUPPLEMENT.json').read_text());O=R/'Authored'
bpy.ops.wm.open_mainfile(filepath=str(O/'FailedPowerCenter_ThreeRooms_Source.blend'))
by={m.get('ue_material_path'):m for m in bpy.data.materials if m.get('ue_material_path')}
def node(m,t):return m.node_tree.nodes.new(t)
def math(m,op,a,b=0):
 n=node(m,'ShaderNodeMath');n.operation=op
 for i,v in enumerate((a,b)):
  if isinstance(v,(int,float)):n.inputs[i].default_value=v
  else:m.node_tree.links.new(v,n.inputs[i])
 return n.outputs[0]
def tex(m,p,noncolor=False,vector=None,box=False):
 im=bpy.data.images.load(str(S/p),check_existing=True)
 if noncolor:im.colorspace_settings.name='Non-Color'
 n=node(m,'ShaderNodeTexImage');n.image=im
 if vector:m.node_tree.links.new(vector,n.inputs['Vector'])
 if box:n.projection='BOX';n.projection_blend=.18
 return n
# Use exactly the delivered original BC/N/ORM, with known DirectX normal Y reversal
# in Blender only. No height is reconstructed from color.
w=meta['wall_concrete']
for m in list(bpy.data.materials):
 if m.get('ue_material_path')!=w['ue_material']:continue
 m.use_nodes=True;links=m.node_tree.links;bs=m.node_tree.nodes.get('Principled BSDF')
 color=tex(m,w['basecolor']);orm=tex(m,w['orm'],True);normal=tex(m,w['normal'],True)
 links.new(color.outputs['Color'],bs.inputs['Base Color']);sep=node(m,'ShaderNodeSeparateColor');links.new(orm.outputs['Color'],sep.inputs['Color']);links.new(sep.outputs['Green'],bs.inputs['Roughness']);bs.inputs['Metallic'].default_value=0
 split=node(m,'ShaderNodeSeparateColor');merge=node(m,'ShaderNodeCombineColor');links.new(normal.outputs['Color'],split.inputs['Color']);links.new(split.outputs['Red'],merge.inputs['Red']);links.new(math(m,'SUBTRACT',1,split.outputs['Green']),merge.inputs['Green']);links.new(split.outputs['Blue'],merge.inputs['Blue'])
 nrm=node(m,'ShaderNodeNormalMap');nrm.inputs['Strength'].default_value=w['normal_strength'];links.new(merge.outputs['Color'],nrm.inputs['Color']);links.new(nrm.outputs['Normal'],bs.inputs['Normal'])
 m['source_preview_only']=True;m['actual_original_maps_attached']=True;m['missing_preview_features']='Original UE triplanar/POM/grain-distance fade remains UE-only; omitted height is not synthesized.'
# A documented partial view of the original SeamMetal shader, using its exact tint,
# roughness, metallic and available original rust/dirt textures. Never a UE override.
for spec in meta['seam_metal']['instances']:
 for m in list(bpy.data.materials):
  if m.get('ue_material_path')!=spec['ue_material']:continue
  links=m.node_tree.links;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*spec['BaseTint'],1);bs.inputs['Roughness'].default_value=spec['Roughness'];bs.inputs['Metallic'].default_value=spec['Metallic']
  tc=node(m,'ShaderNodeTexCoord');scale=node(m,'ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=100/spec['TileSize'];links.new(tc.outputs['Object'],scale.inputs[0])
  rust=tex(m,meta['seam_metal']['included_existing_files']['RustColor_local_copy'],vector=scale.outputs[0],box=True)
  ds=node(m,'ShaderNodeVectorMath');ds.operation='SCALE';ds.inputs[3].default_value=.61;links.new(scale.outputs[0],ds.inputs[0])
  dirty=tex(m,meta['seam_metal']['included_existing_files']['DirtyMetal_original_import_source'],True,ds.outputs[0],True);dc=node(m,'ShaderNodeSeparateColor');links.new(dirty.outputs['Color'],dc.inputs['Color'])
  age=node(m,'ShaderNodeVertexColor');age.layer_name='ServiceAge';ac=node(m,'ShaderNodeSeparateColor');links.new(age.outputs['Color'],ac.inputs['Color'])
  threshold=math(m,'SUBTRACT',1,math(m,'ADD',spec['RustCoverage'],math(m,'MULTIPLY',ac.outputs['Red'],.32)))
  field=math(m,'MINIMUM',1,math(m,'MULTIPLY',dc.outputs['Red'],4.5));mapped=node(m,'ShaderNodeMapRange');mapped.clamp=True;mapped.interpolation_type='SMOOTHSTEP';links.new(field,mapped.inputs['Value']);links.new(math(m,'SUBTRACT',threshold,.08),mapped.inputs['From Min']);links.new(math(m,'ADD',threshold,.08),mapped.inputs['From Max'])
  dirt=math(m,'MINIMUM',1,math(m,'ADD',math(m,'MULTIPLY',dc.outputs['Red'],1.4),math(m,'MULTIPLY',ac.outputs['Red'],.25)))
  coat=node(m,'ShaderNodeMixRGB');coat.blend_type='MULTIPLY';coat.inputs[0].default_value=1;coat.inputs[1].default_value=(*spec['BaseTint'],1);links.new(math(m,'SUBTRACT',1,math(m,'MULTIPLY',dirt,.65*.35)),coat.inputs[2])
  rustshade=node(m,'ShaderNodeMixRGB');rustshade.blend_type='MULTIPLY';rustshade.inputs[0].default_value=1;rustshade.inputs[2].default_value=(.8,.8,.8,1);links.new(rust.outputs['Color'],rustshade.inputs[1])
  mix=node(m,'ShaderNodeMixRGB');links.new(mapped.outputs['Result'],mix.inputs[0]);links.new(coat.outputs['Color'],mix.inputs[1]);links.new(rustshade.outputs['Color'],mix.inputs[2]);links.new(mix.outputs['Color'],bs.inputs['Base Color'])
  links.new(math(m,'MULTIPLY',spec['Metallic'],math(m,'SUBTRACT',1,mapped.outputs['Result'])),bs.inputs['Metallic'])
  # Missing RustORM is left missing; roughness uses the known base + existing dirt G.
  rough=math(m,'ADD',spec['Roughness'],math(m,'MULTIPLY',math(m,'SUBTRACT',dc.outputs['Green'],.5),.32));links.new(rough,bs.inputs['Roughness'])
  m['actual_original_maps_attached']=True;m['source_preview_only']=True;m['missing_preview_features']='RustNormal and RustORM raw sources unavailable; omitted, never synthesized. UE keeps the complete original material.'
# Correct the zero-face legacy slot using its verified identity without any maps.
for m in bpy.data.materials:
 if m.name.startswith('REF_V2_TileMortar'):
  m['ue_material_path']=meta['tile_mortar']['ue_material'];m['unused_source_slot']=True
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
bpy.context.scene['source_preview_material_caveat']='Original concrete BC/N/ORM, tile and equipment PBR attached. SeamMetal preview has exact parameters + original available rust/dirt maps; missing RustNormal/RustORM and full UE POM/projection remain engine-authoritative.'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'FailedPowerCenter_ThreeRooms_Source.blend'))
(R/'Receipts/source-surfaces.json').write_text(json.dumps(dict(stage='original_source_maps_attached',original_concrete=True,original_equipment_atlases=True,original_tile_maps=True,seam_metal_partial_preview=True,missing_raw_sources=meta['seam_metal']['missing_raw_sources'],height_synthesized=False,ue_materials_modified=False,tests_run=False,rendered=False),ensure_ascii=False,indent=2))
print('POWER_ORIGINAL_SOURCE_SURFACES_ATTACHED',flush=True)
