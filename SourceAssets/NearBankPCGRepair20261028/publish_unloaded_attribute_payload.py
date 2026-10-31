"""Publish only closed, unmodified packages while preserving the editor session."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,hashlib,shutil,os
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];CONTENT=(PROJECT/'Content').resolve()
payload=json.loads((R/'attribute_payload.json').read_text());host=R/'PublicationHost'
if payload['stage']!='isolated_payload_saved':raise RuntimeError('Payload is superseded; use the final native authoring batch')
prepared=host.stat().st_ctime
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
dirty.update(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
rows=[]
for row in payload['files']:
    relative=Path(row['relative']);dst=(CONTENT/relative).resolve();src=(host/'Content'/relative).resolve()
    if not dst.is_relative_to(CONTENT) or not src.is_relative_to((host/'Content').resolve()):raise RuntimeError('Invalid package boundary')
    if not (relative.as_posix().startswith('NativeNearBank20261028/Blocks/') or relative.as_posix()=='GameMaps/L_CyberpunkApartment.umap'):raise RuntimeError('Outside publication scope')
    package='/Game/'+relative.with_suffix('').as_posix();objpath=package+'.'+relative.stem
    if package in dirty or u.find_object(None,package) or u.find_object(None,objpath):raise RuntimeError('Preserve loaded or dirty package '+package)
    if dst.stat().st_mtime>prepared:raise RuntimeError('Package changed since publication copy '+package)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Payload file changed '+str(src))
    rows.append((src,dst,relative))
backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/'AttributePublication'
for src,dst,relative in rows:
    b=backup/relative;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,b)
    tmp=dst.with_name(dst.name+'.native-pcg-stage');shutil.copy2(src,tmp);os.replace(tmp,dst)
u.AssetRegistryHelpers.get_asset_registry().scan_modified_asset_files([str(d) for _,d,_ in rows])
d=json.loads((R/'installed.json').read_text());d.update(native_material_attributes_preserved=True,attribute_payload_files=len(rows),active_editor_preserved=True,saved_at=datetime.now().astimezone().isoformat(),attribute_backup=str(backup));(R/'installed.json').write_text(json.dumps(d,indent=2),encoding='utf8')
print('NATIVE_ATTRIBUTES_PUBLISHED_TO_UNLOADED_PACKAGES',len(rows),flush=True)
