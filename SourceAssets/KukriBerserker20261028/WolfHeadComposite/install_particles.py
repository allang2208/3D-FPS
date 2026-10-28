"""Save only the helix particle revision of the existing berserker HUD."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/WolfHeadComposite/install_particles.py').resolve().parent
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
path='/Game/Weapons/Kukri20261020/Berserker20261028/M_BerserkerEnergyHud'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Preserve the running game; material saving needs the preview to end')
if path in {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve unsaved berserker HUD')
mat=u.load_asset(path)
if not mat:raise RuntimeError('Missing active HUD')
custom=next(n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom))
code=(P/'BerserkerWolfHeadHud.hlsl').read_text('utf-8')
custom.set_editor_property('code',code)
E.set_metadata_tag(mat,'HelixPresentation','DiscreteSparkFlowAndDriftV1')
errors=list(L.recompile_material(mat))
if errors:raise RuntimeError(str(errors))
if not E.save_loaded_asset(mat,False):raise RuntimeError('HUD save failed')
receipt={'complete':True,'saved_asset':mat.get_path_name(),'compile_errors':errors,
    'hlsl_sha256':hashlib.sha256(code.encode()).hexdigest(),
    'radius':160.0,'pitch':384.0,'turns':2.72,'rotation_radians_per_second':.45,
    'main_particle_lanes':2,'main_particles_per_lane':156,'per_pixel_main_candidates':12,
    'retained_ambient_slots':32,'drifting_slots_reused':22,'runtime_tested':False}
(P/'particle-install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BERSERKER_HELIX_PARTICLES_COMPILED_AND_SAVED')
