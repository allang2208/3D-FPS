"""Requested inspection of the ten current melee clips and their idle references."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent
ROOTS={'SVD':'/Game/Weapons/SVDDragunov20260922','PKM':'/Game/Weapons/PKMLowpoly20260922'}
MESHES={'SVD':'/StockAdapter20260923/SK_SVD_ModularStock','PKM':'/Accessories14/SK_PKM_Manny_Modular'}
report={'clips':{},'dirty':[], 'PIE_active':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def tr(t):
    return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w], 's':list(t.scale3d.to_tuple())}
for weapon,root in ROOTS.items():
    mesh=u.load_asset(root+MESHES[weapon])
    for family in ['base','vertical','canted','prism','angled']:
        folder=('/Complete20260923/Animations' if family=='base' else '/Accessories20260923/Animations') if weapon=='SVD' else ('/Animations' if family=='base' else '/Accessories14/Animations/'+family)
        prefix='A_'+weapon+'_'+('' if family=='base' else family+'_')
        for clip in ['idle','quick_melee']:
            path=root+folder+'/'+prefix+clip
            anim=u.load_asset(path)
            if not anim: raise RuntimeError('Missing current animation '+path)
            entry={'asset':anim.get_path_name(),'source':anim.get_editor_property('asset_import_data').get_first_filename(),'duration':anim.get_play_length(),'poses':{}}
            if path in dirty:report['dirty'].append(path)
            options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.COMPRESSED;options.optional_skeletal_mesh=mesh
            for t in ([0.] if clip=='idle' else [0.,.035,.075,.1,1/6,.24,.4,.6,.72,.8,.86,.9]):
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,min(t,anim.get_play_length()),options)
                entry['poses'][str(t)]={n:tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ['WPN_root','WPN_SOCKET_Muzzle','clavicle_r','upperarm_r','lowerarm_r','hand_r','clavicle_l','upperarm_l','lowerarm_l','hand_l']}
            report['clips'][weapon+'/'+family+'/'+clip]=entry
(O/'runtime_before.json').write_text(json.dumps(report,indent=2))
print('MELEE24_CURRENT',json.dumps({'PIE_active':report['PIE_active'],'dirty':report['dirty'],'sources':{k:v['source'] for k,v in report['clips'].items()}}))
