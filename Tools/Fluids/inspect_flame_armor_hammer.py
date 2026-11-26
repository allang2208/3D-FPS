"""Read the equipped hammer and existing flame components without changing PIE."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FlameArmor20261016/VisibilityFix/hammer-live.json'

def safe(fn):
    try:
        return fn()
    except Exception as exc:
        return 'ERROR: ' + str(exc)

def vector(v):
    return [v.x, v.y, v.z]

def primitive(c):
    return dict(name=c.get_path_name(), visible=c.is_visible(),
                hidden=c.get_editor_property('hidden_in_game'),
                owner_only=c.get_editor_property('only_owner_see'),
                owner_no_see=c.get_editor_property('owner_no_see'),
                first_person=str(c.get_editor_property('first_person_primitive_type')),
                position=vector(c.get_world_location()), scale=vector(c.get_world_scale()),
                parent=str(c.get_attach_parent()), tags=[str(t) for t in c.component_tags])

report = {'worlds': [], 'heads': []}
catalog = json.loads((ROOT / 'Content/ColdSteelData/warhammer-modules.json').read_text(encoding='utf-8-sig'))
for key, spec in catalog['slots']['hammer_heads'].items():
    mesh = u.load_asset(spec['mesh'])
    bounds = mesh.get_bounding_box()
    report['heads'].append({'option': key, 'asset': mesh.get_path_name(),
                            'min': vector(bounds.min), 'max': vector(bounds.max)})
for world in u.EditorLevelLibrary.get_pie_worlds(False):
    row = {'world': world.get_path_name(), 'pawns': []}
    report['worlds'].append(row)
    for pawn in u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter):
        player = {'pawn': pawn.get_path_name(), 'components': []}
        row['pawns'].append(player)
        for c in pawn.get_components_by_class(u.PrimitiveComponent):
            tags = [str(t) for t in c.component_tags]
            asset = c.static_mesh if isinstance(c, u.StaticMeshComponent) else (
                c.get_editor_property('asset') if isinstance(c, u.NiagaraComponent) else None)
            if not (any(t.startswith('SwordSlot=') for t in tags) or
                    'ProductionTool' in c.get_name() or
                    (asset and 'FlameArmor' in asset.get_path_name())):
                continue
            data = primitive(c)
            data['asset'] = asset.get_path_name() if asset else None
            if isinstance(c, u.NiagaraComponent):
                data['active'] = c.is_active()
                data['params'] = {key: safe(lambda key=key: c.get_variable_float('User.'+key))
                                  for key in ('Fade', 'Detail', 'Coverage', 'UpperVisibility', 'WeaponSize')}
            player['components'].append(data)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('FLAME_ARMOR_HAMMER', json.dumps(report, ensure_ascii=False))
