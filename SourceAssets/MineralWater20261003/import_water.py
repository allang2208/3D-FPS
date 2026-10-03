"""Import and save only this consumable revision; no maps/PIE/acceptance work."""
from pathlib import Path
import json
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/MineralWater20261003')
SPEC=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
DEST='/Game/Items/Consumables/MineralWater20261003'
TOOLS=u.AssetToolsHelpers.get_asset_tools();LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
receipt={'saved':False,'materials':{},'meshes':{},'runtime_tested':False}
if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Stop Play before importing/saving mineral-water assets; the active game was left untouched.')
def record():(OUT/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not EAL.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Save failed: '+asset.get_path_name())
def node(mat,kind,**props):
    n=LIB.create_material_expression(mat,kind)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin=None,output=''):
    names=[str(n) for n in LIB.get_material_expression_input_names(b)]
    if pin is None:pin=names[0]
    aliases={'AGreaterThanB':'A>B','AEqualsB':'A==B','ALessThanB':'A<B'}
    if pin not in names:
        expected=aliases.get(pin,pin)
        pin=next((n for n in names if n.replace(' ','')==expected),pin)
    if not LIB.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material input '+pin+' available '+str(names))
def prop(n,kind,output=''):
    if not LIB.connect_material_property(n,output,kind):raise RuntimeError('Material property '+str(kind))
def scalar(mat,value,kind):
    n=node(mat,u.MaterialExpressionConstant,r=value);prop(n,kind);return n
def vector(mat,v):return node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
def material(name,color,rough,thin=False):
    path=DEST+'/Materials/M_MineralWater_'+name
    m=u.load_asset(path) or TOOLS.create_asset('M_MineralWater_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    # Rebuild only this revision's own graphs when resuming a partial import.
    for expression in list(LIB.get_material_expressions(m)):LIB.delete_material_expression(m,expression)
    c=vector(m,color);prop(c,u.MaterialProperty.MP_BASE_COLOR)
    scalar(m,rough,u.MaterialProperty.MP_ROUGHNESS);scalar(m,0,u.MaterialProperty.MP_METALLIC)
    if thin:
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('two_sided',True)
        trans=node(m,u.MaterialExpressionThinTranslucentMaterialOutput)
        wire(c,trans,str(LIB.get_material_expression_input_names(trans)[0]))
        scalar(m,0,u.MaterialProperty.MP_OPACITY)
    return m
label_name='T_MineralWater_Label'
label=u.load_asset(DEST+'/Textures/'+label_name)
if label is None:
    t=u.AssetImportTask();t.filename=str(OUT/'Textures'/(label_name+'.png'))
    t.destination_name=label_name;t.destination_path=DEST+'/Textures';t.automated=True;t.save=False
    TOOLS.import_asset_tasks([t]);label=u.load_asset(DEST+'/Textures/'+label_name)
if not isinstance(label,u.Texture2D):raise RuntimeError('Label import failed')
label.set_editor_property('srgb',True);save(label)
materials={
    'PET':material('PET',(.955,.985,.975),.12,True),
    'Cap':material('Cap',(.019,.19,.105),.32),
    'Label':material('Label',(.86,.91,.85),.58),
    'Liquid':material('Liquid',(.80,.93,.965),.045,True)
}
paper=materials['Label']
if LIB.get_num_material_expressions(paper)<5:
    n=node(paper,u.MaterialExpressionTextureSample,texture=label)
    prop(n,u.MaterialProperty.MP_BASE_COLOR,'RGB')
water=materials['Liquid']
if LIB.get_num_material_expressions(water)<10:
    water.set_editor_property('tangent_space_normal',False)
    wp=node(water,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    local=node(water,u.MaterialExpressionTransformPosition,
        transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(wp,local)
    z=node(water,u.MaterialExpressionComponentMask,r=False,g=False,b=True,a=False);wire(local,z)
    level=node(water,u.MaterialExpressionScalarParameter,parameter_name='FillHeightCm',default_value=18.4)
    low=node(water,u.MaterialExpressionMin);wire(z,low,'A');wire(level,low,'B')
    difference=node(water,u.MaterialExpressionSubtract);wire(low,difference,'A');wire(z,difference,'B')
    zeros=node(water,u.MaterialExpressionConstant2Vector,r=0,g=0)
    offset=node(water,u.MaterialExpressionAppendVector);wire(zeros,offset,'A');wire(difference,offset,'B')
    world=node(water,u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(offset,world);prop(world,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    # Collapsed shoulder rings become the flat meniscus and use an upward normal.
    up=vector(water,(0,0,1))
    upworld=node(water,u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(up,upworld)
    normals=node(water,u.MaterialExpressionVertexNormalWS)
    select=node(water,u.MaterialExpressionIf)
    wire(z,select,'A');wire(level,select,'B');wire(upworld,select,'AGreaterThanB');wire(upworld,select,'AEqualsB');wire(normals,select,'ALessThanB')
    prop(select,u.MaterialProperty.MP_NORMAL)
for key,m in materials.items():
    LIB.recompile_material(m);save(m);receipt['materials'][key]=m.get_path_name();record()
for name,entry in SPEC['meshes'].items():
    mesh=u.load_asset(DEST+'/'+name)
    if mesh is None:
        options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
        options.import_materials=False;options.import_textures=False
        options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=False;data.auto_generate_collision=False
        data.generate_lightmap_u_vs=True;data.one_convex_hull_per_ucx=True
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        t=u.AssetImportTask();t.filename=entry['file'];t.destination_path=DEST;t.destination_name=name
        t.automated=True;t.replace_existing=False;t.save=False;t.options=options
        TOOLS.import_asset_tasks([t]);mesh=u.load_asset(DEST+'/'+name)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Mesh import failed: '+name)
    for index,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unknown material slot: '+key)
        mesh.set_material(index,materials[key])
    # Thin transparent plastic and liquid use the regular static-mesh path.
    if name!='SM_MineralWater_Cap':
        ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
    save(mesh);receipt['meshes'][name]={'asset':mesh.get_path_name(),'saved':True,'source':entry['file']};record()
receipt['saved']=True;record()
u.log('MINERAL_WATER_ASSETS_SAVED '+str(len(receipt['meshes'])))
