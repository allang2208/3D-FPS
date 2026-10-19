"""Save the three current Saiga profiles, replacing only empty-reload return tracks."""
import unreal as u,json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KReloadReturn20261018';E=u.EditorAssetLibrary
ROOT='/Game/Weapons/Saiga12K/InspectClearance20261018/Profiles'
report={'complete':False,'saved':[],'runtime_tested':False,'scope':'Only vertical/canted/prism empty reload and empty drum return; existing inspect and all other clips retained'}
def serialize(c):
 base=c.get_editor_property('base');retained=c.get_editor_property('retained')
 return {'base':base.get_path_name(),'duration':c.get_editor_property('duration'),'retained':retained.get_path_name() if retained else None,'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]}
for family in ('vertical','canted','prism'):
 path=ROOT+'/DA_'+family;asset=u.load_asset(path)
 if not asset:raise RuntimeError('Current Saiga profile missing '+path)
 current={'family':family,'clips':[serialize(c) for c in asset.get_editor_property('clips')]}
 (O/'Before'/('DA_'+family+'.json')).write_text(json.dumps(current),encoding='utf8')
 source=P/'Content'/Path(path.removeprefix('/Game/')+'.uasset');backup=O/'Before'/'Content'/Path(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(source,backup)
 authored=json.loads((O/'Profiles'/('DA_'+family+'.json')).read_text())
 changes={c['base']:c for c in authored['clips'] if c['base'].rsplit('.',1)[-1].endswith('_reload_empty')}
 if len(changes)!=2:raise RuntimeError('Expected standard and drum empty-reload layers only')
 edited=[]
 for c in current['clips']:
  if c['base'] in changes:
   c.update(changes[c['base']]);edited.append(c['base'])
 if len(edited)!=2:raise RuntimeError('Current reload routing changed')
 shared={'family':family,'clips':[c for c in current['clips'] if not c.get('retained')]}
 if not asset.set_shared_clips_from_json(json.dumps(shared)):raise RuntimeError('Return layer import failed '+family)
 for c in current['clips']:
  if c.get('retained'):asset.keep_clip(u.load_asset(c['base']),u.load_asset(c['retained']))
 E.set_metadata_tag(asset,'Saiga12KEmptyReturn20261018','Native wrist/forearm-helper and finger return, source 380..440 at 120Hz; thumb closure follows fingers; mechanical contacts retained')
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
 report['saved'].append({'family':family,'asset':path,'edited_clips':edited,'total_clips':len(current['clips'])})
 (O/'Receipts/saved-profiles.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('SAIGA_EMPTY_RETURN_SAVED',family,flush=True)
report['complete']=True;(O/'Receipts/saved-profiles.json').write_text(json.dumps(report,indent=2),encoding='utf8')
