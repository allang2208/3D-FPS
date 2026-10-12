import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'inputs.json').read_text());L=u.MaterialEditingLibrary;R={}
for key,row in C['assets'].items():
 if key=='super90':continue
 m=u.load_asset(row['slots'][0]['material']);base=m.get_base_material();r={'base':base.get_path_name(),'textures':[]};R[key]=r
 for n in L.get_material_expressions(base):
  try:
   t=n.get_editor_property('texture')
   if t:r['textures'].append({'node':n.get_name(),'class':n.get_class().get_name(),'path':t.get_path_name(),'sampler':str(n.get_editor_property('sampler_type')),'sources':list(t.get_editor_property('asset_import_data').extract_filenames())})
  except Exception:pass
 for label in ['NORMAL','AMBIENT_OCCLUSION']:
  n=L.get_material_property_input_node(base,getattr(u.MaterialProperty,'MP_'+label));r[label]=n.get_name() if n else None
(O/'material_sources.json').write_text(json.dumps(R,indent=2));print('REARGRIP_MATERIAL_SOURCES',R)
