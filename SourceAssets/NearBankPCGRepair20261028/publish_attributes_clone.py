from pathlib import Path
import runpy,json,hashlib,unreal as u
R=Path(__file__).resolve().parent;MAP='/Game/GameMaps/L_CyberpunkApartment'
runpy.run_path(str(R/'attach_native_attributes.py'),run_name='__main__')
runpy.run_path(str(R/'build_publish_assets.py'),run_name='__main__')
w=u.EditorLoadingAndSavingUtils.load_map(MAP)
result=runpy.run_path(str(R/'install_level.py'))['apply_upgrade'](w)
if not u.EditorLoadingAndSavingUtils.save_map(w,MAP):raise RuntimeError('Cannot save publication copy')
root=R/'PublicationHost/Content';files=[]
for p in sorted((root/'NativeNearBank20261028/Blocks').glob('*.uasset')):
    files.append(dict(relative=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
p=root/'GameMaps/L_CyberpunkApartment.umap';files.append(dict(relative=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(R/'attribute_payload.json').write_text(json.dumps(dict(stage='isolated_payload_saved',files=files,instances=result['instances']),indent=2),encoding='utf8')
print('NATIVE_ATTRIBUTE_PAYLOAD_SAVED',len(files),flush=True)
