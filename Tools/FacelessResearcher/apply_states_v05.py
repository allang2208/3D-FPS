"""Save researcher-native special states and bind them to the original BP."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V05')
DEST='/Game/Monsters/FacelessResearcher';LIB=u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; M05 special-state assignment not started')
source=json.loads((ROOT/'state_source.json').read_text(encoding='utf-8'))
curves=json.loads((ROOT/'state_curves.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'state_manifest.json').read_text(encoding='utf-8'))
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8'))
def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
bp=u.load_asset(source['blueprint']);cdo=u.get_default_object(bp.generated_class())
if cdo.get_editor_property('visual_mesh').get_name() not in ['SK_FacelessResearcher_V04','SK_FacelessResearcher_V05']:
    raise RuntimeError('Researcher visual mesh changed during state authoring')
mesh=u.load_asset(DEST+'/SK_FacelessResearcher_V05');cloth=u.load_asset(DEST+'/SK_FacelessResearcher_Clothing_V05')
if not mesh or not cloth:raise RuntimeError('Both V05 meshes must be saved first')
skeleton=mesh.get_editor_property('skeleton');actual={x.get_name() for x in mesh.get_editor_property('morph_targets')};clips={}
for role,entry in source['clips'].items():
    path=DEST+'/Animations/V05/A_Researcher_'+role+'_V05'
    clip=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(entry['source'],path)
    if not clip or not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Cannot bind '+role+' to researcher skeleton')
    for name,values in curves[role].items():
        if name not in actual:raise RuntimeError('Missing clothing morph '+name)
        if u.AnimationLibrary.does_curve_exist(clip,name,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,name)
        u.AnimationLibrary.add_curve(clip,name)
        times=[min(i/manifest[role]['fps'],clip.get_play_length()) for i in range(len(values))]
        u.AnimationLibrary.add_float_curve_keys(clip,name,times,values)
        u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,name,True)
    clip.set_editor_property('rate_scale',entry['rate_scale']);clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip,'ResearcherSourceMotion',entry['source'])
    LIB.set_metadata_tag(clip,'ResearcherTailoring','V05 special-state clothing; accepted V04 base and core motions retained')
    save(clip);clips[role]=clip
save(skeleton)
cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
combat=cdo.get_editor_property('combat');knock=cdo.get_editor_property('knockdown')
combat.set_editor_property('dizzy_clip',clips['dizzy'])
for role in ['fall','get_up','prone_get_up']:knock.set_editor_property(role+'_clip',clips[role])
LIB.set_metadata_tag(bp,'ResearcherRevision','V05 native special states and cloth, V04 accepted core clips retained; M05 native presentation supplies curve-preserving crossfades')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
report.update(stage='saved',blueprint=bp.get_path_name(),mesh=mesh.get_path_name(),clothing=cloth.get_path_name(),
    clips={k:v.get_path_name() for k,v in clips.items()},shape_counts={k:len(v) for k,v in curves.items()},
    retained_core_clips={role:cdo.get_editor_property(role+'_clip').get_path_name() for role in ['idle','walk','attack']},
    retained_hit_clip=combat.get_editor_property('hit_clip').get_path_name(),runtime_tested=False,rendered=False)
record();print('M05_V05_SPECIAL_STATES_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
