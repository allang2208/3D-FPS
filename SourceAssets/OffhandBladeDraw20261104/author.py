"""Author left-only draws on the weapon and both body rigs from their native dual draw and carry."""
from pathlib import Path
import json
import unreal as u

project=Path(u.Paths.project_dir()).resolve()
dest='/Game/Weapons/TacticalHatchet20261101/OffhandDraw'
body=json.loads((project/'Content/ColdSteelData/player_body.json').read_text('utf-8-sig'))
dual='/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualEquip'
hatchet='/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_PairEquipKH'
arm_mesh='/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'
A=u.AnimPoseExtensions
saved={}
wrist_curves={}
if any(pkg.get_path_name().startswith(dest+'/') for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved offhand draw assets')

def warp(t,src,dst):
    for i in range(1,len(src)):
        if t<=src[i]:
            weight=(t-src[i-1])/(src[i]-src[i-1])
            return dst[i-1]+weight*(dst[i]-dst[i-1])
    return dst[-1]

def bake(label,mesh_path,idle_path,body_draw=None):
    mesh=u.load_asset(mesh_path);idle=u.load_asset(idle_path);cfg=u.AnimPoseEvaluationOptions()
    cfg.optional_skeletal_mesh=mesh;cfg.evaluation_type=u.AnimDataEvalType.SOURCE
    sk=u.SkeletalMeshComponent();sk.set_skeletal_mesh_asset(mesh)
    names=[str(n) for n in A.get_bone_names(mesh.skeleton.get_reference_pose())]
    left={'clavicle_l'}
    for n in names:
        if str(sk.get_parent_bone(n)) in left:left.add(n)
    saved[label]={}
    for axe in [False,True]:
        role='Hatchet' if axe else 'Kukri'
        native=u.load_asset(hatchet if axe else dual)
        draw=u.load_asset(body_draw) if body_draw else native
        length=native.get_play_length()
        frames=round(length*60)
        name='A_Offhand'+role+'Equip';folder=dest+'/'+label;path=folder+'/'+name
        factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
        seq=(u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else
             u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory))
        seq.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(60,1))
        seq.set_retarget_source_asset(mesh);seq.update_retarget_source_asset_data()
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):raise RuntimeError(path)
        keys={n:[] for n in names};positions=[]
        kukri_length=u.load_asset(dual).get_play_length()
        for i in range(frames+1):
            t=min(i/60,length)
            # Both body takes use their own authored left draw. Align their release and catch with the FPS blade.
            cut=t if not body_draw else warp(t,[0,.067+(.1833 if axe else 10/120),.067+(.3833 if axe else 13/30),length],
                [0,.067+10/120,.067+13/30,kukri_length])*draw.get_play_length()/kukri_length
            action=A.get_anim_pose_at_time(draw,min(draw.get_play_length(),cut),cfg)
            hold=A.get_anim_pose_at_time(idle,t%max(.01,idle.get_play_length()),cfg)
            for n in names:
                keys[n].append(A.get_bone_pose(action if n in left else hold,n,u.AnimPoseSpaces.LOCAL))
            if not body_draw:
                wrist=A.get_bone_pose(action,'hand_l',u.AnimPoseSpaces.WORLD).translation
                positions.append((-wrist.y,wrist.x,wrist.z))
        if positions:
            end=positions[-1];wrist_curves[role]=[tuple(a-b for a,b in zip(point,end)) for point in positions]
        ctl=seq.get_editor_property('controller')
        tracks={str(n) for n in u.AnimationLibrary.get_animation_track_names(seq)}
        ctl.open_bracket(name,False)
        try:
            ctl.set_frame_rate(u.FrameRate(60,1),False);ctl.set_number_of_frames(u.FrameNumber(frames),False)
            for n,values in keys.items():
                if n not in tracks:ctl.add_bone_curve(n,False)
                if not ctl.set_bone_track_keys(n,[t.translation for t in values],[t.rotation for t in values],[t.scale3d for t in values],False):raise RuntimeError(n)
            if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq):raise RuntimeError(path)
        finally:ctl.close_bracket(False)
        seq.set_editor_property('enable_root_motion',False);seq.set_editor_property('force_root_lock',True);seq.set_preview_skeletal_mesh(mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq) or not u.EditorAssetLibrary.save_loaded_asset(seq,False):raise RuntimeError(path)
        saved[label][role]=seq.get_path_name()

bake('Arms',arm_mesh,'/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualIdle')
for label,rig in [('Jason',body),('Kaitlin',body['body_variants']['kaitlin'])]:
    bake(label,rig['body_mesh'],rig['clips']['Kukri.FullBody.Dual.Idle'],rig['clips']['Kukri.FullBody.Dual.Equip'])
lines=['#pragma once','// Native left-wrist displacement from the final carry, in camera centimetres, sampled at 60 Hz.',
       'namespace OffhandDrawWrist','{']
for key,samples in wrist_curves.items():
    lines+=['    inline constexpr float '+key+'[][3]={']
    lines+=['        {'+','.join(f'{x:.4f}f' for x in p)+'},' for p in samples]
    lines+=['    };']
lines+=['}']
(project/'Source/FPSGAME/Weapons/Kukri/OffhandDrawWrist.h').write_text('\n'.join(lines)+'\n','utf8')
(Path(__file__).parent/'saved.json').write_text(json.dumps(saved,indent=2),'utf8')
