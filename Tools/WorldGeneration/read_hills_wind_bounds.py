"""Read-only follow-up to a failed runtime foliage bounds assertion."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/Saved/VegetationStreamingCheck/wind-bounds-20261114.json')
assets = u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
rows = []
def xyz(v):
    return [v.x, v.y, v.z]
for role in ('trees', 'forest_saplings', 'forest_shrubs', 'forest_ferns'):
    for ref in assets.get_editor_property(role):
        mesh = u.load_asset(ref.get_path_name())
        rest, padded = mesh.get_imported_bounds(), mesh.get_bounds()
        rows.append(dict(role=role, path=mesh.get_path_name(), rest=xyz(rest.box_extent),
                         padded=xyz(padded.box_extent),
                         positive=xyz(mesh.get_editor_property('positive_bounds_extension')),
                         negative=xyz(mesh.get_editor_property('negative_bounds_extension'))))
        out.write_text(json.dumps(rows, indent=2), encoding='utf-8')
u.log('HILLS_WIND_BOUNDS_READ meshes=%d' % len(rows))
