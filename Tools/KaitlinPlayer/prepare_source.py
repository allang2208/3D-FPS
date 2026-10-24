"""Stage the user-downloaded Kaitlin preset in an isolated UE authoring host."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'SourceAssets/KaitlinPlayer20261023'
SOURCE = Path('D:/FPS3D/VaultCache/FabLibrary/MetaHuman_-_Kaitlin_female_character_editable-ebbc58e2/metahuman/UE_5.8/mhc_kaitlin.mhpkg')
HOST = WORK / 'AuthorHost'

WORK.mkdir(parents=True, exist_ok=True)
HOST.mkdir(exist_ok=True)
project = HOST / 'KaitlinAuthor.uproject'
if not project.exists():
    project.write_text(json.dumps({
        'FileVersion': 3, 'EngineAssociation': '5.8',
        'Plugins': [{'Name': name, 'Enabled': True} for name in (
            'MetaHumanCharacter', 'PythonScriptPlugin', 'EditorScriptingUtilities', 'GeometryScripting')]
    }, indent=2), encoding='utf-8')
config = HOST / 'Config/DefaultEngine.ini'
config.parent.mkdir(exist_ok=True)
if not config.exists():
    config.write_text('[/Script/Engine.RendererSettings]\nr.SkinCache.CompileShaders=True\nr.VirtualTextures=True\n', encoding='utf-8')
with zipfile.ZipFile(SOURCE) as archive:
    manifest = json.loads(archive.read('Manifest.json'))
    target = HOST / 'Content/EditableCharacters/Kaitlin/MHC_Kaitlin.uasset'
    target.parent.mkdir(parents=True, exist_ok=True)
    # Never replace the author's staged asset after rigging or assembly updates.
    if not target.exists():
        target.write_bytes(archive.read('MHC_Kaitlin.uasset'))
    (WORK / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
receipt = {
    'selected_by_user': 'Kaitlin',
    'listing': 'https://www.fab.com/listings/ebbc58e2-f745-482c-bb9a-9d73b6379d93',
    'download': str(SOURCE), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'source_type': manifest['assetType'], 'source_files': ['MHC_Kaitlin.uasset'],
    'authoring_host': str(project), 'staged_asset': str(target),
    'runtime_published': False,
    'status': 'editable_preset_staged_assembly_pending',
    'redistribution': 'Local authorized integration only; no binary publication.',
}
(WORK / 'source_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False))
