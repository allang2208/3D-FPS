import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=P.resolve():raise RuntimeError('Wrong project')
donor=u.load_asset('/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_holographic')
metal=next(s.material_interface for s in donor.static_materials if str(s.material_slot_name)=='M16_InterfaceMetal')
mesh=u.load_asset('/Game/Weapons/CommonHK41620260930/Meshes/SM_M16_eoth_holographic')
slots=list(mesh.static_materials)
for i,slot in enumerate(slots):
    if str(slot.material_slot_name)=='Universal_InterfaceSteel':slot.material_interface=metal;slots[i]=slot
mesh.set_editor_property('static_materials',slots)
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('M16 material save failed')
report=json.loads((O/'import_receipt.json').read_text());report['meshes']['M16/eoth_holographic']['material_slots']=[s.material_interface.get_path_name() for s in slots]
(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('EOTH_M16_HOST_FINISH_SAVED')
