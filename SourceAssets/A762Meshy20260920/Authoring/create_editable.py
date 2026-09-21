"""Package the original Meshy mesh and material into an editable Blender source.

No render, mesh modification, mechanical split or game integration is performed.
Run: blender --background --python create_editable.py
"""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Meshy/candidate01/downloads/model_urls_glb.glb'
OUTPUT = ROOT / 'A762_Meshy_Candidate01_Editable.blend'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene = bpy.context.scene
scene['asset_identity'] = 'A762 Meshy candidate01'
scene['source'] = str(SOURCE.relative_to(ROOT))
scene['stage'] = 'Generated visual candidate; not rigged, not game-integrated, untested'
scene['scale_note'] = 'Original generator scale; reference screenshots contain no reliable dimensions'
scene['reference_note'] = 'Two user screenshots plus three imagegen reconstruction views; unseen surfaces are inferred'
scene['production_parameters'] = (ROOT / 'meshy_settings.json').read_text(encoding='utf-8')
text = bpy.data.texts.new('A762_README')
text.write((ROOT / 'README.md').read_text(encoding='utf-8'))
for obj in scene.objects:
    if obj.type == 'MESH':
        obj['source_mesh_preserved'] = True
        obj['mechanical_parts_split'] = False
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
print(json.dumps({'editable_saved': str(OUTPUT)}, ensure_ascii=False))
