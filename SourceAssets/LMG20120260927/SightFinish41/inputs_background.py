from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'read_pose.py').read_text(encoding='utf-8-sig'),str(O/'read_pose.py'),'exec'),globals())
import unreal as u,json,hashlib
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;P=O.parents[2]
paths=set(json.loads((O.parent/'Material21/bindings.json').read_text())['meshes'])
out={}
for path in sorted(paths):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 out[a.get_path_name()]={'sha256':hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
(O/'finish_targets.json').write_text(json.dumps(out,indent=2))
print('S41_FINISH_INPUTS',len(out),flush=True)
