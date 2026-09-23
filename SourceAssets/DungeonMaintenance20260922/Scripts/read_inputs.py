"""Read actual ownership/references before retiring user-rejected generated props."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Sources';OUT.mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem);E=u.EditorAssetLibrary
if not UE or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Requires FPSGAME editor')
roots=['/Game/Dungeons/AtmosphereV2/Generated','/Game/Dungeons/AtmosphereV2/RoomInteriors/Generated','/Game/Dungeons/IndustrialV1/Props/GoddessCandidate']
data=dict(world=UE.get_editor_world().get_path_name(),gameplay=bool(UE.get_game_world()),
 dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],roots=roots,actors=[],assets=[])
for a in AA.get_all_level_actors():
    if not a.get_actor_label().startswith('DGN_'):continue
    components=[]
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        p=c.static_mesh.get_path_name()
        if any(p.startswith(root+'/') for root in roots):
            components.append(dict(name=c.get_name(),mesh=p,materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
    if components:data['actors'].append(dict(label=a.get_actor_label(),path=a.get_path_name(),package=a.get_package().get_name(),location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple()),components=components))
for root in roots:
    for path in E.list_assets(root,True,False):
        data['assets'].append(dict(path=path,referencers=list(E.find_package_referencers_for_asset(path,False))))
(OUT/'retirement-inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(dict(world=data['world'],gameplay=data['gameplay'],dirty_maps=data['dirty_maps'],actors=data['actors'],assets=len(data['assets']))))
