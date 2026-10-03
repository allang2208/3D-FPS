"""Capture the existing game pawn's sword contacts; never starts or changes play."""
import json
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonTwoHandSword20261003/runtime-followup.json')
def path(x): return x.get_path_name() if x else None
def tf(t):
    return {'p':[t.translation.x,t.translation.y,t.translation.z],
            'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
            's':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
report={'pawns':[]}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['world']=path(world)
if world:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        b=pawn.get_component_by_class(u.FPSPlayerBodyComponent)
        p={'pawn':path(pawn),'body_state':b.get_body_state().export_text() if b else None,'meshes':[]}
        try:p['adapter_anim']=path(b.get_editor_property('body_animation'))
        except Exception as e:p['adapter_anim_error']=str(e)
        for m in pawn.get_components_by_class(u.SkeletalMeshComponent):
            if m!=pawn.mesh and m.get_class().get_name() not in ('RuneSwordMeshComponent','FPSBodyWeaponMeshComponent') and 'Sword' not in m.get_name():continue
            a=m.get_skeletal_mesh_asset()
            if not a:continue
            names=[str(n) for n in m.get_all_socket_names()]
            bones=[n for n in names if n in ('root','pelvis','spine_01','spine_03','WPN_root') or any(n.startswith(s) for s in ('clavicle','upperarm','lowerarm','hand','middle_01','index_01','thumb_01'))]
            p['meshes'].append({'name':m.get_name(),'class':m.get_class().get_name(),'mesh':path(a),'anim':path(m.get_anim_instance()),
                'visible':m.is_visible(),'hidden':m.get_editor_property('hidden_in_game'),
                'parent':path(m.get_attach_parent()),'socket':str(m.get_attach_socket_name()),'frame':tf(m.get_world_transform()),
                'bones':{n:{'parent':str(m.get_parent_bone(n)),'cs':tf(m.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))} for n in bones}})
            for prop in ('predicted_lod_level','forced_lod_model','disable_post_process_blueprint','pause_anims','leader_pose_component'):
                try:p['meshes'][-1][prop]=str(m.get_editor_property(prop))
                except Exception as e:p['meshes'][-1][prop]=str(e)
        report['pawns'].append(p)
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SWORD_RUNTIME_CAPTURE '+str(out)+' pawns='+str(len(report['pawns'])))
