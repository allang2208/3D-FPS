"""Save four unchanged bone-motion copies with new continuous coat curves."""
import json
from pathlib import Path
import unreal as u
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009')
ROOT=BASE/'V03';DEST='/Game/Monsters/FacelessResearcher';LIB=u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; waist assignment not started')
source=json.loads((ROOT/'waist_source.json').read_text(encoding='utf-8'))
curves=json.loads((ROOT/'waist_curves.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'waist_manifest.json').read_text(encoding='utf-8'))
oldnames=json.loads((BASE/'V02/export_receipt.json').read_text(encoding='utf-8'))['morph_names']
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8'))
def record():(ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
bp=u.load_asset(source['blueprint']);cdo=u.get_default_object(bp.generated_class())
if cdo.get_editor_property('visual_mesh').get_name() not in ['SK_FacelessResearcher_V02','SK_FacelessResearcher_V03']:
    raise RuntimeError('Researcher mesh changed since the waist authoring inputs were exported')
mesh=u.load_asset(DEST+'/SK_FacelessResearcher_V03');clothing=u.load_asset(DEST+'/SK_FacelessResearcher_Clothing_V03')
if not mesh or not clothing:raise RuntimeError('Save both V03 meshes before binding the character')
skeleton=mesh.get_editor_property('skeleton');actual={m.get_name() for m in mesh.get_editor_property('morph_targets')};clips={}
for role,entry in source['clips'].items():
    path=DEST+'/Animations/V03/A_Researcher_'+role+'_V03'
    clip=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(entry['source'],path)
    if not clip or not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Cannot bind '+role)
    for name in oldnames:
        if u.AnimationLibrary.does_curve_exist(clip,name,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,name)
    for name,values in curves[role].items():
        if name not in actual:raise RuntimeError('Missing imported tailoring shape '+name)
        if u.AnimationLibrary.does_curve_exist(clip,name,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,name)
        u.AnimationLibrary.add_curve(clip,name)
        times=[min(i/manifest[role]['fps'],clip.get_play_length()) for i in range(len(values))]
        u.AnimationLibrary.add_float_curve_keys(clip,name,times,values)
        u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,name,True)
    clip.set_editor_property('rate_scale',entry['rate_scale']);clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip,'ResearcherTailoring','V03 continuous 360-degree waist band and clothed-body envelope; source bone tracks and rate retained')
    LIB.set_metadata_tag(clip,'ResearcherSourceMotion',entry['source']);save(clip);clips[role]=clip
save(skeleton)
cdo.set_editor_property('visual_mesh',mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
for role in ['idle','walk','attack']:cdo.set_editor_property(role+'_clip',clips[role])
cdo.get_editor_property('combat').set_editor_property('hit_clip',clips['hit'])
LIB.set_metadata_tag(bp,'ResearcherRevision','V03 M-05 circumferential waist/hem contact in idle, walk, attack and stagger')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
report.update(stage='saved',blueprint=bp.get_path_name(),mesh=mesh.get_path_name(),clothing=clothing.get_path_name(),
    clips={k:v.get_path_name() for k,v in clips.items()},shape_counts={k:len(v) for k,v in curves.items()},
    preserved='Complete body, trousers, topology, UV, materials, skeleton, source bone tracks, rate scales, gameplay values and M-05 entry',
    runtime_tested=False,rendered=False)
record();print('RESEARCHER_WAIST_V03_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
