"""Import this rack revision and update only its two existing scene actors."""
from pathlib import Path
from datetime import datetime
import json,re,unreal as u
ROOT=Path(__file__).resolve().parents[1];DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopRackPolish';TARGET='/Game/GameMaps/L_Dungeon_Prototype'
MAN=json.loads((ROOT/'Authored/manifest.json').read_text());SRC=json.loads((ROOT/'Sources/scene-inputs.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if not UE or UE.get_game_world():raise RuntimeError('Editor must be out of gameplay for rack installation')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
if UE.get_editor_world().get_path_name().split('.')[0]!=TARGET:raise RuntimeError('Preserve current map; open the dungeon before this scoped installation')
actors={a.get_actor_label():a for a in AA.get_all_level_actors()};targets=[]
for src in SRC['actors']:
    a=actors.get(src['label']);c=a.get_component_by_class(u.StaticMeshComponent) if a else None
    if not c or not c.static_mesh:raise RuntimeError('Expected rack actor missing '+src['label'])
    e=next((e for e in MAN['objects'] if e['replaces'] in src['mesh'] or e['name'] in src['mesh']),None)
    if not e:raise RuntimeError('No scoped replacement for '+src['label'])
    if c.static_mesh.get_path_name()!=src['mesh'] and not c.static_mesh.get_path_name().startswith(DEST+'/Meshes/'+e['name']):raise RuntimeError('Preserve independently changed rack actor '+src['label'])
    targets.append((a,c,e))
receipt=dict(stage='importing',meshes={},actors=[],tests_run=False,screenshots_taken=False)
def write():(ROOT/'Receipts/install.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+asset.get_path_name())

parent=u.load_asset('/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/M_WBK_Surface')
for key,col,rough in [('PackingTape',[.26,.175,.085],.72),('FuseCeramic',[.49,.49,.43],.62)]:
    name='MI_WSRack_'+key;path=DEST+'/Materials/'+name;mi=u.load_asset(path)
    if not mi:mi=A.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mi.modify();L.set_material_instance_parent(mi,parent)
    for ch in ('Base','Normal','Roughness','Metallic'):L.set_material_instance_scalar_parameter_value(mi,'Use'+ch+'Map',0)
    for k,value in [('MetallicValue',0),('RoughnessValue',rough),('DustAmount',.015),('Specular',.28)]:L.set_material_instance_scalar_parameter_value(mi,k,value)
    L.set_material_instance_vector_parameter_value(mi,'BaseTint',u.LinearColor(*col,1));L.update_material_instance(mi);save(mi)
clean=lambda name:re.sub(r'[._][0-9]{3}$','',name)
aliases={clean(k):v for k,v in MAN['materials'].items()}
for e in MAN['objects']:
    path=DEST+'/Meshes/'+e['name'];old=u.load_asset(path)
    task=u.AssetImportTask();task.filename=e['fbx'];task.destination_path=DEST+'/Meshes';task.destination_name=e['name'];task.automated=True;task.replace_existing=bool(old);task.replace_existing_settings=True;task.save=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.generate_lightmap_u_vs=False;d.auto_generate_collision=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Rack import failed '+path)
    mesh.modify()
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=clean(str(slot.get_editor_property('material_slot_name')));mat=u.load_asset(aliases[key])
        if not mat:raise RuntimeError('Required rack material missing '+aliases[key])
        mesh.set_material(i,mat)
    # Small stock and printed faces use their authored triangles without Nanite reduction.
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=False;mesh.set_editor_property('nanite_settings',settings)
    save(mesh);receipt['meshes'][e['name']]=mesh.get_path_name();write()
for a,c,e in targets:
    a.modify();c.modify();c.set_static_mesh(u.load_asset(receipt['meshes'][e['name']]));c.set_editor_property('override_materials',[])
    receipt['actors'].append(dict(label=a.get_actor_label(),mesh=c.static_mesh.get_path_name(),location=list(a.get_actor_location().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple())))
receipt['stage']='scene_changed';write()
if not ED.save_current_level():raise RuntimeError('Rack map save failed; retain the live scene for saving')
receipt.update(stage='map_saved',saved_at=datetime.now().isoformat());write()

# The full dungeon restoration must reuse this final revision rather than the old stock.
path=ROOT.parent/'DungeonWorkbenchKit20260921/Config/surroundings.json';data=json.loads(path.read_text());bylabel={row['label']:row for row in data['actors']}
for src in SRC['actors']:
    result=next(r for r in receipt['actors'] if r['label']==src['label']);row=bylabel.get(src['label'])
    if row is None:
        row=dict(label=src['label'],class_path='/Script/Engine.StaticMeshActor',location=src['location'],rotation=src['rotation'],scale=src['scale'],hidden=src['hidden'],visible=src['visible'],cast_shadow=True,collision='NoCollision');data['actors'].append(row)
    row['mesh']=result['mesh'];row['materials']=[]
path.write_text(json.dumps(data,indent=2),encoding='utf-8')
print('WORKSHOP_RACK_MAP_SAVED '+json.dumps(receipt))
