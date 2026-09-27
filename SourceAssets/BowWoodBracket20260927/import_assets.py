"""Import/save the independent carved sight. No PIE, screenshot or live equip."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).parent;DEST='/Game/Weapons/DarkBow20260925/WoodBracketV19'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=P/'import-receipt.json'
r=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'runtime_tested':False,'rendered':False}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(DEST+'/')]
if dirty:raise RuntimeError('Preserve unsaved candidate packages '+str(dirty))

def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    r['saved'][asset.get_name()]=asset.get_path_name()
    receipt.write_text(json.dumps(r,indent=2),encoding='utf8')

def fresh(name):
    if name not in r['saved'] and E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Unowned asset '+name)

def scalar(mat,value):
    n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=value;return n

def color(mat,rgb):
    n=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*rgb,1);return n

def texture(mat,name,kind):
    path='/Game/Weapons/DarkBow20260925/WoodLongbow20260925/Textures/T_WoodLongbow_'+name
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Retained bow texture missing '+path)
    n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=asset;n.sampler_type=kind;return n

materials={}
for slot,name,rgb,rough in [('BracketBowWood','M_Bow_BracketWood',(1,1,1),.50),
    ('BracketWaxedLinen','M_Bow_BracketWaxedLinen',(.085,.062,.035),.85),
    ('BracketEndgrain','M_Bow_BracketEndgrain',(.25,.135,.061),.60)]:
    if name in r['saved']:
        materials[slot]=u.load_asset(r['saved'][name]);continue
    fresh(name);mat=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    L.connect_material_property(scalar(mat,0),'',u.MaterialProperty.MP_METALLIC)
    if slot=='BracketBowWood':
        base=texture(mat,'BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        orm=texture(mat,'ORM',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        normal=texture(mat,'Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        tint=L.create_material_expression(mat,u.MaterialExpressionVertexColor)
        multiply=L.create_material_expression(mat,u.MaterialExpressionMultiply)
        L.connect_material_expressions(base,'RGB',multiply,'A')
        L.connect_material_expressions(tint,'RGB',multiply,'B')
        L.connect_material_property(multiply,'',u.MaterialProperty.MP_BASE_COLOR)
        mx=L.create_material_expression(mat,u.MaterialExpressionMax)
        L.connect_material_expressions(scalar(mat,rough),'',mx,'B')
        L.connect_material_expressions(orm,'G',mx,'A');L.connect_material_property(mx,'',u.MaterialProperty.MP_ROUGHNESS)
        # Gentle grain, kept consistent with the longbow while avoiding harsh
        # normal exaggeration on a small curved aiming aperture.
        lerp=L.create_material_expression(mat,u.MaterialExpressionLinearInterpolate)
        L.connect_material_expressions(scalar(mat,.28),'',lerp,'Alpha')
        L.connect_material_expressions(color(mat,(0,0,1)),'',lerp,'A')
        L.connect_material_expressions(normal,'RGB',lerp,'B')
        L.connect_material_property(lerp,'',u.MaterialProperty.MP_NORMAL)
        L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    else:
        L.connect_material_property(color(mat,rgb),'',u.MaterialProperty.MP_BASE_COLOR)
        L.connect_material_property(scalar(mat,rough),'',u.MaterialProperty.MP_ROUGHNESS)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material compilation failed '+str(errors))
    save(mat);materials[slot]=mat

name='SM_Bow_WoodBracketSight';source=P/'Export'/(name+'.fbx')
sha=hashlib.sha256(source.read_bytes()).hexdigest()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
if name not in r['saved'] or r.get('fbx_sha256')!=sha:
    fresh(name)
    if name in r['saved']:
        raise RuntimeError('Changed FBX requires a fresh candidate asset name; existing saved asset preserved')
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.static_mesh_import_data.combine_meshes=True
    opt.static_mesh_import_data.auto_generate_collision=False
    opt.static_mesh_import_data.build_nanite=False
    opt.static_mesh_import_data.generate_lightmap_u_vs=False
    opt.static_mesh_import_data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;task.options=opt;A.import_asset_tasks([task])
    asset=u.load_asset(DEST+'/'+name)
    if not asset:raise RuntimeError('Sight import missing')
    slots=list(asset.static_materials)
    for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
    asset.static_materials=slots
    r['fbx_sha256']=sha;r['sight_pin_cm']=json.loads((P/'authoring.json').read_text())['sight_pin_cm']
    save(asset)
print('BOW_WOOD_BRACKET_SIGHT_SAVED',json.dumps(r))
