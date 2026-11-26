"""Independent shirt materials; the matching hat keeps its existing material family."""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/TailoredFinish20261021'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def save(asset):
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Tailored asset not saved '+asset.get_path_name())
def wire(a,output,b,pin):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect tailored material '+pin)
def output(node,prop,pin=''):
    if not L.connect_material_property(node,pin,prop):raise RuntimeError('Cannot connect tailored material output')
def material(name,family=None,color=None,rough=.8,metal=0):
    m=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    for usage in (u.MaterialUsage.MATUSAGE_SKELETAL_MESH,u.MaterialUsage.MATUSAGE_STATIC_MESH):L.set_material_usage(m,usage)
    if family:
        vertex=L.create_material_expression(m,u.MaterialExpressionVertexColor)
        for channel in ('BaseColor','Normal','ORM'):
            tex=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D);tex.set_editor_property('parameter_name',channel);tex.set_editor_property('texture',u.load_asset(DEST+'/Textures/T_'+family+'_'+channel))
            tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            if channel=='BaseColor':
                mul=L.create_material_expression(m,u.MaterialExpressionMultiply);wire(tex,'RGB',mul,'A');wire(vertex,'',mul,'B');output(mul,u.MaterialProperty.MP_BASE_COLOR)
            elif channel=='Normal':
                strength=L.create_material_expression(m,u.MaterialExpressionScalarParameter);strength.set_editor_property('parameter_name','SurfaceNormalStrength');strength.set_editor_property('default_value',1.)
                flat=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',u.LinearColor(0.,0.,1.,1.))
                blend=L.create_material_expression(m,u.MaterialExpressionLinearInterpolate);wire(flat,'',blend,'A');wire(tex,'RGB',blend,'B');wire(strength,'',blend,'Alpha')
                normalized=L.create_material_expression(m,u.MaterialExpressionNormalize);wire(blend,'',normalized,'');output(normalized,u.MaterialProperty.MP_NORMAL)
            else:
                output(tex,u.MaterialProperty.MP_AMBIENT_OCCLUSION,'R');output(tex,u.MaterialProperty.MP_METALLIC,'B')
                mul=L.create_material_expression(m,u.MaterialExpressionMultiply);wire(tex,'G',mul,'A');wire(vertex,'A',mul,'B');output(mul,u.MaterialProperty.MP_ROUGHNESS)
    else:
        node=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);node.set_editor_property('constant',u.LinearColor(*color,1));output(node,u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in ((rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)):
            node=L.create_material_expression(m,u.MaterialExpressionConstant);node.set_editor_property('r',value);output(node,prop)
    node=L.create_material_expression(m,u.MaterialExpressionConstant);node.set_editor_property('r',.22 if family=='RangerTwill' else .30);output(node,u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Tailored material compilation '+str(errors))
    save(m);return m
def create():
    revision=hashlib.sha256(Path(__file__).read_bytes()+(R/'surfaces.json').read_bytes()).hexdigest();receipt=R/'materials.json'
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if old.get('revision')==revision:return [u.load_asset(p) for p in old['materials']]
    surface=json.loads((R/'surfaces.json').read_text())
    for family in ('RangerTwill','RangerLeather'):
        for channel in ('BaseColor','Normal','ORM'):
            task=u.AssetImportTask();task.filename=str(R/'Textures'/(family+'_'+channel+'.png'));task.destination_path=DEST+'/Textures';task.destination_name='T_'+family+'_'+channel;task.automated=True;task.replace_existing=True;task.save=False
            A.import_asset_tasks([task]);tex=u.load_asset(DEST+'/Textures/'+task.destination_name)
            tex.set_editor_property('srgb',channel=='BaseColor');tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
            tex.set_editor_property('flip_green_channel',channel=='Normal');tex.set_editor_property('never_stream',False)
            tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if channel=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR if channel=='ORM' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
            tex.set_editor_property('address_x',u.TextureAddress.TA_WRAP);tex.set_editor_property('address_y',u.TextureAddress.TA_WRAP);tex.set_editor_property('compression_no_alpha',True)
            if channel=='Normal':tex.set_editor_property('normalize_normals',True)
            if channel=='ORM':
                tex.set_editor_property('composite_texture',u.load_asset(DEST+'/Textures/T_'+family+'_Normal'))
                tex.set_editor_property('composite_texture_mode',u.CompositeTextureMode.CTM_NORMAL_ROUGHNESS_TO_GREEN)
                tex.set_editor_property('composite_power',surface.get('composite_normal_roughness_power',.7))
            save(tex)
    mats=[material('M_RangerCloth','RangerTwill'),material('M_RangerLeather','RangerLeather'),material('M_RangerLining',color=(.021,.023,.016),rough=.90),material('M_RangerBrass',color=(.19,.115,.047),rough=.48,metal=.9),material('M_RangerThread',color=(.105,.071,.039),rough=.86)]
    receipt.write_text(json.dumps(dict(completed=True,revision=revision,surface_revision=surface.get('revision'),materials=[m.get_path_name() for m in mats],texture_size=2048,streaming=True,normal_map_mips='SimpleAverage + normalized',roughness_mips='Composite normal variance into ORM green',normal_convention=surface['normal_convention'],runtime_tested=False),indent=2),encoding='utf-8');return mats
if __name__=='__main__':create()
