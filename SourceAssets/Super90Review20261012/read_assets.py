"""Read-only SUPER90 resource, profile and packaging review requested by user."""
import json, re
from pathlib import Path
import unreal as u

O=Path(__file__).parent
P=O.parents[1]
R=u.AssetRegistryHelpers.get_asset_registry()
R.wait_for_completion()
options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True, include_searchable_names=False,
    include_soft_management_references=False, include_hard_management_references=False)
ini=(P/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
cook=re.findall(r'^\+DirectoriesToAlwaysCook=\(Path="([^"]+)"\)',ini,re.M)
report=dict(assets={},profiles={},mounted_shell={},game_run=False)
def inspect(path):
    a=u.load_asset(path)
    s=dict(exists=bool(a),explicit_cook=any(path==c or path.startswith(c+'/') for c in cook),
           referencers=[str(x) for x in R.get_referencers(path,options)])
    if isinstance(a,u.AnimSequence):
        s.update(duration=a.get_play_length(),frames=u.AnimationLibrary.get_num_frames(a),
                 skeleton=a.get_editor_property('skeleton').get_path_name())
    if isinstance(a,u.StaticMesh):
        component=u.StaticMeshComponent()
        component.set_static_mesh(a)
        s['sockets']={name:list(component.get_socket_location(name).to_tuple())
            for name in ('Emitter','AimGuide') if component.does_socket_exist(name)}
    report['assets'][path]=s
    return a
for role in ('reload_continuous','reload_full','fire','fire_last','idle','quick_melee'):
    inspect('/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_'+role)
for kind in ('normal','empty'):
    for n in range(1,8):
        inspect('/Game/Weapons/Super90/Speedloader20261007/Animations/A_Super90_loader_'+kind+'_'+str(n))
inspect('/Game/Weapons/Super90/Speedloader20261007/Animations/A_Super90_loader_cycle')
for asset in R.get_assets_by_path('/Game/Weapons/Super90/TacticalSprint20261007',recursive=True):
    if str(asset.asset_class_path.asset_name)=='AnimSequence':inspect(str(asset.package_name))
for name in ('laser','flashlight','blessed_laser'):
    inspect('/Game/Weapons/Super90/TacticalBottom20261012/SM_'+name)
for family in ('vertical','canted','prism','angled'):
    a=u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family)
    rows=[]
    for clip in a.get_editor_property('clips'):
        base=clip.get_editor_property('base')
        rows.append(dict(base=base.get_path_name(),duration=float(clip.get_editor_property('duration')),
            base_duration=base.get_play_length(),retained=str(clip.get_editor_property('retained')),
            track_end=max((max(t.get_editor_property('times')) for t in clip.get_editor_property('tracks')),default=0)))
    report['profiles'][family]=rows
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
report['mounted_shell']['slots']=[dict(name=str(m.get_editor_property('material_slot_name')),
    imported=str(m.get_editor_property('imported_material_slot_name')),
    material=m.get_editor_property('material_interface').get_path_name() if m.get_editor_property('material_interface') else None)
    for m in mesh.get_editor_property('materials')]
(O/'assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_REVIEW_READ_ONLY',len(report['assets']),'assets',flush=True)
