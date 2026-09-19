"""Import the generated GLB into an editable Blender source. No rendering or validation."""
import bpy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'seed_91379'
SOURCE = OUT / 'textured_master_00001_.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
scene = bpy.context.scene
scene['asset_status'] = 'Generated candidate; user selection and game integration pending'
scene['reference'] = str(ROOT / 'reference_original.png')
scene['generated_reference'] = str(ROOT / 'three_views.png')
scene['generation_seed'] = 91379
scene['generation_model'] = 'microsoft/TRELLIS.2-4B'
scene['source_geometry_policy'] = 'Original imported topology, UVs, textures, normals and transforms retained'
scene['units_policy'] = 'Generator coordinates retained; no physical size or mounting transform assigned'
scene['runtime_test_status'] = 'Not tested; user tests'
texture_dir = OUT / 'Textures'
texture_dir.mkdir(exist_ok=True)
textures = []
for index, image in enumerate(bpy.data.images):
    if image.source not in {'FILE', 'GENERATED'}:
        continue
    safe_name = ''.join(c if c.isalnum() or c in '_-' else '_' for c in image.name)
    target = texture_dir / f'{index:02d}_{safe_name}.png'
    # GLB images can be packed without a decoded pixel buffer in background
    # Blender. Preserve those original PNG bytes rather than skipping them.
    if image.packed_file:
        target.write_bytes(image.packed_file.data)
    else:
        if not image.has_data:
            image.reload()
        image.filepath_raw = str(target)
        image.file_format = 'PNG'
        image.save()
    textures.append({'file':str(target.relative_to(OUT)), 'image_name':image.name, 'color_space':image.colorspace_settings.name, 'size':list(image.size)})
bpy.ops.file.pack_all()
blend = OUT / 'SkeletonStock_5080_Candidate_Editable.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
receipt = {
    'operation':'GLB import, original texture extraction, and packed editable source save',
    'source':SOURCE.name,
    'blend':blend.name,
    'blender_version':bpy.app.version_string,
    'textures':textures,
    'geometry_edits':False,
    'rendered':False,
    'tested':False,
    'ue_imported':False,
    'runtime_reference':None,
}
(OUT / 'editable_source_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('EDITABLE_SOURCE_SAVED ' + str(blend), flush=True)
