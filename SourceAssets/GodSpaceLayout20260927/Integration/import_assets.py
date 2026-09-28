"""Import authored hub additions and persist only this batch's new assets."""
import json,runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent
DEST='/Game/Props/GodSpaceLayout20260927'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE is running; no import/save batch started')
DATA=json.loads((ROOT/'placements.json').read_text(encoding='utf8'))
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
report={'saved':[],'complete':False,'tested':False}
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    (ROOT/'Receipts/import.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing dependency '+path)
    return a
def material(name,color,roughness,metallic=0,emissive=None,texture=None):
    path=DEST+'/Materials/'+name
    m=u.load_asset(path)
    if m:return m
    m=TOOLS.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if texture:
        node=L.create_material_expression(m,u.MaterialExpressionTextureSample,0,0)
        node.set_editor_property('texture',texture)
        L.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    else:
        node=L.create_material_expression(m,u.MaterialExpressionConstant3Vector,0,0)
        node.set_editor_property('constant',u.LinearColor(*color,1))
        L.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,roughness),(u.MaterialProperty.MP_METALLIC,metallic),(u.MaterialProperty.MP_SPECULAR,.2)]:
        n=L.create_material_expression(m,u.MaterialExpressionConstant,-200,200)
        n.set_editor_property('r',value);L.connect_material_property(n,'',prop)
    if emissive:
        n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector,-200,400)
        n.set_editor_property('constant',u.LinearColor(*emissive,1));L.connect_material_property(n,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.recompile_material(m);save(m);return m

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
E.make_directory(DEST+'/Meshes');E.make_directory(DEST+'/Materials');E.make_directory(DEST+'/Textures')
white=load('/Game/Props/RomanColumn20260915/M_WhiteMarble_V2')
gold=load('/Game/Props/RomanPavilionRoof20260919/WhiteCelestial/M_PavilionAgedGold')
floor_brass=runpy.run_path(str(ROOT/'build_floor_trim_material.py'))['build']()
dark=material('M_GodSpaceBlueStone',(.055,.085,.11),.52,.06)
carpet_builder=runpy.run_path(str(ROOT/'build_navy_carpet.py'))
carpet=carpet_builder['build'](apply_binding=False)
orb=material('M_GodSpaceCore',(.44,.80,.92),.28,.05,(.8,1.7,2.1))
for entry in DATA['new_meshes']:
    if entry['name']=='SM_GodSpaceDistantOcean':continue
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal=False;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
    d=opt.static_mesh_import_data
    d.combine_meshes=True;d.auto_generate_collision=True;d.import_uniform_scale=1
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    d.reorder_material_to_fbx_order=True
    t=u.AssetImportTask();t.filename=entry['file'];t.destination_path=DEST+'/Meshes';t.destination_name=entry['name']
    t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.options=opt
    TOOLS.import_asset_tasks([t])
    mesh=load(DEST+'/Meshes/'+entry['name'])
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        # FBX preserves this source order; import material names are normalized by UE.
        name=entry['materials'][i].lower()
        mat=floor_brass if name=='floor satin brass' else gold if 'brass' in name else (carpet if entry['name']=='SM_GodSpaceStructure' else dark) if 'inlay' in name else orb if 'deity' in name else white
        mesh.set_material(i,mat)
    if entry['name']=='SM_GodSpaceStructure':
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        carpet_builder['configure_carpet_density'](mesh)
    E.set_metadata_tag(mesh,'GodSpaceLayout','20260927-V1-Accepted')
    save(mesh)
ocean_script=ROOT/'import_distant_ocean.py';ocean_namespace={'__file__':str(ocean_script)}
exec(compile(ocean_script.read_text(encoding='utf8'),str(ocean_script),'exec'),ocean_namespace)
report['saved'].extend(ocean_namespace['report']['saved'])
report['complete']=True
(ROOT/'Receipts/import.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_ASSETS_SAVED '+str(len(report['saved'])))
