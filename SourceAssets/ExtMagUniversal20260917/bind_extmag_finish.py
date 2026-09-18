"""Bind each extended magazine to its own rifle's receiver finish.

weapon-finish.md: every accessory matches its host rifle's current coating and
"a model may be reused across M4/AKM/QBZ191 but the metalwork takes that
rifle's material - M4's material must not be handed to the AKM, and the set must
not be tinted one uniform grey". The most faithful source for a magazine is the
rifle's own magazine material slot, so each new mesh is bound slot-for-slot from
its host's skeletal mesh.

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json

JOBS = {
    'SM_ExtMag_QBZ40': ('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny', 'M_QBZ191_Wear_Magazine'),
    'SM_ExtMag_M440': ('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416', 'Magazine_Light_001'),
    'SM_ExtMag_AKM40': ('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative', 'M_AKM_Soviet_Magazine'),
}
D = '/Game/Weapons/ExtMagUniversal20260917'
report = {}

for name, (host_path, slot_name) in JOBS.items():
    host = u.load_asset(host_path)
    if not host:
        report[name] = 'HOST MISSING ' + host_path
        continue
    host_map = {str(m.material_slot_name): m.material_interface
                for m in host.get_editor_property('materials')}
    if slot_name not in host_map or not host_map[slot_name]:
        report[name] = 'slot %s not found on host (have %s)' % (slot_name, sorted(host_map))
        continue
    source = host_map[slot_name]

    mesh = u.load_asset(f'{D}/{name}')
    if not mesh:
        report[name] = 'MESH MISSING'
        continue
    slots = mesh.get_editor_property('static_materials')
    for i, slot in enumerate(slots):
        slot.material_interface = source          # every slot of the source part
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    u.EditorAssetLibrary.save_loaded_asset(mesh, False)
    report[name] = {'bound_to': source.get_path_name(),
                    'slots': [str(s.material_slot_name) for s in slots]}

u.log('EXTMAG_FINISH ' + json.dumps(report))
