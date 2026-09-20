import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parents[1]; report={}
P='/Game/Weapons/AKMIntegration/SovietFab'
for variant,family in [('base','ReloadPolish'),('angled','GripErgonomic'),('vertical','GripVRENatural'),('prism','GripVREExtensions'),('canted','GripVREExtensions')]:
 for clip in ['drum_reload','drum_reload_empty']:
  name='A_AKM_'+('' if variant=='base' else variant+'_')+clip
  path=P+'/'+family+'/'+variant+'/'+name
  a=u.load_asset(path)
  if not a: raise RuntimeError(path)
  source=a.get_editor_property('asset_import_data').extract_filenames()
  report[variant+'/'+clip]={'asset':path,'source':list(source),'duration':a.get_play_length(),'skeleton':a.get_editor_property('skeleton').get_path_name(),'compression':a.get_editor_property('bone_compression_settings').get_path_name()}
(O/'source_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
