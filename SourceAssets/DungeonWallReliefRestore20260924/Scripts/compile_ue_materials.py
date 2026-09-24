"""Compile saved UE material permutations in an offscreen asset commandlet.

No world loading, actor spawning, frame capture or game execution. get_statistics
calls FMaterialResource::FinishCompilation in this engine, unlike NullRHI alone.
"""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
L=u.MaterialEditingLibrary
paths=['/Game/Dungeons/AtmosphereV2/Materials/M_Concrete',
       '/Game/Dungeons/WallDamage20260923/Materials/M_WallMortarProjectedRelief20260924',
       '/Game/Dungeons/WallDamage20260923/Materials/MI_FabExposedBed',
       '/Game/Dungeons/WallDamage20260923/Materials/MI_FabBondingMortar']
report={'scope':'Saved material shader compilation; no scene/visual/performance test','materials':{}}
for path in paths:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing '+path)
    override=L.get_nanite_override_material(mat)
    stats=L.get_statistics(mat)
    row={'parent':mat.get_base_material().get_path_name(),'nanite_override':override.get_path_name() if override else None}
    for key in ('num_pixel_shader_instructions','num_vertex_shader_instructions','num_samplers','num_pixel_texture_samples','num_uv_scalars'):
        row[key]=stats.get_editor_property(key)
    report['materials'][path]=row
    (ROOT/'Receipts/ue-material-build.json').write_text(json.dumps(report,indent=2))
    print('WALL_UE_MATERIAL_BUILD',path,json.dumps(row),flush=True)
