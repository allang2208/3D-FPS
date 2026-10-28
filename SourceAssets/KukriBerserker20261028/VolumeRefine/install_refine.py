"""Publish local-space blade runes and the original column with its new wolf-head crown."""
import json
from pathlib import Path
import unreal as u
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/VolumeRefine/install_refine.py').resolve().parent
BASE='/Game/Weapons/Kukri20261020/Berserker20261028'
DEST=BASE+'/VolumeRefine'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve the running game')
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
targets=[BASE+'/M_BerserkerEnergyHud']+[BASE+'/Materials/M_Berserker_'+r['kind'] for r in json.loads((P/'projection-layouts.json').read_text())]
if any(p in dirty for p in targets) or any(p.startswith(DEST) for p in dirty):raise RuntimeError('Preserve unsaved rune materials')
receipt={'complete':False,'saved_assets':[],'runtime_tested':False}

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())

def node(mat,cls,**props):
    x=L.create_material_expression(mat,cls)
    for k,v in props.items():x.set_editor_property(k,v)
    return x

def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)

# Preserve the lower bar; the user's latest crown replaces the upper cap and
# flat sigil. Reimports must not restore either rejected HUD revision.
head=P.parent/'WolfHeadComposite/install_head.py'
exec(compile(head.read_text('utf-8'),str(head),'exec'),{'__file__':str(head),'__name__':'__main__'})
materials=[]
glyph=u.load_asset(BASE+'/Textures/T_BerserkerWolf')
glyph.set_editor_properties({'srgb':False,'compression_settings':u.TextureCompressionSettings.TC_BC7,'max_texture_size':2048})
save(glyph)
for layout in json.loads((P/'projection-layouts.json').read_text('utf-8')):
    kind=layout['kind'];mat=u.load_asset(BASE+'/Materials/M_Berserker_'+kind)
    expr=L.get_material_expressions(mat)
    projection=next((n for n in expr if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='BerserkerLocalProjection'),None)
    if projection is None:
        pins=[]
        for key in ('LocalPos','Glyph','Center','Extent'):
            p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
        projection=node(mat,u.MaterialExpressionCustom,description='BerserkerLocalProjection',inputs=pins,output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
        link(node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='BerserkerGlyph',texture=glyph),'',projection,'Glyph')
        center=node(mat,u.MaterialExpressionVectorParameter,parameter_name='BerserkerCenter')
        extent=node(mat,u.MaterialExpressionVectorParameter,parameter_name='BerserkerExtent')
        link(center,'RGB',projection,'Center');link(extent,'RGB',projection,'Extent')
    # UE 5.8 exposes PreSkinnedPosition in the vertex shader only. Explicitly
    # interpolate it before the pixel shader's rune texture and derivative work.
    position=next((n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionPreSkinnedPosition)),None)
    position=position or node(mat,u.MaterialExpressionPreSkinnedPosition)
    local_pixel=next((n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionVertexInterpolator)
        and str(n.get_editor_property('desc'))=='BerserkerLocalPositionToPixel'),None)
    local_pixel=local_pixel or node(mat,u.MaterialExpressionVertexInterpolator,desc='BerserkerLocalPositionToPixel')
    link(position,'',local_pixel,'VS');link(local_pixel,'PS',projection,'LocalPos')
    projection.set_editor_property('code',(P/'RuneProjection.hlsl').read_text('utf-8'))
    for n in L.get_material_expressions(mat):
        if isinstance(n,u.MaterialExpressionVectorParameter):
            key=str(n.get_editor_property('parameter_name'))
            if key=='BerserkerCenter':n.set_editor_property('default_value',u.LinearColor(*layout['center_cm'],layout['angle_radians'],1))
            elif key=='BerserkerExtent':n.set_editor_property('default_value',u.LinearColor(layout['width_cm'],layout['height_cm'],0,1))
        if isinstance(n,u.MaterialExpressionLinearInterpolate):link(projection,'',n,'Alpha')
        if isinstance(n,u.MaterialExpressionCustom) and 'float3(.85,.012,.022)' in n.get_editor_property('code'):link(projection,'',n,'Mask')
    # Remove the old UV-atlas rune-height contribution; the blade's original PBR normal remains intact.
    base_normal=next(n for n in expr if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('sampler_type')==u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    slab=next(n for n in expr if isinstance(n,u.MaterialExpressionSubstrateShadingModels))
    link(base_normal,'RGB',slab,'Normal');L.connect_material_property(base_normal,'RGB',u.MaterialProperty.MP_NORMAL)
    E.set_metadata_tag(mat,'RuneProjection','CentimetersAspectPreservedV2')
    materials.append(mat)
for mat in materials:
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(mat.get_path_name()+': '+str(errors))
if not u.PoisonMaggotMonster.compile_material_assets(materials):raise RuntimeError('Material compilation failed')
for mat in materials:save(mat)
receipt['complete']=True
(P/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BERSERKER_VOLUME_REFINEMENT_SAVED',len(receipt['saved_assets']))
