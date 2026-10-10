"""Save the V29 distal model, retained V25 clothing and matched soft corpse."""
from pathlib import Path
import json
import unreal as u

BC_GARMENT_REVISION='TentacleReachV29'
BC_GARMENT_VERSION='V29'
BC_GARMENT_SOURCE='/Game/Monsters/BoundCongregate/GarmentDrapeV25/SK_BoundCongregate_GarmentDrapeV25'
BC_GARMENT_PRESERVED='accepted CombatV28 flurry, V28 bite, V25 garments, skeleton reference transforms, damage and capture rules'
BC_GARMENT_COLLISION_REVISION='unchanged V25 interior garment contacts and skin carriers'
BC_GARMENT_MATERIAL_REVISION='retained V25 Witch Fabric09 and original flesh materials'
script=Path('D:/FPS3D/FPSGAME/Tools/BoundCongregate/import_garment_drape_v18.py')
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),globals())
if STAGE!='prepare':
    # These are absolute values; resuming the import cannot multiply range.
    values={'tentacle_range':3000.,'tentacle_recover_seconds':.72,
            'aggro_radius':max(3000.,float(cdo.get_editor_property('aggro_radius')))}
    report['before_tuning']={k:float(cdo.get_editor_property(k)) for k in values}
    report['preserved_flurry']=cdo.get_editor_property('flurry_clip').get_path_name()
    report['preserved_bite']=cdo.get_editor_property('bite_clip').get_path_name()
    report['saved']=False;record()
    for key,value in values.items():cdo.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(saved=True,tuning=values,maximum_range_metres=30.,
        strike_seconds='existing 0.09 close snap to 0.18 at 30 metres',gameplay_tested=False)
    record()
    print('BOUND_CONGREGATE_TENTACLE_REACH_V29_SAVED '+json.dumps(values),flush=True)
