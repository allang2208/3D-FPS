"""Read only the scene inputs needed to author the gate and shallow water."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not UE or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('FPSGAME editor required')
world=UE.get_editor_world()
if world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':raise RuntimeError('Dungeon map is required')
records=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m or not any(k in m.get_name() for k in ('MachineGrille','WetPatches')):continue
        b=m.get_bounds()
        records.append(dict(label=a.get_actor_label(),mesh=m.get_path_name(),location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),bounds_origin=list(b.origin.to_tuple()),bounds_extent=list(b.box_extent.to_tuple()),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
water=u.load_asset('/Game/Props/RomanFountain20260917/Materials/MIC_FountainWaveWater')
record=dict(world=world.get_path_name(),actors=records,fountain_parent=water.get_editor_property('parent').get_path_name() if water else None)
(ROOT/'Sources').mkdir(parents=True,exist_ok=True)
(ROOT/'Sources/scene-inputs.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
