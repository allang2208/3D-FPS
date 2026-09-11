"""UE material variant: original geometry/textures stay editable and unchanged."""
import unreal,json
from pathlib import Path
L=unreal.MaterialEditingLibrary
D='/Game/Items/EnhancementMaterials/enhancement_stone'
name='M_enhancement_stone_amethyst'
m=unreal.load_asset(D+'/'+name)
if not m:
 m=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name,D,unreal.load_asset(D+'/M_enhancement_stone_0'))
for n in list(L.get_material_expressions(m)):
 if str(n.get_editor_property('desc')).startswith('Amethyst:'):L.delete_material_expression(m,n)
source=next(n for n in L.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionTextureSample) and n.texture and n.texture.get_name().endswith('_Base_Color'))
mask='float peak=max(max(C.r,C.g),C.b); float vein=smoothstep(0.10,0.34,(C.b-C.r)/max(peak,0.02))*smoothstep(0.025,0.12,peak); '
def custom(label,code,prop):
 n=L.create_material_expression(m,unreal.MaterialExpressionCustom)
 n.set_editor_property('desc','Amethyst: '+label);n.set_editor_property('code',mask+code)
 n.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
 i=unreal.CustomInput();i.set_editor_property('input_name','C');n.set_editor_property('inputs',[i])
 assert L.connect_material_expressions(source,'RGB',n,'C')
 assert L.connect_material_property(n,'',prop)
custom('ore and crystal color','float l=dot(C,float3(0.2126,0.7152,0.0722)); float3 rock=lerp(C,l*float3(0.80,0.24,1.10),0.82); float3 crystal=float3(0.50,0.055,0.90)*max(l*2.1,0.055); return lerp(rock,crystal,vein);',unreal.MaterialProperty.MP_BASE_COLOR)
custom('restrained crystal glow','return vein*float3(0.38,0.018,0.85)*0.42*saturate(peak*3.0);',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
custom('mineral reflectance','return lerp(0.25,0.06,vein);',unreal.MaterialProperty.MP_METALLIC)
# Existing normal and roughness retain baked mineral detail.
L.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
mesh=unreal.load_asset(D+'/SM_enhancement_stone');mesh.set_material(0,m);unreal.EditorAssetLibrary.save_loaded_asset(mesh)
Path('D:/FPS3D/FPSGAME/Saved/AmethystStoneMaterial.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'material':m.get_path_name(),'preserved':['geometry','normal','roughness','original textures'],'glow_strength':0.42},indent=2))
unreal.log('AMETHYST_STONE_MATERIAL_PASS')
