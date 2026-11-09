from pathlib import Path
import unreal as u
m=u.load_asset('/Game/Weapons/M249/Materials/M_M249_OpticHousing')
lib=u.MaterialEditingLibrary
color=lib.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
if not lib.connect_material_property(color,'A',u.MaterialProperty.MP_OPACITY_MASK):raise RuntimeError('Housing mask connection failed')
lib.recompile_material(m)
if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Housing save failed')
script=Path(__file__).with_name('read_saved.py')
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'))
