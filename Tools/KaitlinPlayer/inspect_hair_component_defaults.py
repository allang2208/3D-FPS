"""Read the native long-hair component's transform and authored LOD map."""
import json
from pathlib import Path
import unreal as u

W=Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinHairLOD20261024')
bp=u.load_asset('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/BP_Kaitlin.BP_Kaitlin')
sub=u.get_engine_subsystem(u.SubobjectDataSubsystem); lib=u.SubobjectDataBlueprintFunctionLibrary
rows=[]
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(h),bp)
    if isinstance(obj,u.GroomComponent) and obj.get_editor_property('groom_asset'):
        rows.append({'name':obj.get_name(),'relative':obj.get_relative_transform().export_text(),
                     'simulation':obj.get_editor_property('simulation_settings').export_text()})
    elif isinstance(obj,u.LODSyncComponent):
        rows.append({'name':obj.get_name(),'num_lods':obj.get_editor_property('num_lods'),
                     'mapping':{str(k):v.export_text() for k,v in obj.get_editor_property('custom_lod_mapping').items()}})
(W/'native_defaults.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
