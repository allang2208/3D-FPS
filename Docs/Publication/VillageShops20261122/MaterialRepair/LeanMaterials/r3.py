from pathlib import Path
import unreal as u, json, os
stage=Path(r'F:/FPSGAMEData/ArtProduction/HillsVillageShops/ShopNetworkAndDistance-20261122/LeanMaterials')
assert Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()==(stage/'Host').resolve()
assets=json.loads((stage/'r3-input.json').read_bytes())
audit=os.getenv('SHOP_USAGE_PHASE')=='witness'
if audit:
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,50))
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    lib=u.SubobjectDataBlueprintFunctionLibrary
    root=sub.k2_gather_subobject_data_for_instance(actor)[0]
rows=[]
for i,p in enumerate(assets):
    m=u.load_asset(p);assert isinstance(m,u.Material),p
    if audit:
        assert m.get_editor_property('used_with_instanced_static_meshes'),p
        h,r=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root,new_class=u.InstancedStaticMeshComponent))
        c=lib.get_associated_object(lib.get_data(h))
        c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        c.set_material(0,m);c.add_instance(u.Transform(location=[0,i*110,0]),False)
    else:
        m.modify()
        m.set_editor_property('used_with_instanced_static_meshes',False)
        m.set_editor_property('used_with_instanced_static_meshes',True)
        u.MaterialEditingLibrary.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m,False),p
    rows.append(p)
if audit:assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/ShopUsageWitness')
(stage/('r3-witness.json' if audit else 'r3-saved.json')).write_text(json.dumps(rows))
