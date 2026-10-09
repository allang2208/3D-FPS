"""Save the tailored hit clip and assign it to Researcher M-05 only."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V02')
DEST='/Game/Monsters/FacelessResearcher'
LIB=u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE is active; researcher reaction assignment not started')
source=json.loads((ROOT/'reaction_source.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'reaction_manifest.json').read_text(encoding='utf-8'))
curves=json.loads((ROOT/'reaction_curves.json').read_text(encoding='utf-8'))
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8'))
def record():
    (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
bp=u.load_asset(source['blueprint']);cdo=u.get_default_object(bp.generated_class())
if cdo.get_editor_property('visual_mesh').get_name() not in ['SK_FacelessResearcher_V01','SK_FacelessResearcher_V02']:
    raise RuntimeError('Researcher active mesh changed during reaction authoring')
mesh=u.load_asset(DEST+'/SK_FacelessResearcher_V02')
clothing=u.load_asset(DEST+'/SK_FacelessResearcher_Clothing_V02')
if not mesh or not clothing:raise RuntimeError('Both V02 meshes must be saved before assigning the character')
skeleton=mesh.get_editor_property('skeleton');actual={m.get_name() for m in mesh.get_editor_property('morph_targets')}
clip_path=DEST+'/Animations/A_Researcher_Hit_V02'
clip=u.load_asset(clip_path) if LIB.does_asset_exist(clip_path) else LIB.duplicate_asset(source['clips']['hit']['source'],clip_path)
if not clip or not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):
    raise RuntimeError('Cannot bind the reaction to the researcher skeleton')
clip.set_preview_skeletal_mesh(mesh)
for name,values in curves['hit'].items():
    if name not in actual:raise RuntimeError('Reaction shape missing from imported mesh: '+name)
    if u.AnimationLibrary.does_curve_exist(clip,name,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,name)
    u.AnimationLibrary.add_curve(clip,name)
    times=[min(i/manifest['hit']['fps'],clip.get_play_length()) for i in range(len(values))]
    u.AnimationLibrary.add_float_curve_keys(clip,name,times,values)
    u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,name,True)
LIB.set_metadata_tag(clip,'ResearcherReactionRevision','V02 original 0.6 second Nurse reaction tracks with coat, trouser-envelope and pocket corrective shapes')
save(clip);save(skeleton)
cdo.set_editor_property('visual_mesh',mesh)
cdo.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
cdo.get_editor_property('combat').set_editor_property('hit_clip',clip)
LIB.set_metadata_tag(bp,'ResearcherRevision','V02 M-05 hit reaction garment tailoring; V01 normal motions retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),mesh=mesh.get_path_name(),clothing=clothing.get_path_name(),
    hit_clip=clip.get_path_name(),hit_duration=clip.get_play_length(),added_hit_shapes=len(curves['hit']),
    source_hit=source['clips']['hit']['source'],runtime_tested=False,rendered=False,
    preserved='V01 complete body, material slots, idle/walk/attack clips and corrective shapes, capsule, gameplay timing and values')
record()
print('RESEARCHER_REACTION_V02_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
