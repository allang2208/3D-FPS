"""Read serialized cloth settings without modifying or saving assets."""
from pathlib import Path
import json
import unreal as u

u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
mesh=u.load_asset('/Game/Monsters/BoundCongregate/FullWhipV10/SK_BoundCongregate_FullWhipV10')
clothes=mesh.get_editor_property('mesh_clothing_assets')
report={'mesh':mesh.get_path_name(),'cloth':[]}
for cloth in clothes:
    config=cloth.get_editor_property('cloth_configs')
    info={'name':cloth.get_name(),'configs':{str(k):v.get_path_name() for k,v in config.items()}}
    for v in config.values():
        if v.get_class().get_name()=='ChaosClothConfig':
            info.update(ccd=v.get_editor_property('bUseCCD'),self_spheres=v.get_editor_property('bUseSelfCollisionSpheres'))
    report['cloth'].append(info)
dest=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/ClothPerfV11/serialized.json')
dest.write_text(json.dumps(report,indent=2),encoding='utf8')
print('BC_SERIALIZED_CLOTH',json.dumps(report),flush=True)
