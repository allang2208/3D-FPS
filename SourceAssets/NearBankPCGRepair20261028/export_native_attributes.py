"""Carry the native PCG instance material attributes into the baked district."""
from pathlib import Path
import json,unreal as u
R=Path(__file__).resolve().parent
w=u.EditorLoadingAndSavingUtils.load_map('/Game/NativeNearBank20261028/AuthoringState')
rows={};components=0
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        n=c.get_editor_property('num_custom_data_floats')
        if n:
            rows[a.get_actor_label()+'|'+c.get_name()]=dict(stride=n,data=list(c.get_editor_property('per_instance_sm_custom_data')))
        components+=1
(R/'native_instance_attributes.json').write_text(json.dumps(dict(stage='attributes_exported',source_components=components,attributes=rows),separators=(',',':')),encoding='utf8')
print('NATIVE_MATERIAL_ATTRIBUTES_EXPORTED',components,len(rows),flush=True)
