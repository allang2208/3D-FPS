"""Repair the warhammer surface and active viewmodel's saved material slots."""
import json,shutil,sys
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
R=P.parents[2]
D='/Game/Weapons/SteelWarhammer20261014'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
sys.path.insert(0,str(P.parent))
from warhammer_surface import build_surface
asset=D+'/Materials/M_SteelWarhammerSurface'
mesh_path=D+'/SprintDragV1/SK_Warhammer_BareArmsSprintV1'
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name() in (asset,mesh_path):raise RuntimeError('Unsaved warhammer asset; preserve the current edit')
material=u.load_asset(asset)
if not material:raise RuntimeError('Missing warhammer material')
textures={key:u.load_asset(D+'/Textures/T_SteelWarhammer_'+key) for key in ('BaseColor','MetallicRoughness','Normal')}
if any(tex is None for tex in textures.values()):raise RuntimeError('Missing source texture; do not replace the graph')
mesh=u.load_asset(mesh_path)
bare=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/Pickaxe/SK_Pickaxe_BareArmsV7')
if not mesh or not bare:raise RuntimeError('Missing active viewmodel or native hand donor')
native={str(s.material_slot_name):s.material_interface for s in bare.get_editor_property('materials')}
bindings={'M_SteelWarhammerSurface':material}
for author,source in (('Skin_UpperArm','BareUpperArms'),('Skin_Forearm','BareLowerArms'),('Skin_Hand','BareHandsOriginalGrip')):
    bindings[author]=native[source]
if any(m is None for m in bindings.values()):raise RuntimeError('Native material missing; preserve viewmodel')
before=P/'Before';before.mkdir(exist_ok=True)
file=R/'Content/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface.uasset'
if not (before/file.name).exists():shutil.copy2(file,before/file.name)
mesh_file=R/'Content/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1.uasset'
if not (before/mesh_file.name).exists():shutil.copy2(mesh_file,before/mesh_file.name)
receipt=build_surface(material,textures)
slots=mesh.get_editor_property('materials')
for i,slot in enumerate(slots):
    slot.set_editor_property('material_interface',bindings[str(slot.material_slot_name)])
    slots[i]=slot
mesh.set_editor_property('materials',slots)
if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost(),mesh.get_outermost()],False):raise RuntimeError('Warhammer asset save failed')
receipt['mesh']=mesh.get_path_name()
receipt['slots']=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.get_editor_property('materials')]
receipt.update(saved=True,game_started=False,mesh_reimported=False)
(P/'repair_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_MATERIAL_REPAIRED '+json.dumps(receipt))
