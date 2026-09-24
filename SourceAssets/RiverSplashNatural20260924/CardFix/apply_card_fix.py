"""Save only the crown material fix. No game, emitter reset or texture reimport."""
import importlib
import json
from pathlib import Path
import sys
import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if root != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
sys.path.insert(0, str(root / 'Tools/Fluids'))
import author_river_splash_natural as natural
natural = importlib.reload(natural)
material = u.load_asset('/Game/Fluids/RiverPilot20260923/M_RiverCrown')
atlas = u.load_asset('/Game/Fluids/RiverSplashNatural20260924/T_RiverSplashPacked')
before = {'allow_front_layer_translucency': material.get_editor_property('allow_front_layer_translucency'),
          'output_translucent_velocity': material.get_editor_property('output_translucent_velocity')}
natural.b.SAVED.clear()
natural.material('M_RiverCrown', True, atlas)
record = {'saved': list(natural.b.SAVED), 'before': before,
          'fix': ['exact-zero empty coverage', 'discard empty card pixels',
                  'neutral normal for empty coverage', 'coverage-masked specular',
                  'exclude crown from front-layer translucency'],
          'textures_changed': False, 'niagara_changed': False, 'river_changed': False,
          'extra_texture_samples': 0, 'extra_particles': 0,
          'runtime_tested': False, 'visual_tested': False}
(root / 'SourceAssets/RiverSplashNatural20260924/CardFix/delivery.json').write_text(
    json.dumps(record, indent=2), encoding='utf-8')
u.log('RIVER_CARD_FIX_SAVED ' + json.dumps(record))
