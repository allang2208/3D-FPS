import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
report=[]
for f in ['material_report.json','dirty_metal_report.json']:
 data=json.loads((root/f).read_text());mi=u.EditorAssetLibrary.load_asset(data['material']);mat=mi.get_editor_property('parent')
 overrides=mi.get_editor_property('base_property_overrides')
 row={'path':mi.get_path_name(),'parent_two_sided':mat.get_editor_property('two_sided'),'parent_skeletal':mat.get_editor_property('used_with_skeletal_mesh'),'before_override':str(overrides),'textures':[t.get_path_name() for t in u.MaterialEditingLibrary.get_used_textures(mat)]}
 overrides.set_editor_property('override_two_sided',True);overrides.set_editor_property('two_sided',True);mi.set_editor_property('base_property_overrides',overrides)
 u.MaterialEditingLibrary.update_material_instance(mi)
 assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
 assert row['parent_two_sided'] and row['parent_skeletal']
 row['after_override']=str(mi.get_editor_property('base_property_overrides'));report.append(row)
(root/'surfaces_verified.json').write_text(json.dumps(report,indent=2))
u.log('CHEST_SURFACES_VERIFIED '+str(len(report)))
