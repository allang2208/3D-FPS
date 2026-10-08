import json
from pathlib import Path
P=Path(__file__).resolve().parent
recipe_path=P.parent/'surface_recipe.json'
recipe=json.loads(recipe_path.read_text())
recipe['texture_residency']={'never_stream':True,'lod_bias':0,'color_group':'Weapon','normal_group':'WeaponNormalMap','scope':'Four blade maps only'}
recipe_path.write_text(json.dumps(recipe,indent=2))
residency=json.loads((P/'residency_repair.json').read_text())
result={'symptom':'Blade surface engraving and normal detail appear missing',
    'asset_binding':'Runtime diagnosis confirmed V3 blade and material, with no material override',
    'source_uv':'Blender and FBX UVs match; imported UE UV0 spans the intended blade atlas',
    'gpu_reproduction':{'before':'Four textures resident at 16 x 64; normal appears flat',
                        'after':'Four textures resident at 1024 x 4096; engraving and normals visible'},
    'fix':'Weapon texture groups, zero LOD bias and NeverStream on the four blade textures; no global streaming change',
    'saved_assets':residency['saved'],
    'material_shader_errors':json.loads((P/'after_sampling_report.json').read_text())['shader_errors'],
    'geometry_changed':False,'guard_changed':False,'game_started_for_testing':False,
    'evidence':['diagnosis_before.json','author_uv.json','blade_imported_uv.json','residency_repair.json','after_graph_color.png','after_graph_normal.png']}
(P/'result.json').write_text(json.dumps(result,indent=2))
print('BLADE_TEXTURE_REPAIR_RECORDED')
