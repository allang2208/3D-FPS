"""Read active charcoal sources and native bare arms for the reported spikes."""
import sys
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'Tools/ModularOutfit'))
import garment_ue as g

config = g.read(P / 'Content/ColdSteelData/modular_outfits.json')
recipe = config['items']['ue_field_sweater_charcoal']
sources = {k: v for k, v in recipe['rig_meshes'].items() if k not in ('Body', 'Traversal')}
before = R / 'before.json'
if before.exists():
    if g.read(before)['sources'] != sources:
        raise RuntimeError('Active charcoal sources changed')
else:
    g.write(before, dict(sources=sources, recipe=recipe))

for profile, source in sources.items():
    folder = R / 'Before' / profile
    if (folder / 'paths.json').exists():
        continue
    native, row = next((k, v) for k, v in config['profiles'].items() if v['rig_profile'] == profile)
    skin_path = row['native_bare_skin']
    shirt = u.load_asset(source)
    _, data = g.source_snapshot(shirt)
    skin_dm, skin = g.source_snapshot(u.load_asset(skin_path))
    _, bones = g.B.get_all_bones_info(skin_dm)
    skin['bones'] = {str(b.name): dict(index=b.index, parent=b.parent_index,
        position=list(b.world_transform.translation.to_tuple()),
        axes=[list((b.world_transform.transform_location(v)-b.world_transform.translation).to_tuple()) for v in
              [u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1)]]) for b in bones}
    g.write(folder / 'shirt.json', data)
    g.write(folder / 'skin.json', skin)
    g.write(folder / 'paths.json', dict(shirt=source, native=native, skin=skin_path,
        source_sha256=g.digest(g.asset_file(source)), skin_sha256=g.digest(g.asset_file(skin_path))))
    print('CHARCOAL_CAPTURED', profile, len(data['triangles']), len(skin['triangles']), flush=True)
print('CHARCOAL_CAPTURE_DONE', len(sources), flush=True)
