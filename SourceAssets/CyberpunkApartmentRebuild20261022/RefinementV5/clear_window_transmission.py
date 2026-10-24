"""Remove only the opaque coating from the already-installed window material."""
from pathlib import Path
from datetime import datetime
import json,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
PATH='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV5/Materials/M_AP5_WindowGlass'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
report=dict(stage='preparing',material=PATH,game_run=False,rendered=False)
def record():(ROOT/'window-transmission-saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
try:
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
 if any(p.get_path_name()==PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved window material')
 m=u.load_asset(PATH)
 if not m:raise RuntimeError('Installed window material missing')
 backup=ROOT/'Backups'/('WindowTransmission-'+datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=True)
 source=PROJECT/'Content'/((PATH.removeprefix('/Game/'))+'.uasset');shutil.copy2(source,backup/source.name)
 report['backup']=str(backup/source.name)
 slab=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
 if not isinstance(slab,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unexpected installed window surface')
 opacity=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='GlassOpaqueCoating'),None)
 if opacity is None:opacity=L.create_material_expression(m,u.MaterialExpressionScalarParameter)
 opacity.set_editor_property('parameter_name','GlassOpaqueCoating');opacity.set_editor_property('default_value',0.)
 if not L.connect_material_expressions(opacity,'',slab,'Opacity'):raise RuntimeError('Window opaque coating connection failed')
 if not L.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY):raise RuntimeError('Window root opacity connection failed')
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Window material compile failed '+str(errors))
 if not E.save_loaded_asset(m,False):raise RuntimeError('Window material save failed')
 report.update(stage='material_saved',opaque_coating=0.,surface_coverage_unchanged=True,
  transmittance_unchanged=True,specular_unchanged=True,roughness_unchanged=True,normal_unchanged=True,
  geometry_unchanged=True,map_rewrite_required=False)
 record();print('APARTMENT_CLEAR_WINDOW_MATERIAL_SAVED',PATH)
except Exception:
 report['stage']='failed';report['error']=traceback.format_exc();record();raise
