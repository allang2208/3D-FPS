"""Authorized desktop executor only. Never run import_candidate.py/install_formal.py.
Invoke using runpy.run_path(path, init_globals={'APPLY_APPROVED': True}) only after
parent has authorized this exact sphere material change. No PIE or map writes.
"""
from pathlib import Path
import unreal as u, hashlib, json, datetime
ROOT=Path(__file__).resolve().parent
assert globals().get('APPLY_APPROVED') is True,'Explicit sphere-only application approval required'
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
assert not editor.get_game_world(),'Stop: PIE running'
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Stop: pre-existing dirty content'
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Stop: pre-existing dirty map'
D='/Game/Props/GodSpaceCoreStarfield20261005/DetailV4/Materials/'
M=D+'M_CoreStarfield_V4'
mat=u.load_asset(M); mi=u.load_asset(D+'MI_Core_Starfield_V4')
mesh=u.load_asset('/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceCore')
assert mat and mi and mesh
assert mi.get_editor_property('parent')==mat
assert mat.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_UNLIT
for key in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values']:
 assert not mi.get_editor_property(key),'Unexpected formal instance override: '+key
slots_before=[(str(x.material_slot_name),x.material_interface.get_path_name()) for x in mesh.get_editor_property('static_materials')]
assert ('Core_Starfield',mi.get_path_name()) in slots_before
custom=u.find_object(None,M+'.M_CoreStarfield_V4:MaterialExpressionCustom_0')
assert custom and isinstance(custom,u.MaterialExpressionCustom),'Exact audited custom node missing'
assert L.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)==custom
names=[str(x.get_editor_property('input_name')) for x in custom.get_editor_property('inputs')]
assert names==['Tex','Stars','Detail','P','C','V','Strength','StarStrength','Depth','Rim','DetailStrength'],names
expected={'StarfieldStrength':3.4,'StarsStrength':3.5,'InteriorDepth':.65,'RimStrength':.9,'DetailStrength':1.0}
for k,v in expected.items():assert abs(L.get_material_instance_scalar_parameter_value(mi,k)-v)<1e-5,k
def canonical(s):return s.replace('\r\n','\n').strip()+'\n'
def digest(s):return hashlib.sha256(canonical(s).encode()).hexdigest()
old=custom.get_editor_property('code');baseline=(ROOT/'Starfield_V4.hlsl').read_text();new=(ROOT/'Starfield_BlueGlow_V5_SamePins.hlsl').read_text()
assert digest(old) in [digest(baseline),digest(new)],'Live shader differs from audited source: stop and reconcile'
# The old V1 completion metadata is intentionally neither read as a cache nor erased.
# Updating this exact node leaves all existing pins, links, MI parents and mesh slots intact.
if digest(old)!=digest(new):
 (ROOT/'live_sphere_before.hlsl').write_text(old)
 try:
  mat.modify();custom.modify();custom.set_editor_property('code',new)
  errors=L.recompile_material(mat);assert not errors,errors
  assert [str(x.get_editor_property('input_name')) for x in custom.get_editor_property('inputs')]==names
  assert L.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)==custom
  assert [(str(x.material_slot_name),x.material_interface.get_path_name()) for x in mesh.get_editor_property('static_materials')]==slots_before
 except Exception:
  custom.set_editor_property('code',old);L.recompile_material(mat)
  raise
 E.set_metadata_tag(mat,'CoreBlueGlowRevision','V5-sphere-only')
 assert E.save_loaded_asset(mat,False),'Sphere material save failed; stop and inspect before retry'
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'material':mat.get_path_name(),'custom_node':custom.get_path_name(),'hlsl_sha256':digest(new),'input_names':names,'slots_unchanged':True,'sphere_model':'UNLIT','new_glow_defaults':{'BlueGlowStrength':2.8,'BlueRimStrength':2.4},'gold_modified':False,'mesh_reimported':False,'textures_modified':False,'map_saved':False,'PIE':False,'engine_visual_acceptance':False}
(ROOT/'sphere_only_apply_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
