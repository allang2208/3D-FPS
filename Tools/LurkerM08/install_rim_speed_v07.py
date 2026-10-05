"""Bind real skinned aperture landmarks and save the requested M08 speeds."""
import json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/Monsters/LurkerM08/RimSpeedV07_20261005'
BASE='/Game/Monsters/LurkerM08';REV='M08_RimSpeedV07_20261005';LIB=u.EditorAssetLibrary
SOURCE=json.loads((ROOT/'rim_binding.json').read_text(encoding='utf-8'))
REPORT={'revision':REV,'state':'binding','saved':[],'runtime_tested':False,'rendered':False}
def record():(ROOT/'installation.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if asset is None:raise RuntimeError('Missing asset '+path)
    return asset
def save(asset):
    LIB.set_metadata_tag(asset,'M08.RimSpeedRevision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    REPORT['saved'].append(asset.get_path_name());record()
def vec(v):return (v.x,v.y,v.z)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def ue_name(name):return name.replace('.','_')

def run():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if package.get_name().startswith(BASE):raise RuntimeError('Preserving unsaved M08 asset '+package.get_name())
    bp=load(BASE+'/BP_LurkerM08');dataset=load(BASE+'/DA_M08_AnimationSet');mesh=load(SOURCE['mesh_asset'])
    actions={str(k):v for k,v in dataset.get_editor_property('actions').items()};clip=actions['AttackAirCannon'].sequence
    backup=ROOT/'Before';backup.mkdir(exist_ok=True)
    for name in ('BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset'):
        if not (backup/name).exists():shutil.copy2(PROJECT/'Content/Monsters/LurkerM08'/name,backup/name)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    before=ROOT/'before_references.json'
    if not before.exists():before.write_text(json.dumps({'actions':{str(k):v.sequence.get_path_name() if v.sequence else None for k,v in actions.items()},
        'walk_speed':cdo.get_editor_property('walk_speed'),'chase_speed':cdo.get_editor_property('chase_speed'),
        'climb_speed':cdo.get_editor_property('climb_speed'),
        'source_walk_speed':dataset.walk_speed,'source_run_speed':dataset.run_speed,
        'run_blend_start_ratio':dataset.run_blend_start_ratio,'run_blend_full_ratio':dataset.run_blend_full_ratio,
        'note':'Native defaults may already be rebased by the V07 build; requested pre-change rates were 100/210/180 cm/s.'},ensure_ascii=False,indent=2),encoding='utf-8')
    # Resolve the actual imported reference basis. This handles FBX handedness,
    # armature container scale, and bone roll without guessed axis signs.
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,options)
    source_bones=SOURCE['calibration_bones']
    names=set(source_bones)|{w['bone'] for p in SOURCE['landmarks'] for w in p['weights']}
    refs={n:u.AnimPoseExtensions.get_ref_bone_pose(pose,ue_name(n),u.AnimPoseSpaces.WORLD) for n in names}
    src_origin=source_bones['pelvis'];dst_origin=vec(refs['pelvis'].translation)
    a=sub(source_bones['hand.L'],source_bones['hand.R']);b=sub(source_bones['chest'],src_origin);c=sub(source_bones['arch_crown'],src_origin)
    aa=sub(vec(refs['hand.L'].translation),vec(refs['hand.R'].translation));bb=sub(vec(refs['chest'].translation),dst_origin);cc=sub(vec(refs['arch_crown'].translation),dst_origin)
    determinant=dot(a,cross(b,c))
    if abs(determinant)<1e-9:raise RuntimeError('Degenerate imported reference basis')
    def imported_position(position):
        q=sub(position,src_origin)
        x=dot(q,cross(b,c))/determinant;y=dot(a,cross(q,c))/determinant;z=dot(a,cross(b,q))/determinant
        return u.Vector(*(dst_origin[i]+x*aa[i]+y*bb[i]+z*cc[i] for i in range(3)))
    landmarks=[];binding=[]
    for row in SOURCE['landmarks']:
        vertex=u.LurkerM08RimVertex();influences=[]
        point=imported_position(row['position_m']);authored=[]
        for weight in row['weights']:
            local=u.MathLibrary.inverse_transform_location(refs[weight['bone']],point)
            influence=u.LurkerM08RimInfluence()
            influence.set_editor_property('bone',ue_name(weight['bone']))
            influence.set_editor_property('bone_local_position',local);influence.set_editor_property('weight',weight['weight'])
            influences.append(influence);authored.append({'bone':ue_name(weight['bone']),'local':vec(local),'weight':weight['weight']})
        vertex.set_editor_property('influences',influences);landmarks.append(vertex)
        binding.append({'source_vertex':row['vertex'],'reference_component_cm':vec(point),'influences':authored})
    cdo.set_editor_property('air_cannon_rim',landmarks)
    for key,value in {'walk_speed':150.,'chase_speed':315.,'climb_speed':270.,'pounce_flight_speed_multiplier':2.}.items():cdo.set_editor_property(key,value)
    cdo.get_editor_property('character_movement').set_editor_property('max_walk_speed',315.)
    # Keep source stride speeds (100/210) so animation advances with travel.
    # Only the gait-selection band moves: old 100..136.5 -> 150..204.75 cm/s.
    dataset.set_editor_property('run_blend_start_ratio',150./210.)
    dataset.set_editor_property('run_blend_full_ratio',204.75/210.)
    save(dataset);save(bp)
    REPORT.update(state='rim_and_speed_v07_saved_and_bound',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
        mesh=mesh.get_path_name(),landmarks=binding,landmark_count=len(landmarks),
        speeds_cm_s={'walk':150,'chase':315,'climb':270},pounce_flight_speed_multiplier=2,
        pounce_flight_seconds='clamp(distance_cm/760 + 0.16, 0.44, 0.95) / 2',
        source_stride_speeds={'walk':dataset.walk_speed,'run':dataset.run_speed},f6_id='LurkerM08',
        unchanged_actions={str(k):v.sequence.get_path_name() if v.sequence else None for k,v in actions.items()})
    record();u.log('M08_RIM_SPEED_V07_SAVED '+bp.get_path_name())
try:run()
except Exception:
    REPORT['state']='failed';REPORT['error']=traceback.format_exc();record();raise
