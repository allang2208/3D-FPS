"""Create missing dependencies, then install V2 options and V3 upper grip. No acceptance run.
Use the existing editor bridge or a commandlet when the editor is closed.
"""
import unreal as u
import json, runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# Current user-selected reference design; the old sphere-head branch below is archival.
import runpy
runpy.run_path(str(ROOT/'BarkRebuildV21/import_model.py'),run_name='__main__')
raise SystemExit(0)
DEST='/Game/Weapons/ApprenticeStaff20260927'
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before importing staff assets.')
tools=u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
def import_missing(source,name,destination,options=None):
    existing=u.load_asset(destination+'/'+name)
    if existing:return existing
    task=u.AssetImportTask();task.set_editor_property('filename',str(source));task.set_editor_property('destination_path',destination)
    task.set_editor_property('destination_name',name);task.set_editor_property('automated',True);task.set_editor_property('save',False)
    if options:task.set_editor_property('options',options)
    tools.import_asset_tasks([task]);asset=u.load_asset(destination+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset
textures={}
for key in ('base_color','roughness','metallic','normal'):
    asset=u.load_asset(DEST+'/Textures/T_Staff_'+key)
    if not asset:
        asset=import_missing(ROOT/f'Meshy/staff/downloads/texture_urls_0_{key}.png','T_Staff_'+key,DEST+'/Textures')
        asset.set_editor_property('srgb',key=='base_color')
        if key=='normal':asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        elif key!='base_color':asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(asset)
    textures[key]=asset
def scalar(m,value,prop):
    n=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',value)
    u.MaterialEditingLibrary.connect_material_property(n,'',prop)
wood=u.load_asset(DEST+'/Materials/M_Staff_Wood')
if not wood:
    wood=tools.create_asset('M_Staff_Wood',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    for key,prop in [('base_color',u.MaterialProperty.MP_BASE_COLOR),('roughness',u.MaterialProperty.MP_ROUGHNESS),('metallic',u.MaterialProperty.MP_METALLIC),('normal',u.MaterialProperty.MP_NORMAL)]:
        n=u.MaterialEditingLibrary.create_material_expression(wood,u.MaterialExpressionTextureSample);n.set_editor_property('texture',textures[key])
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='base_color' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        u.MaterialEditingLibrary.connect_material_property(n,'RGB' if key in ('base_color','normal') else 'R',prop)
    u.MaterialEditingLibrary.recompile_material(wood);save(wood)
palette={'ice':(.12,.6,.9),'fire':(.8,.14,.025),'light':(.16,.62,.3),'electric':(.38,.18,.9),'metal':(.21,.23,.25)}
for key,color in palette.items():
    if u.load_asset(DEST+'/Materials/M_Staff_'+key):continue
    m=tools.create_asset('M_Staff_'+key,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    n=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionConstant3Vector)
    n.set_editor_property('constant',u.LinearColor(*color,1));u.MaterialEditingLibrary.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
    scalar(m,.7 if key=='metal' else 0,u.MaterialProperty.MP_METALLIC)
    scalar(m,.38 if key in ('metal','ice','electric') else .65,u.MaterialProperty.MP_ROUGHNESS)
    if key!='metal':u.MaterialEditingLibrary.connect_material_property(n,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    u.MaterialEditingLibrary.recompile_material(m);save(m)
options=u.FbxImportUI();options.set_editor_property('import_mesh',True);options.set_editor_property('import_as_skeletal',False)
options.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
options.set_editor_property('import_materials',False);options.set_editor_property('import_textures',False)
data=options.get_editor_property('static_mesh_import_data');data.set_editor_property('combine_meshes',True)
data.set_editor_property('auto_generate_collision',False);data.set_editor_property('import_uniform_scale',1)
data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
base_names=('SM_Staff_Base','SM_Staff_Body','SM_Staff_head_crystal_false','SM_Staff_grip_lining_false')
for entry in json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8')):
    if entry['name'] not in base_names or u.load_asset(DEST+'/Meshes/'+entry['name']):continue
    asset=import_missing(entry['fbx'],entry['name'],DEST+'/Meshes',options)
    for i in range(len(asset.get_editor_property('static_materials'))):asset.set_material(i,wood)
    save(asset)
icons=[(ROOT/'Reference/apprentice_staff_original.png','T_ApprenticeStaff')]+[(p,'T_'+p.stem) for p in (ROOT/'Reference/LegacyIcons').glob('*.png')]
for source,name in icons:
    if u.load_asset(DEST+'/Icons/'+name):continue
    asset=import_missing(source,name,DEST+'/Icons');asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);save(asset)
runpy.run_path(str(ROOT/'RepairV2/import_repaired_staff.py'),run_name='__main__')
runpy.run_path(str(ROOT/'UpperGripV3/import_upper_grip.py'),run_name='__main__')
