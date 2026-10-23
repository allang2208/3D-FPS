"""Read the affected bag material and asset revisions for this repair."""
import json
from pathlib import Path
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BackpackHarnessRebuild20261020')
rows = []
for row in json.loads((R/'manifest.json').read_text())['variants']:
    asset = u.load_asset(row['asset'])
    mat = asset.materials[0].material_interface
    chain = []
    while mat:
        entry = {'path': mat.get_path_name(), 'class': mat.get_class().get_name()}
        if isinstance(mat, u.Material):
            entry.update(two_sided=mat.get_editor_property('two_sided'),
                         blend_mode=str(mat.get_editor_property('blend_mode')))
            chain.append(entry)
            break
        entry['overrides'] = str(mat.get_editor_property('base_property_overrides'))
        chain.append(entry)
        mat = mat.get_editor_property('parent')
    rows.append({'profile': row['profile'], 'asset': row['asset'],
                 'revision': u.EditorAssetLibrary.get_metadata_tag(asset, 'BackpackHarnessRevision'),
                 'source_sha256': u.EditorAssetLibrary.get_metadata_tag(asset, 'BackpackHarnessSourceSHA256'),
                 'material_chain': chain})
(R/'ShellRepair20261022/material_inputs.json').write_text(json.dumps(rows, indent=2))
print('BAG_MATERIAL_INPUTS_SAVED', flush=True)
