"""Save slope-aware copies of the accepted white gather and slam FX; no preview.

Owns only /Game/Skills/IceWall/TerrainV1. Thirty-two bounded ground planes are
uploaded once per wall/impact, without adding per-column Niagara components.
"""
import json
import re
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref, put, save
from build_fireball_flames import FLOAT
from build_fireball_flight import user_parameter, expression

DEST = '/Game/Skills/IceWall/TerrainV1'
SOURCES = {
    'NS_IceWallColdMist': '/Game/Skills/IceWall/GatherV2/NS_IceWallColdMist',
    'NS_IceWallLanding': '/Game/Skills/IceWall/SlamV3/NS_IceWallLanding',
}


def ground(x, y):
    index = f'clamp(floor((({y})-User.WallCenter+User.WallSize.y*.5)/max(1,User.WallSize.y)*User.GroundCount),0,max(0,User.GroundCount-1))'
    plane = 'User.Ground31'
    for i in reversed(range(31)):
        plane = f'(({index})<{i+.5}?User.Ground{i:02d}:{plane})'
    return f'(({plane}).y+({plane}).z*({x})+({plane}).w*(({y})-({plane}).x))'


def motion_module(system, emitter, script):
    stack = API.call_method('GetScriptStackTopology', (ref(system, emitter, script),))
    for module in stack.get_editor_property('modules'):
        names = {str(v.get_editor_property('name')) for v in module.get_editor_property('inputs')}
        if {'Particles.Position', 'Particles.SpriteSize'}.issubset(names):
            return str(module.get_editor_property('module_name'))
    raise RuntimeError('Missing authored position/size module: ' + emitter + '/' + script)


def adapt(system, source, emitter, script, x, y, wall_only):
    module = motion_module(system, emitter, script)
    source_module = motion_module(source, emitter, script)
    raw = u.RainAssetEditor.read_input(source, emitter, script, source_module, 'Particles.Position')
    match = re.fullmatch(r'\(HlslExpression="(.*)"\)', raw, re.DOTALL)
    if not match:
        raise RuntimeError('Unsupported position input export: ' + raw)
    old = match.group(1)
    height = ground(x, y)
    if wall_only:
        value = f'({old})+User.WallPhase*(User.Side*User.WallCenter+User.Up*{height})'
    else:
        value = f'({old})+float3(0,User.WallCenter,{height})'
    expression(system, emitter, script, module, 'Particles.Position', value)


def main():
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for name in SOURCES:
        if DEST + '/' + name in dirty:
            raise RuntimeError('Preserve unsaved terrain FX: ' + name)
    u.EditorAssetLibrary.make_directory(DEST)
    saved = []
    for name, path in SOURCES.items():
        source = u.load_asset(path)
        target = DEST + '/' + name
        system = (u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target)
                  else u.EditorAssetLibrary.duplicate_asset(path, target))
        if not source or not system:
            raise RuntimeError('Missing accepted wall FX: ' + path)
        for param in ['GroundCount', 'WallCenter']:
            user_parameter(system, param, FLOAT)
        for i in range(32):
            user_parameter(system, f'Ground{i:02d}', '/Script/CoreUObject.Vector4f')
        if name == 'NS_IceWallColdMist':
            y = '(frac(float(Particles.UniqueID)*.754877666)*2-1)*max(0,User.WallSize.y*.5-6)+User.WallCenter'
            x = '(frac(float(Particles.UniqueID)*.5)<.5?-1:1)*(User.WallSize.x*.5+4)'
            adapt(system, source, 'RocketTrail', 'ParticleSpawnScript', x, y, True)
        else:
            for emitter, mist in [('GroundDust', False), ('GroundColdMist', True)]:
                count = 'floor(User.' + ('MistCount' if mist else 'DustCount') + '*(1-saturate(User.DetailReduction))+.5)'
                y = f'((floor(float(Particles.UniqueID)*.5)+.5)/max(1,ceil(({count})*.5))-.5)*User.WallSize.y+User.WallCenter'
                seed = 'frac(float(Particles.UniqueID)*.618033989)'
                travel = f'(72+12*{seed})*(1-exp(-Particles.Age*8))' if mist else f'(190+45*{seed})*(1-exp(-Particles.Age*18))'
                x = f'(frac(float(Particles.UniqueID)*.5)<.5?-1:1)*(User.WallSize.x*.5+8+{travel})'
                for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
                    adapt(system, source, emitter, script, x, y, False)
        save(system)
        saved.append(system.get_path_name())
    receipt = {'saved_assets': saved, 'sources_read_only': list(SOURCES.values()),
               'ground_profile_slots': 32, 'max_terrain_sections': 31,
               'systems_per_wall': 1, 'systems_per_impact': 1,
               'existing_particle_caps_preserved': True, 'gameplay_tested': False}
    out = ROOT / 'Saved/IceWallTerrain20261001'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ICE_WALL_TERRAIN_FX_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    main()
