"""Publish only the reviewed two native meshes; preserve unrelated assets."""
import sys,hashlib,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;sys.path.insert(0,str(O))
from ue_pipeline import P,E,file_for,backup,apply_patch,readback
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Stop PIE before saving Super90 final surfaces.')
checks=json.loads((O/'geometry_checks.json').read_text());assert checks['passed'] and len(checks['readback'])==2
assert (O/'visual_review.json').exists()
patches=json.loads((O/'patches.json').read_text());dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,patch in patches.items():
 path=patch['path'];assert path not in dirty,'Unsaved Super90 mesh: '+path
 assert hashlib.sha256(file_for(path).read_bytes()).hexdigest()==patch['source_sha256'],'Retain newer Super90 changes: '+path
 backup(path)
receipt={}
for key,patch in patches.items():
 mesh=u.load_asset(patch['path']);assert mesh
 apply_patch(mesh,patch)
 fbx=P/'SourceAssets/BenelliM4Super9020261006/Exports'/('SK_Super90_BareArmsV7.fbx' if key=='arms' else 'SK_Super90_V7.fbx')
 E.set_metadata_tag(mesh,'Super90SourceSHA256',hashlib.sha256(fbx.read_bytes()).hexdigest())
 assert E.save_loaded_asset(mesh,False)
 readback(mesh,key+'_published')
 receipt[key]={'path':patch['path'],'before_sha256':patch['source_sha256'],'saved_sha256':hashlib.sha256(file_for(patch['path']).read_bytes()).hexdigest(),'geometry_patch_vertices':len(patch['positions']),'normal_vertices':len(patch['normals'])}
 (O/'published.json').write_text(json.dumps(receipt,indent=2))
 print('SUPER90_SURFACE_PUBLISHED',key,flush=True)
