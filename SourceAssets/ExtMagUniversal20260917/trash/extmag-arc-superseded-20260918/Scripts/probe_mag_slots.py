"""Read the magazine slots of the three rifles and of the extended magazines.

Read-only: reports material slot names, the material asset each slot uses, and
mesh sizes, so the extended magazine can be bound to the same material the
rifle's own factory magazine uses in that rifle's mesh.

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json

MESHES = [
    '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
    '/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny',
    '/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_M440',
    '/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_AKM40',
    '/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_QBZ40',
]

report = {}
for path in MESHES:
    asset = u.load_asset(path)
    if not asset:
        report[path] = 'MISSING'
        continue
    slots = []
    if isinstance(asset, u.StaticMesh):
        source = asset.get_editor_property('static_materials')
    else:
        source = asset.get_editor_property('materials')
    for slot in source:
        mat = slot.material_interface
        slots.append({
            'slot': str(slot.material_slot_name),
            'material': mat.get_path_name() if mat else None,
            'class': mat.get_class().get_name() if mat else None,
        })
    info = {'slots': slots}
    if isinstance(asset, u.StaticMesh):
        info['lod0_vertices'] = asset.get_num_vertices(0)
        info['lod0_triangles'] = asset.get_num_triangles(0)
        bounds = asset.get_bounds()
        info['bounds_cm'] = [round(bounds.box_extent.x * 2, 2), round(bounds.box_extent.y * 2, 2),
                             round(bounds.box_extent.z * 2, 2)]
    report[path] = info

u.log('MAG_SLOTS ' + json.dumps(report, indent=1))
with open(r'D:\FPS3D\FPSGAME\SourceAssets\ExtMagUniversal20260917\Reference\mag_slots.json',
          'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=1, ensure_ascii=False)
