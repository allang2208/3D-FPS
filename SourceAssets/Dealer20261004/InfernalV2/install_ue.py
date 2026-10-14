"""Save Infernal V2 title/burst materials, packed mask and the current result-mesh binding."""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
BASE='/Game/Weapons/Dealer20261004'
DEST=BASE+'/InfernalV2'
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
L=u.MaterialEditingLibrary
receipt={'version':2,'complete':False,'saved_assets':[],'runtime_tested':False,'rendered':False}


def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());record()


target=BASE+'/Meshes/SM_DealerResult'
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if p.get_name().startswith(DEST+'/') or p.get_name()==target]
if dirty:raise RuntimeError('Preserve unsaved Dealer targets: '+', '.join(dirty))
record()
source=ROOT.parents[2]/'Content/Weapons/Dealer20261004/Meshes/SM_DealerResult.uasset'
backup=ROOT/'BackupV1/SM_DealerResult.uasset'
if source.is_file() and not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)

task=u.AssetImportTask()
for key,value in {'filename':str(ROOT/'Export/T_DealerInfernalMasks.png'),'destination_path':DEST+'/Textures',
    'destination_name':'T_DealerInfernalMasks','automated':True,'replace_existing':True,'save':False}.items():task.set_editor_property(key,value)
A.import_asset_tasks([task])
texture=u.load_asset(DEST+'/Textures/T_DealerInfernalMasks')
if not texture:raise RuntimeError('Cannot import Infernal glyph mask')
texture.set_editor_property('srgb',False)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
texture.set_editor_property('max_texture_size',4096)
save(texture)


def build_material(name,code_file,atlas=None):
    path=DEST+'/Materials/'+name
    mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'DealerInfernalRevision')!='2':raise RuntimeError('Preserve unowned material '+path)
    if not mat:mat=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if not mat:raise RuntimeError('Cannot create '+path)
    for expression in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expression)
    for key,value in {'blend_mode':u.BlendMode.BLEND_TRANSLUCENT,'shading_model':u.MaterialShadingModel.MSM_UNLIT,
        'two_sided':True,'disable_depth_test':True,'translucency_pass':u.MaterialTranslucencyPass.MTP_AFTER_DOF,
        'enable_responsive_aa':True}.items():mat.set_editor_property(key,value)
    count=0

    def node(cls,**props):
        nonlocal count
        n=L.create_material_expression(mat,cls,-1700+(count%8)*240,(count//8)*250);count+=1
        for k,v in props.items():n.set_editor_property(k,v)
        return n

    def wire(a,b,pin=0,output=''):
        if isinstance(pin,int):pin=str(L.get_material_expression_input_names(b)[pin])
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+name+' '+str(pin))

    inputs={'UV':node(u.MaterialExpressionTextureCoordinate),
        'Reveal':node(u.MaterialExpressionScalarParameter,parameter_name='Reveal',default_value=0.0),
        'Age':node(u.MaterialExpressionScalarParameter,parameter_name='Age',default_value=0.0),
        'Tier':node(u.MaterialExpressionScalarParameter,parameter_name='Tier',default_value=0.0)}
    if atlas:
        inputs['CardIndex']=node(u.MaterialExpressionScalarParameter,parameter_name='CardIndex',default_value=0.0)
        inputs['Atlas']=node(u.MaterialExpressionTextureObjectParameter,parameter_name='TitleAtlas',texture=atlas,
            sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    custom=node(u.MaterialExpressionCustom,code=(ROOT/code_file).read_text(encoding='utf-8'),output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for key in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for key,expr in inputs.items():wire(expr,custom,key)
    color=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);wire(custom,color)
    alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);wire(custom,alpha)
    exposure=node(u.MaterialExpressionEyeAdaptationInverse);wire(color,exposure,0)
    wire(node(u.MaterialExpressionConstant,r=1.0),exposure,1)
    if not L.connect_material_property(exposure,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Cannot connect emissive')
    if not L.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY):raise RuntimeError('Cannot connect coverage')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Infernal material compile failed '+name+': '+str(errors))
    E.set_metadata_tag(mat,'DealerInfernalRevision','2');save(mat)
    return mat


title=build_material('M_DealerInfernalTitle','InfernalTitle.hlsl',texture)
burst=build_material('M_DealerInfernalBurst','InfernalBurst.hlsl')
mesh=u.load_asset(target)
if not mesh:raise RuntimeError('Missing existing Dealer result mesh')
mesh.set_material(0,title);save(mesh)
receipt['complete']=True
receipt['title_grid']=[3,3]
receipt['high_results']=['FULL HOUSE','FOUR OF A KIND','STRAIGHT FLUSH']
record()
print('DEALER_INFERNAL_V2_SAVED texture=1 materials=2 mesh_binding=1 tested=false rendered=false')
