"""Finish only this material's shader compilation for the requested bug diagnosis."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path='/Game/Dungeons/AtmosphereV2/GateWater/Materials/M_Dungeon_ShallowPuddle'
mat=u.load_asset(path)
if not mat:raise RuntimeError('Puddle material missing')
# UE GetStatistics finishes this material resource's compile jobs before reading.
stats=u.MaterialEditingLibrary.get_statistics(mat)
data={name:stats.get_editor_property(name) for name in ('num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers','num_pixel_texture_samples')}
if data['num_pixel_shader_instructions']<=0 or data['num_samplers']<=0:raise RuntimeError('Puddle shader resource did not produce compiled pixel instructions: '+str(data))
receipt=json.loads((ROOT/'Receipts/puddle-sampler-repair.json').read_text())
receipt['compiled_shader_statistics']=data;receipt['shader_compilation_completed']=True
(ROOT/'Receipts/puddle-sampler-repair.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('PUDDLE_COMPILED_SHADER_READY '+json.dumps(data))
