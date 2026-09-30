"""Patch only belt/link bone tracks in the ten currently used reload assets."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];S=json.loads((O/'source.json').read_text());E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE retained')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def file(p):return P/'Content'/(p.removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(file(p).read_bytes()).hexdigest()
report={'status':'saving_belt_tracks','saved':{},'non_belt_tracks_modified':False,'duration_changed':False,'runtime_tested':False}
for key,spec in S['clips'].items():
 path=spec['path']
 if path in dirty or sha(path)!=spec['sha256']:raise RuntimeError('Concurrent animation retained '+path)
for key,spec in S['clips'].items():
 path=spec['path'];backup=O/'Before'/file(path).relative_to(P/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
 if backup.exists():raise RuntimeError('Existing backup retained '+path)
 shutil.copy2(file(path),backup)
 with gzip.open(O/'Tracks'/(key.split('_')[0]+'_tracks.json.gz'),'rt') as f:tracks=json.load(f)
 a=u.load_asset(path);c=a.get_editor_property('controller');c.open_bracket('BeltFit53 belt and linking tracks only',False)
 try:
  for n,rows in tracks.items():
   assert 'LMG201_Belt_' in n
   if not c.set_bone_track_keys(n,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):
    if not c.add_bone_curve(n,False) or not c.set_bone_track_keys(n,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Cannot update '+n)
 finally:c.close_bracket(False)
 E.set_metadata_tag(a,'201BeltFitRevision','BeltFit53: linked rigid rounds; pouch rim routing; seated receiver run')
 u.AKMAnimationAuditLibrary.finish_animation_compression(a)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+path)
 report['saved'][path]={'before_sha256':spec['sha256'],'sha256':sha(path),'updated_tracks':len(tracks),'backup':str(backup)}
 (O/'animation_delivery.json').write_text(json.dumps(report,indent=2));print('B53_ANIMATION_SAVED',key,flush=True)
report['status']='ten_reload_belt_tracks_saved';(O/'animation_delivery.json').write_text(json.dumps(report,indent=2))
