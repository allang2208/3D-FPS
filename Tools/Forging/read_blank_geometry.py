"""Read only the forge assets involved in the reported hidden strike guide."""
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir())
out = root / 'SourceAssets/ForgeHammerRefine20261024'
out.mkdir(parents=True, exist_ok=True)
profiles = json.loads((root / 'Content/ColdSteelData/forge-blanks.json').read_text(encoding='utf-8-sig'))
paths = [s['mesh'] for s in profiles['profiles']['warhammer']['stages']]
paths += ['/Game/Props/ForgeInteraction20260927/SM_ForgeRing']
rows = []
for path in paths:
    mesh = u.load_asset(path)
    bounds = mesh.get_bounding_box()
    rows.append({'asset': path, 'min': [bounds.min.x, bounds.min.y, bounds.min.z],
                 'max': [bounds.max.x, bounds.max.y, bounds.max.z],
                 'materials': [str(s.material_interface.get_path_name()) if s.material_interface else None
                               for s in mesh.get_editor_property('static_materials')]})
report = {'meshes': rows, 'dirty_target_packages': [p.get_path_name() for p in
    u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if p.get_path_name().startswith('/Game/Props/ForgeInteraction20260927')]}
guide = u.load_asset('/Game/Props/ForgeInteraction20260927/M_ForgeGuide')
report['guide_material'] = {key: str(guide.get_editor_property(key)) for key in
    ('two_sided', 'blend_mode', 'shading_model', 'disable_depth_test')}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['running_forge'] = []
if world:
    for actor in u.ActorIterator(world, u.ForgeInteraction):
        report['running_forge'].append({'actor': actor.get_name(), 'components': [
            {'name': c.get_name(), 'visible': c.is_visible(),
             'position': str(c.get_relative_location()), 'scale': str(c.get_relative_scale3d()),
             'mesh': c.static_mesh.get_path_name() if c.static_mesh else None}
            for c in actor.get_components_by_class(u.StaticMeshComponent)
            if c.get_name() in ('SwordBlank', 'HeatSpot', 'HammerAim')]})
(out / 'geometry_before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
