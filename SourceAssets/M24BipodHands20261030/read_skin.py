from pathlib import Path
code=(Path(__file__).parent.parent/'M24LeftElbowReview20261028/read_geometry.py').read_text()
exec(compile(code.replace("(O/'geometry.json')","(O/'skin_geometry.json')"),'read_current_skin','exec'))
import shutil
backup=O/'AnatomyBefore/Assets';backup.mkdir(parents=True,exist_ok=True)
shutil.copy2(file,backup/file.name)
manifest=json.loads((O/'input_manifest.json').read_text())
for p in manifest:
    asset=Path(p);shutil.copy2(asset,backup/asset.name)
    manifest[p]=hashlib.sha256(asset.read_bytes()).hexdigest()
(O/'review_input_manifest.json').write_text(json.dumps(manifest,indent=2))
print('CURRENT_M24_MORPHS',len(mesh.get_editor_property('morph_targets')),flush=True)
