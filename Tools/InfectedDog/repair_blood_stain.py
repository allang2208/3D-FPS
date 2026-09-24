"""Repair only the shared blood-stain asset used by infected-dog hits."""
import json,shutil
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/InfectedDogMeshy20260924/RunBloodDiagnosis'
OUT.mkdir(parents=True,exist_ok=True)
PATH='/Game/Weapons/GunplayFX/Impacts/Blood/M_FleshStainV3'
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End current PIE before saving the repaired blood material')
if PATH in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserving unsaved blood-material edits')
backup=OUT/'M_FleshStainV3.before.uasset'
if not backup.exists():shutil.copy2(ROOT/'Content/Weapons/GunplayFX/Impacts/Blood/M_FleshStainV3.uasset',backup)
m=u.load_asset(PATH)
shape=next(n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
    and n.get_editor_property('description')=='Fluid polish blood stain')
shape.set_editor_property('code',(ROOT/'SourceAssets/FluidPolish20260924/BloodStain.hlsl').read_text(encoding='utf-8'))
coverage=L.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
convert=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
if not isinstance(convert,u.MaterialExpressionSubstrateConvertToDecal) or coverage is None:
    raise RuntimeError('Blood graph changed; expected an explicit Substrate decal')
if not L.connect_material_expressions(coverage,'',convert,'Coverage'):
    raise RuntimeError('Could not connect decal coverage')
errors=L.recompile_material(m)
if errors:raise RuntimeError(str(errors))
if not E.save_loaded_asset(m,False):raise RuntimeError('Blood material save failed')
report={'saved':m.get_path_name(),'changes':['HLSL reserved identifier replaced','Substrate decal Coverage connected'],
        'recompile_return':str(errors),'coverage_input':str(coverage),'runtime_tested':False}
(OUT/'blood_repair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLOOD_STAIN_REPAIRED '+json.dumps(report))
