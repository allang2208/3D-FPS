"""Finish the four village material permutations before publishing the package group."""
import json
import os
from pathlib import Path
import unreal as u

run=Path(os.environ['VILLAGE_RELIEF_WORK'])
receipt=json.loads((run/'saved.json').read_text())
compiled={}
for name in receipt['materials']:
    material=u.load_asset('/Game/WorldGeneration/TemperateHills/VillageMasonry/Relief/'+name)
    stats=u.MaterialEditingLibrary.get_statistics(material)
    if stats.num_samplers<0 or (not stats.num_pixel_shader_instructions and not stats.num_vertex_shader_instructions):
        raise RuntimeError('No compiled SM6 material for '+name)
    compiled[name]=dict(vertex=stats.num_vertex_shader_instructions,pixel=stats.num_pixel_shader_instructions,samplers=stats.num_samplers)
(run/'sm6.json').write_text(json.dumps(compiled,indent=2))
