"""Save independent frost-raven materials, glyph, crown and final standard icon."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
ROOT='/Game/Weapons/Kukri20261020/FrostRaven20261028'
DONOR='/Game/Weapons/Kukri20261020/Berserker20261028'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT) for p in dirty):raise RuntimeError('Preserve unsaved frost-raven assets')
receipt={'complete':False,'saved_assets':[],'surface_materials':{},'runtime_tested':False}
def record():(P/'import-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());record();return asset
def duplicate(source,path):
    if E.does_asset_exist(path):return u.load_asset(path)
    obj=E.duplicate_asset(source,path)
    if not obj:raise RuntimeError('Cannot duplicate '+source)
    return obj
def texture(file,name,icon=False):
    dest='/Game/ColdSteelData/AttachmentIcons20260913' if icon else ROOT+'/Textures'
    if dest+'/'+name in dirty:raise RuntimeError('Preserve unsaved icon')
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=dest;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
    tex=u.load_asset(dest+'/'+name)
    if not tex:raise RuntimeError('Import failed '+name)
    tex.set_editor_properties({'srgb':icon,'never_stream':True,'max_texture_size':2048,
        'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON if icon else u.TextureCompressionSettings.TC_BC7,
        'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
        'address_x':u.TextureAddress.TA_CLAMP,'address_y':u.TextureAddress.TA_CLAMP})
    return save(tex)
record()
glyph=texture(P.parent/'BladeSigilV2/Art/RavenSigilFine.png','T_FrostRavenGlyph')
crown=texture(P.parent/'CrystalCrownV3/Art/FrostRavenCrystal.png','T_FrostRavenCrown')
icon=texture(P/'Icons/ue_kukri_blade_2_frost_raven_rune.png','ue_kukri_blade_2_frost_raven_rune',True)
receipt['icon']=icon.get_path_name()
hud=duplicate(DONOR+'/M_BerserkerEnergyHud',ROOT+'/M_FrostRavenEnergyHud')
nodes=L.get_material_expressions(hud)
custom=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom))
custom.set_editor_properties({'code':(P/'FrostRavenEnergyHud.hlsl').read_text('utf-8'),'description':'FrostRavenUnifiedCrystalCrownV3'})
head=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='WolfHeadTex')
head.set_editor_property('texture',crown)
E.set_metadata_tag(hud,'SourceAuthoring','KukriFrostRaven20261028/CrystalCrownV3')
E.set_metadata_tag(hud,'EnergyBarDesign','OriginalVessel_UnifiedSapphireEagle')
E.set_metadata_tag(hud,'CrownJoin','IntegralCrystalRoot_WidthMatchedV1')
materials=[hud]
for layout in json.loads((P/'projection-layouts.json').read_text('utf-8')):
    kind=layout['kind'];slot='M_Kukri' if kind=='Factory' else 'M_Kukri_'+kind
    mat=duplicate(DONOR+'/Materials/M_Berserker_'+kind,ROOT+'/Materials/M_FrostRaven_'+kind)
    for node in L.get_material_expressions(mat):
        if isinstance(node,u.MaterialExpressionTextureObjectParameter) and str(node.get_editor_property('parameter_name'))=='BerserkerGlyph':node.set_editor_property('texture',glyph)
        if isinstance(node,u.MaterialExpressionVectorParameter):
            key=str(node.get_editor_property('parameter_name'))
            if key=='BerserkerCenter':node.set_editor_property('default_value',u.LinearColor(*layout['center_cm'],layout['angle_radians'],1))
            elif key=='BerserkerExtent':node.set_editor_property('default_value',u.LinearColor(layout['width_cm'],layout['height_cm'],0,1))
        if isinstance(node,u.MaterialExpressionCustom):
            code=str(node.get_editor_property('code'))
            if 'Mask*float3(' in code and 'Time' in code:node.set_editor_property('code',(P.parent/'BladeSigilV2/FineRuneGlow.hlsl').read_text('utf-8'))
            elif str(node.get_editor_property('description'))=='BerserkerLocalProjection':node.set_editor_property('code',(P/'RuneProjection.hlsl').read_text('utf-8'))
    E.set_metadata_tag(mat,'SourceAuthoring','KukriFrostRaven20261028/BladeSigilV2');E.set_metadata_tag(mat,'RuneProjection','LocalCentimetersAspectPreserved')
    instance=duplicate(DONOR+'/Materials/MI_Berserker_'+kind,ROOT+'/Materials/MI_FrostRaven_'+kind)
    L.set_material_instance_parent(instance,mat)
    L.set_material_instance_texture_parameter_value(instance,'BerserkerGlyph',glyph)
    L.set_material_instance_vector_parameter_value(instance,'RuneTint',u.LinearColor(.09,.27,.43,1))
    L.set_material_instance_vector_parameter_value(instance,'BerserkerCenter',u.LinearColor(*layout['center_cm'],layout['angle_radians'],1))
    L.set_material_instance_vector_parameter_value(instance,'BerserkerExtent',u.LinearColor(layout['width_cm'],layout['height_cm'],0,1))
    L.update_material_instance(instance);materials.extend([mat,instance]);receipt['surface_materials'][slot]=instance.get_path_name()
for mat in materials:
    if isinstance(mat,u.Material):
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError(mat.get_path_name()+': '+str(errors))
if not u.PoisonMaggotMonster.compile_material_assets(materials):raise RuntimeError('Frost-raven material compilation failed')
for mat in materials:save(mat)
fx=P/'author_materials.py'
exec(compile(fx.read_text('utf-8'),str(fx),'exec'),{'__file__':str(fx),'__name__':'__main__'})
receipt['saved_assets']+=json.loads((P/'material-receipt.json').read_text('utf-8'))['assets']
receipt['hud']=hud.get_path_name();receipt['complete']=True;record()
u.log('FROST_RAVEN_ASSETS_SAVED '+str(len(receipt['saved_assets'])))
