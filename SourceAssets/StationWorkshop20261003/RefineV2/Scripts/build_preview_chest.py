"""Saved skeletal treasure preview with the production-owned collision shape."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
rules=json.loads((ROOT/'Config/workshop.json').read_text('utf8'));spec=rules['props'][0]
path=rules['preview_chest_blueprint'];folder,name=path.rsplit('/',1)
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();bp=u.load_asset(path)
if not bp:
    E.make_directory(folder);factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.SkeletalMeshActor)
    bp=A.create_asset(name,folder,u.Blueprint,factory)
    S=u.get_engine_subsystem(u.SubobjectDataSubsystem) or u.new_object(u.SubobjectDataSubsystem)
    F=u.SubobjectDataBlueprintFunctionLibrary;handles=S.k2_gather_subobject_data_for_blueprint(bp)
    root=next(h for h in handles if F.is_root_component(F.get_data(h)))
    params=u.AddNewSubobjectParams(parent_handle=root,new_class=u.BoxComponent,blueprint_context=bp)
    handle,reason=S.add_new_subobject(params)
    if not F.is_handle_valid(handle):raise RuntimeError('Treasure collision component creation failed '+str(reason))
    S.rename_subobject(handle,u.Text('TreasureCollision'))
    box=F.get_object(F.get_data(handle));box.set_mobility(u.ComponentMobility.MOVABLE)
    box.set_box_extent(u.Vector(*spec['collision_extent']),False);box.set_collision_profile_name('BlockAll')
    box.set_editor_property('relative_location',u.Vector(*spec['collision_center']))
    mesh=F.get_object(F.get_data(root));mesh.set_mobility(u.ComponentMobility.MOVABLE)
    mesh.set_skeletal_mesh_asset(u.load_asset(spec['skeletal_mesh']));mesh.set_collision_profile_name('NoCollision')
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Treasure Blueprint compile failed')
    if not E.save_loaded_asset(bp,False):raise RuntimeError('Treasure Blueprint save failed')
receipt=ROOT/'Receipts/assets.json';report=json.loads(receipt.read_text('utf8'))
report['blueprint']=path;report['stage']='assets_saved';receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('STATION_UPPER_CHEST_BLUEPRINT_SAVED',flush=True)
