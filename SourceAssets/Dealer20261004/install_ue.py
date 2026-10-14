"""Import and save only the authored Dealer deck; safe for background commandlets or the mutex bridge."""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
DEST='/Game/Weapons/Dealer20261004'
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
L=u.MaterialEditingLibrary
receipt={'complete':False,'cards':52,'saved_assets':[],'runtime_tested':False,'rendered':False}


def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());record()


dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved Dealer packages: '+', '.join(dirty))
record()
textures={}
for name in ['T_DealerFaces','T_DealerBack','T_DealerResults']:
    task=u.AssetImportTask()
    for key,value in {'filename':str(ROOT/'Export/Textures'/(name+'.png')),'destination_path':DEST+'/Textures',
        'destination_name':name,'automated':True,'replace_existing':True,'save':False}.items():task.set_editor_property(key,value)
    A.import_asset_tasks([task])
    tex=u.load_asset(DEST+'/Textures/'+name)
    if not tex:raise RuntimeError('Texture import failed '+name)
    tex.set_editor_property('srgb',True)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
    tex.set_editor_property('max_texture_size',4096 if name=='T_DealerFaces' else 2048)
    textures[name]=tex;save(tex)


def material(name,texture=None,columns=1,rows=1):
    path=DEST+'/Materials/'+name
    mat=u.load_asset(path)
    if mat and E.get_metadata_tag(mat,'DealerAuthored')!='20261004':raise RuntimeError('Preserve unowned material '+path)
    if not mat:mat=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if not mat:raise RuntimeError('Cannot create material '+path)
    for expression in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,expression)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('disable_depth_test',True)
    mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_AFTER_DOF)
    mat.set_editor_property('enable_responsive_aa',True)
    count=0

    def node(cls,**props):
        nonlocal count
        n=L.create_material_expression(mat,cls,-1400+(count%7)*230,(count//7)*230);count+=1
        for k,v in props.items():n.set_editor_property(k,v)
        return n

    def wire(a,b,pin=0,output=''):
        if isinstance(pin,int):pin=str(L.get_material_expression_input_names(b)[pin])
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+name+' '+pin)

    def multiply(a,b):
        n=node(u.MaterialExpressionMultiply);wire(a,n,0);wire(b,n,1);return n

    reveal=node(u.MaterialExpressionScalarParameter,parameter_name='Reveal',default_value=1.0)
    glow=node(u.MaterialExpressionScalarParameter,parameter_name='ResultGlow',default_value=0.0)
    gold=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.55,.36,.12,1))
    if texture:
        sample=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='CardAtlas',texture=texture)
        uv=node(u.MaterialExpressionTextureCoordinate)
        if columns>1:
            custom=node(u.MaterialExpressionCustom,code=(ROOT/'DealerCardUV.hlsl').read_text(encoding='utf-8'),
                output_type=u.CustomMaterialOutputType.CMOT_FLOAT2)
            inputs={'UV':uv,'CardIndex':node(u.MaterialExpressionScalarParameter,parameter_name='CardIndex',default_value=0.0),
                'Columns':node(u.MaterialExpressionConstant,r=float(columns)),'Rows':node(u.MaterialExpressionConstant,r=float(rows))}
            pins=[]
            for key in inputs:
                pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
            custom.set_editor_property('inputs',pins)
            for key,expr in inputs.items():wire(expr,custom,key)
            uv=custom
        wire(uv,sample,0)
        alpha=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True);wire(sample,alpha,0,'RGBA')
        color=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False);wire(sample,color,0,'RGBA')
    else:
        color=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.32,.23,.11,1))
        alpha=node(u.MaterialExpressionConstant,r=.72)
    add=node(u.MaterialExpressionAdd);wire(color,add,0);wire(multiply(glow,gold),add,1)
    inverse=node(u.MaterialExpressionEyeAdaptationInverse);wire(add,inverse,0)
    wire(node(u.MaterialExpressionConstant,r=1.0),inverse,1)
    if not L.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Emissive connection failed')
    opacity=multiply(alpha,reveal)
    if not L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY):raise RuntimeError('Opacity connection failed')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material compilation failed '+name+': '+str(errors))
    E.set_metadata_tag(mat,'DealerAuthored','20261004');save(mat)
    return mat


materials={'DealerFace':material('M_DealerFace',textures['T_DealerFaces'],13,4),
    'DealerBack':material('M_DealerBack',textures['T_DealerBack']),
    'DealerEdge':material('M_DealerEdge'),
    'DealerResult':material('M_DealerResult',textures['T_DealerResults'],3,3)}
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    options=u.FbxImportUI()
    for key,value in {'import_mesh':True,'import_as_skeletal':False,'mesh_type_to_import':u.FBXImportType.FBXIT_STATIC_MESH,
        'automated_import_should_detect_type':False,'import_materials':False,'import_textures':False}.items():options.set_editor_property(key,value)
    data=options.get_editor_property('static_mesh_import_data')
    for key,value in {'combine_meshes':True,'auto_generate_collision':False,'import_uniform_scale':1.0,
        'convert_scene':True,'convert_scene_unit':False,'normal_import_method':u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}.items():data.set_editor_property(key,value)
    mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    for entry in json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8')):
        task=u.AssetImportTask()
        for key,value in {'filename':entry['fbx'],'destination_path':DEST+'/Meshes','destination_name':entry['name'],
            'automated':True,'replace_existing':True,'save':False,'options':options}.items():task.set_editor_property(key,value)
        A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/Meshes/'+entry['name'])
        if not mesh:raise RuntimeError('Mesh import failed '+entry['name'])
        for slot in entry['slots']:
            index=mesh.get_material_index(slot)
            if index<0:raise RuntimeError('Missing authored material slot '+slot)
            mesh.set_material(index,materials[slot])
        settings=mesh_editor.get_lod_build_settings(mesh,0)
        settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True
        mesh_editor.set_lod_build_settings(mesh,0,settings);save(mesh)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
infernal=runpy.run_path(str(ROOT/'InfernalV2/install_ue.py'))
receipt['saved_assets']+=infernal['receipt']['saved_assets']
receipt['result_revision']=2
audio=runpy.run_path(str(ROOT/'AudioV3/install_ue.py'))
receipt['saved_assets']+=audio['receipt']['saved_assets']
receipt['audio_revision']=3
selection=runpy.run_path(str(ROOT/'SelectionV5/install_ue.py'))
receipt['saved_assets']+=selection['receipt']['saved_assets']
receipt['selection_revision']=5
receipt['complete']=True;record()
print('DEALER_ASSETS_SAVED cards=52 meshes=2 materials=4 textures=3 tested=false rendered=false')
