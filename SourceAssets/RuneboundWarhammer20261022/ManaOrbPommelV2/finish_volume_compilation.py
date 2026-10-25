"""Finish GPU compilation for the material already saved by the repair stage."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
path='/Game/Weapons/RuneboundWarhammer20261022/ManaOrbPommelV2/M_RuneboundManaOrb_VolumeV2'
material=u.load_asset(path)
if not material:raise RuntimeError('Missing repaired volume material')
# GetStatistics submits the resource's missing jobs and calls FinishCompilation.
# It does not launch gameplay, a preview capture, or a material test scene.
stats=u.MaterialEditingLibrary.get_statistics(material)
receipt=json.loads((P/'pixel_material_repair_receipt.json').read_text('utf-8'))
receipt['gpu_compilation']={
    'vertex_instructions':stats.num_vertex_shader_instructions,
    'pixel_instructions':stats.num_pixel_shader_instructions,
    'completed':stats.num_pixel_shader_instructions>0,
    'platform':'current editor RHI (PCD3D_SM6)',
}
(P/'pixel_material_repair_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if stats.num_pixel_shader_instructions<=0:raise RuntimeError('GPU compilation has no pixel shader; preserve failure for repair')
# The repair stage already saved the graph. Compilation populates the shader
# cache and does not edit the asset; no second package save is necessary.
print('MANA_ORB_GPU_SHADER_COMPILED '+json.dumps(receipt['gpu_compilation']))
