"""Install the eight refined tile groups and three PBR material families."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
SOURCE=ROOT/'Authored/TilePolish';BASE='/Game/Dungeons/AtmosphereV2';OUT=BASE+'/TilePolish'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
TARGET='/Game/GameMaps/L_Dungeon_Prototype'
if UE.get_game_world():raise RuntimeError('Gameplay is active; tile installation deferred')
if UE.get_editor_world().get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Target dungeon is not loaded; current editor preserved')
manifest=json.loads((SOURCE/'geometry-manifest.json').read_text())
textures=json.loads((SOURCE/'material-manifest.json').read_text())
receipt={'map':TARGET,'meshes':{},'materials':{},'geometry':manifest['stats'],'tests_run':False,'visual_acceptance':'pending user review'}
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
def texture(name,filename,channel):
    path=OUT+'/Textures/T_'+name
    t=u.load_asset(path)
    if True:
        task=u.AssetImportTask();task.filename=str(filename);task.destination_path=OUT+'/Textures';task.destination_name='T_'+name
        task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;A.import_asset_tasks([task]);t=u.load_asset(path)
        if not t:raise RuntimeError('Texture import failed: '+path)
        t.set_editor_property('srgb',channel=='BaseColor')
        if channel=='Normal':
            t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);t.set_editor_property('flip_green_channel',True)
        elif channel!='BaseColor':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(t)
    return t
def output(n,prop,pin=''):
    if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Unable to wire material '+prop)
for name,maps in textures.items():
    loaded={channel:texture(name+'_'+channel,file,channel) for channel,file in maps.items()}
    path=OUT+'/Materials/M_'+name;m=u.load_asset(path)
    if not m:
        m=A.create_asset('M_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
        for channel,pin in [('BaseColor','BASE_COLOR'),('Roughness','ROUGHNESS'),('Normal','NORMAL')]:
            n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.texture=loaded[channel]
            n.sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'Roughness':u.MaterialSamplerType.SAMPLERTYPE_MASKS,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[channel]
            output(n,pin,'R' if channel=='Roughness' else '')
        L.layout_material_expressions(m);L.recompile_material(m);save(m)
    receipt['materials'][name]=path

for entry in manifest['objects']:
    name=entry['name'];path=BASE+'/Structure/'+name
    task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=BASE+'/Structure';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Mesh import failed: '+path)
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=str(slot.get_editor_property('material_slot_name')).removeprefix('V2_')
        material_path=receipt['materials'].get(key,BASE+'/Materials/M_'+key)
        material=u.load_asset(material_path)
        if not material:raise RuntimeError('Missing material for '+key)
        mesh.set_material(index,material)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;mesh.set_editor_property('nanite_settings',settings)
    save(mesh);receipt['meshes'][name]={'path':path,'source':entry['fbx']}
    (ROOT/'Receipts/tile-polish-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

opacity=texture('TileLeak_Opacity',SOURCE/'Textures/TileLeak_Opacity.png','Opacity')
decal_path=OUT+'/Materials/M_TileLeak';decal=u.load_asset(decal_path)
if not decal:
    decal=A.create_asset('M_TileLeak',OUT+'/Materials',u.Material,u.MaterialFactoryNew())
    decal.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    decal.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    n=L.create_material_expression(decal,u.MaterialExpressionTextureSample);n.texture=opacity;n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
    L.connect_material_property(n,'R',u.MaterialProperty.MP_OPACITY)
    color=L.create_material_expression(decal,u.MaterialExpressionConstant3Vector);color.constant=u.LinearColor(.055,.043,.026,1)
    L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=L.create_material_expression(decal,u.MaterialExpressionConstant);rough.r=.48
    L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    L.layout_material_expressions(decal);L.recompile_material(decal);save(decal)
for actor in AA.get_all_level_actors():
    if actor.get_actor_label().startswith('DGN_AV2_TilePolish_Leak_'):AA.destroy_actor(actor)
for i,(pos,yaw,size) in enumerate([
    ([380,-385,190],-90,[5,77,178]),([155,-15,152],90,[5,72,141]),
    ([690,-385,122],-90,[5,58,110]),([645,405,149],90,[5,75,138]),
    ([1140,-784,152],-90,[5,68,142]),([1790,-15,148],90,[5,64,137])]):
    actor=AA.spawn_actor_from_class(u.DecalActor,u.Vector(*pos),u.Rotator(pitch=0,yaw=yaw,roll=0))
    actor.set_actor_label('DGN_AV2_TilePolish_Leak_'+str(i));actor.set_folder_path('DungeonAtmosphereV2/SurfaceHistory')
    c=actor.get_component_by_class(u.DecalComponent);c.set_decal_material(decal)
    c.set_editor_property('decal_size',u.Vector(*size));c.set_editor_property('sort_order',2)
receipt['new_local_leaks']=6
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():raise RuntimeError('Tile refinement map save failed')
(ROOT/'Receipts/tile-polish-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TILE_POLISH_IMPORTED',len(receipt['meshes']),'existing groups; 3 PBR surfaces, 6 localized leaks; saved')
