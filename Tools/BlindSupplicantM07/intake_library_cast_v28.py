"""Read local casting source poses and current M07 proportions for authoring."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/LibraryCastV28')
ROOT.mkdir(parents=True, exist_ok=True)
VEXA = '/Game/Vefects/Easy_Impact_Frames/Demo/Stylized_Female_Character_Vexa'
RAMPAGE = '/Game/ParagonRampage/Characters/Heroes/Rampage'
sources = [(VEXA+'/Animations/'+name, VEXA+'/SK/SK_Vefects_Vexa') for name in
           ('HandsSpell_Vexa','SnappySpell_Vexa','SummonCreature_Vexa')]
sources.append((RAMPAGE+'/Animations/Cast', RAMPAGE+'/Meshes/Rampage'))
bp = u.load_asset('/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07')
defaults = u.get_default_object(bp.generated_class())
mesh = defaults.get_editor_property('visual_mesh')
bounds = mesh.get_bounds()
report = dict(candidates=[], current=dict(mesh=mesh.get_path_name(),
    height_cm=bounds.box_extent.z*2., bounds_origin_cm=[bounds.origin.x,bounds.origin.y,bounds.origin.z],
    settings={p: defaults.get_editor_property(p) for p in ('attack_range','sweep_hit_radius',
        'magic_minimum_distance','magic_release_contact_time','magic_charge_forward_offset_cm')},
    clips={p: defaults.get_editor_property(p).get_path_name() for p in ('magic_gather_clip','magic_release_clip',
        'melee_left_clip','melee_right_clip')}), rendered=False, tested=False)

def transform(t):
    return dict(translation_cm=[t.translation.x,t.translation.y,t.translation.z],
                rotation_xyzw=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])

for path, mesh_path in sources:
    clip, donor = u.load_asset(path), u.load_asset(mesh_path)
    if not isinstance(clip,u.AnimSequence) or not isinstance(donor,u.SkeletalMesh):
        report['candidates'].append(dict(asset=path,mesh=mesh_path,available=False))
        continue
    component = u.new_object(u.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(donor)
    bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    options = u.AnimPoseEvaluationOptions()
    options.evaluation_type = u.AnimDataEvalType.RAW
    options.optional_skeletal_mesh = donor
    duration = clip.get_play_length()
    frames = []
    for i in range(round(duration*30)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/30.,duration),options)
        frames.append({b:transform(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones})
    reference = {b:transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
    cache = ROOT/(clip.get_name()+'_source.json')
    cache.write_text(json.dumps(dict(asset=path,mesh=mesh_path,fps=30,reference=reference,frames=frames)),encoding='utf-8')
    report['candidates'].append(dict(asset=path,mesh=mesh_path,available=True,duration_seconds=duration,
        bones=bones,parents={b:str(component.get_parent_bone(b)) for b in bones},pose_cache=str(cache)))
(ROOT/'source_intake_v28.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M07_V28_CAST_INTAKE_SAVED '+str(ROOT/'source_intake_v28.json'))
