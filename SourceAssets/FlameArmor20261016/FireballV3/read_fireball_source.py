"""Read the live fireball asset contract for the requested flame-armor revision."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FlameArmor20261016/FireballV3'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, emitters, LIB

report = {'systems': {}, 'materials': {}, 'dirty': []}
report['dirty'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
for leaf in ('NS_FireballSlowBurnCore', 'NS_FireballVelocityTrail'):
    system = u.load_asset('/Game/Skills/Fireball/' + leaf)
    rows = []
    for name in emitters(system):
        renderer = json.loads(API.call_method('GetRendererData', (ref(system, name, renderer=0),)).get_editor_property('property_values'))
        row = {'name': name, 'renderer': renderer, 'assignments': {}}
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            module = u.EditorAssetLibrary.get_metadata_tag(system, 'Fireball.Assignments.'+name+'.'+stage)
            if module:
                row['assignments'][stage] = {field: u.RainAssetEditor.read_input(system, name, stage, module, field)
                    for field in ('Particles.Color', 'Particles.DynamicMaterialParameter', 'Particles.SpriteSize')}
        rows.append(row)
    report['systems'][leaf] = rows
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'fireball-source.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('FIREBALL_SOURCE', json.dumps({key: [{'name': row['name'], 'material': row['renderer'].get('Material'),
     'grid': row['renderer'].get('SubImageSize'), 'values': row['assignments']} for row in rows]
     for key, rows in report['systems'].items()}))
print('DIRTY_TARGETS', [p for p in report['dirty'] if 'FlameArmor' in p])
