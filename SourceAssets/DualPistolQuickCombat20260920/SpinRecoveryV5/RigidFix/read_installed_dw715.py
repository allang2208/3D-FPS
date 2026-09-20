"""Read only DW715 recovery rigidity and the currently existing dual meshes."""
import unreal as u,json,math,hashlib
from pathlib import Path
P=Path(__file__).parent;PROJECT=Path(u.Paths.project_dir()).resolve()
def vector(v):return [v.x,v.y,v.z]
def unpack(v):return {'p':vector(v.translation),'q':[v.rotation.w,v.rotation.x,v.rotation.y,v.rotation.z],'s':vector(v.scale3d)}
report={'project':str(PROJECT),'clips':{},'live':[]}
for side in ('r','l'):
    mp=f'/Game/Weapons/PistolDualWield20260914/DW715/{side}/SK_Dual_DW715_{side}'
    mesh=u.load_asset(mp);component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
    names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    parents={n:str(component.get_parent_bone(n)) for n in names}
    bones=[n for n in names if n.startswith('WPN_')]
    for revision,kind in [('SpinRecoveryV5',k) for k in ('quickcombat','quickcombat_fitted','quickcombat_long','quickcombat_left','quickcombat_left_fitted','quickcombat_left_long')]+[('VideoRefV3','quickcombat')]:
        path=f'/Game/Weapons/DualPistolQuickCombat20260920/{revision}/DW715/{side}/Animations/A_Dual_DW715_{side}_{kind}'
        clip=u.load_asset(path);modes={}
        for label,mode,retarget in [('source',u.AnimDataEvalType.SOURCE,True),('source_unretargeted',u.AnimDataEvalType.SOURCE,False),('compressed',u.AnimDataEvalType.COMPRESSED,True)]:
            opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=mode;opts.optional_skeletal_mesh=mesh;opts.should_retarget=retarget
            rows=[]
            for i in range(97):
                t=i*clip.get_play_length()/96;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
                rows.append({'time':t,'world':{n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones},
                    'local':{n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in bones}})
            modes[label]=rows
        disk=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        report['clips'][revision+'/'+side+'/'+kind]={'asset':path,'parents':{n:parents[n] for n in bones},'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'samples':modes}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    pawn=u.GameplayStatics.get_player_character(world,0)
    if pawn:
        for c in pawn.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_skeletal_mesh_asset()
            if not mesh or 'SK_Dual_DW715_' not in mesh.get_name():continue
            record={'component':c.get_name(),'mesh':mesh.get_path_name(),'component_transform':unpack(c.get_component_transform()),'bones':{}}
            for i in range(c.get_num_bones()):
                n=str(c.get_bone_name(i))
                if n.startswith('WPN_'):record['bones'][n]=unpack(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))
            anim=c.get_anim_instance()
            if anim:
                for field in ('action_clip','action_time','action_alpha'):
                    try:
                        v=anim.get_editor_property(field);record[field]=v.get_path_name() if isinstance(v,u.Object) else v
                    except Exception:pass
            report['live'].append(record)
(P/'installed_dw715.json').write_text(json.dumps(report,separators=(',',':')))
u.log('DW715_RIGID_READ '+str(len(report['clips']))+' clips; live meshes='+str(len(report['live'])))
