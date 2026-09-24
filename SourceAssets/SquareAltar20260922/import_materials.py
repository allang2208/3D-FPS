"""Create only this altar's UE materials and source marble texture."""
import json
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent
ROOT='/Game/Props/SquareAltar20260922'
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools()
saved=[]


def save(asset):
    package=u.load_package(asset.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    saved.append(asset.get_path_name())


path=ROOT+'/Textures/T_SquareAltar_Marble'
texture=u.load_asset(path)
if not texture:
    task=u.AssetImportTask();task.filename=str(HERE/'Authored/T_SquareAltar_Marble.png')
    task.destination_path=ROOT+'/Textures';task.destination_name='T_SquareAltar_Marble'
    task.automated=True;task.save=False
    A.import_asset_tasks([task]);texture=u.load_asset(path)
    if not texture:raise RuntimeError('Marble import failed')
    texture.set_editor_property('srgb',True);save(texture)


def scalar(mat,name,value):
    n=L.create_material_expression(mat,u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value)
    return n


def vector(mat,name,value):
    n=L.create_material_expression(mat,u.MaterialExpressionVectorParameter)
    n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1))
    return n


def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material link failed: '+pin)


def output(node,pin,prop):
    if not L.connect_material_property(node,pin,prop):raise RuntimeError('Material output failed: '+str(prop))


recipes={
 'Altar_WhiteMarble':([.87,.86,.83],.31,0,True),
 'Altar_PolishedMolding':([.91,.90,.87],.23,0,True),
 'Altar_SatinGold':([.67,.43,.15],.27,.92,False),
 'Altar_BlueSapphire':([.014,.032,.24],.105,.12,False),
}
for name,(color,roughness,metallic,stone) in recipes.items():
    path=ROOT+'/Materials/M_'+name
    mat=u.load_asset(path)
    if mat:continue
    mat=A.create_asset('M_'+name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    tint=vector(mat,'BaseTint',color)
    if stone:
        sample=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
        sample.set_editor_property('parameter_name','MarbleAlbedo');sample.set_editor_property('texture',texture)
        sample.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        mix=L.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
        amount=scalar(mat,'VeinAmount',.52)
        link(tint,'RGB',mix,'A');link(sample,'RGB',mix,'B');link(amount,'',mix,'Alpha')
        output(mix,'',u.MaterialProperty.MP_BASE_COLOR)
        # Mineral veins affect colour, not large physical cracks. Only a small
        # reflectance variation is taken from the green channel.
        rmin=scalar(mat,'RoughnessMin',roughness-.025);rmax=scalar(mat,'RoughnessMax',roughness+.025)
        rmix=L.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
        link(rmin,'',rmix,'A');link(rmax,'',rmix,'B');link(sample,'G',rmix,'Alpha')
        output(rmix,'',u.MaterialProperty.MP_ROUGHNESS)
    else:
        output(tint,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        output(scalar(mat,'Roughness',roughness),'',u.MaterialProperty.MP_ROUGHNESS)
    output(scalar(mat,'Metallic',metallic),'',u.MaterialProperty.MP_METALLIC)
    output(scalar(mat,'Specular',.58 if 'Sapphire' in name else .48),'',u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    E.set_metadata_tag(mat,'Source','gamedev defense_base.png / SquareAltar20260922')
    save(mat)
(HERE/'materials_receipt.json').write_text(json.dumps({'saved':saved,'runtime_tested':False},indent=2),encoding='utf-8')
print('SQUARE_ALTAR_MATERIALS_SAVED '+json.dumps(saved))
