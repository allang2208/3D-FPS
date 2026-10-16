"""Repair the loaded source mesh's missing material interfaces, never a PIE map."""
from pathlib import Path
import json,unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualLoadRepair20261016')
BASE='/Game/Building/PotionWorkbench20261015/ManualV9/'
mesh=u.load_asset(BASE+'Meshes/SK_BookLeafTemplate')
paper=u.load_asset(BASE+'Materials/M_BookLeafPaper')
edge=u.load_asset(BASE+'Materials/M_BookLeafEdge')
if not mesh or not paper or not edge:raise RuntimeError('Missing manual page dependency')
expected={'M_BookPages':edge,'RecipeLeft':paper,'RecipeRight':paper}
def describe():
    return [dict(slot=str(s.get_editor_property('material_slot_name')),
        material=s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None)
        for s in mesh.get_editor_property('materials')]
report=dict(complete=False,mesh=mesh.get_path_name(),before=describe(),runtime_tested=False,visual_tested=False)
def record():(ROOT/'repair-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
record()
slots=mesh.get_editor_property('materials')
if {str(s.get_editor_property('material_slot_name')) for s in slots}!=set(expected):raise RuntimeError('Unexpected leaf slots')
mesh.modify()
for i,slot in enumerate(slots):
    slot.set_editor_property('material_interface',expected[str(slot.get_editor_property('material_slot_name'))])
    # UE's struct array iteration yields a value copy. Write each value back.
    slots[i]=slot
mesh.set_editor_property('materials',slots)
report['after']=describe();record()
for slot in report['after']:
    if slot['material']!=expected[slot['slot']].get_path_name():raise RuntimeError('Material assignment was not retained')
package=mesh.get_outermost()
if package.get_path_name()!=BASE+'Meshes/SK_BookLeafTemplate':raise RuntimeError('Refuse to save a duplicated PIE package')
report['saved']=bool(u.EditorLoadingAndSavingUtils.save_packages([package],False));record()
if not report['saved']:raise RuntimeError('Failed to save corrected source mesh')
# Read the component-level inputs that caused the user's initialization failure.
component=u.PoseableMeshComponent();component.set_skinned_asset_and_update(mesh)
report['chain_bones']=sum(str(component.get_bone_name(i)).startswith('Page_') for i in range(component.get_num_bones()))
report['component_materials']={name:component.get_material(component.get_material_index(name)).get_path_name() for name in expected}
report['complete']=True;record()
u.log('MANUAL_PAGE_MATERIALS_REPAIRED '+json.dumps(report))
