"""Publish matched material slots and dry/wet pairs on HK416 attachments."""
import unreal as u,json,re,importlib.util
from pathlib import Path
from runpy import run_path
O=Path(__file__).parent;C=O.parent/'HK416CommonAttachments20260930'
apply_current_bindings=run_path(str(O.parent/'WeaponSurface20260930/HK416/current_bindings.py'))['apply_current_bindings']
spec=importlib.util.spec_from_file_location('hk416_surfaces',C/'surface_materials.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(O.parents[1]/'Content').resolve():raise RuntimeError('Wrong project content')
finish=f.SurfaceLibrary();models=json.loads((C/'models.json').read_text());receipt={'meshes':{},'materials':{},'tested':False}
def record():
 receipt['materials']=finish.records;(O/'surface_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
canonical=lambda s:re.sub(r'[._]\d{3}$','',s)
for key,part in models['parts'].items():
 mesh=f.load(f.D+'/Meshes/'+part['name']);slots=list(mesh.static_materials);bindings={canonical(k):(k,v) for k,v in part['bindings'].items()}
 for i,slot in enumerate(slots):
  binding,path=bindings[canonical(str(slot.material_slot_name))]
  slot.material_interface=finish.material(key,binding,path);slots[i]=slot
 mesh.set_editor_property('static_materials',slots);apply_current_bindings(mesh);f.save(mesh)
 receipt['meshes'][key]=mesh.get_path_name();record();print('HK416_MATCHED_SURFACE_SAVED',key,flush=True)
library=f.load('/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials')
entries=dict(library.get_editor_property('wet_materials'));entries.update(finish.wet);library.set_editor_property('wet_materials',entries);f.save(library)
receipt['wet_library_saved']=True;record();print('HK416_MATCHED_SURFACES_COMPLETE',len(receipt['meshes']),len(finish.records),flush=True)
