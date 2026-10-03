import json
from pathlib import Path
import unreal as u
p=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/MembraneStabilityV31')
m=u.load_asset('/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18')
rows=[]
for c in m.get_editor_property('mesh_clothing_assets'):
    for k,v in c.get_editor_property('cloth_configs').items():
        row=dict(key=str(k),object=v.get_path_name(),native_class=v.get_class().get_path_name(),python_type=str(type(v)),properties={})
        for name in ('AnimDriveStiffness','AnimDriveDamping','DampingCoefficient','LocalDampingCoefficient','LinearVelocityScale','AngularVelocityScale','IterationCount','SubdivisionCount'):
            try:row['properties'][name]=str(v.get_editor_property(name))
            except Exception as e:row['properties'][name]=str(e)
        rows.append(row)
(p/'active_config_types_v31.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows))
