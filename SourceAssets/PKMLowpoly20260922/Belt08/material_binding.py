"""Bind PKM sections by FBX identity, not the retained editor slot label.

Legacy FBX reimport preserves MaterialSlotName even when the incoming material
is renamed or reordered. ImportedMaterialSlotName is the imported identity.
The runtime also reads MaterialSlotName for old/new prop visibility, so both
names must describe the same geometry after a reimport.
"""
import unreal as u

BOX_PAINT_PATH='/Game/Weapons/PKMLowpoly20260922/AmmoBox30/Materials/M_PKM_AmmoBoxPaint_Dry'

def box_paint_override(name):
 # Legacy author blends label the painted box as QBZ_Body. Both reload props
 # retain their section names for visibility, but must not inherit gun steel.
 if name.endswith(('__OldBox','__NewBox')) and u.EditorAssetLibrary.does_asset_exist(BOX_PAINT_PATH):
  return u.load_asset(BOX_PAINT_PATH)
 return None

def imported_name(slot):
 name=str(slot.get_editor_property('imported_material_slot_name'))
 return str(slot.material_slot_name) if name in ('','None') else name

def capture_bindings(mesh):
 bindings={}
 for slot in mesh.materials:
  bindings[str(slot.material_slot_name)]=slot.material_interface
  bindings[imported_name(slot)]=slot.material_interface
 return bindings

def bind_materials(mesh,surfaces,previous):
 slots=mesh.materials;changes=[]
 for i,slot in enumerate(slots):
  before=str(slot.material_slot_name);name=imported_name(slot);base=name.split('__')[0]
  material=box_paint_override(name)
  if not material:
   material=u.load_asset(surfaces[base]) if base in surfaces else previous.get(name) or previous.get(base)
  if not material:raise RuntimeError('No PKM material binding for imported section '+name)
  changes.append({'index':i,'previous_slot':before,'slot':name,'material':material.get_path_name()})
  slot.set_editor_property('material_slot_name',u.Name(name));slot.material_interface=material;slots[i]=slot
 mesh.set_editor_property('materials',slots)
 return changes
