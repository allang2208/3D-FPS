import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
out={}
out['active_head_evidence']='ColdSteelPlayer_PIE_0_A.sav PlayerHeadId=kaitlin; corroborated by FPSGAME.log 2026-10-30 09:24 UTC'
cd=u.get_default_object(u.FPSGAMECharacter)
out['defaults']={}
for key in ('hip_viewmodel_location','m4_hip_viewmodel_location','m4_action_viewmodel_location','viewmodel_scale','base_vertical_field_of_view'):
    try:out['defaults'][key]=str(cd.get_editor_property(key))
    except Exception as e:out['defaults'][key]=str(e)
data=json.loads((O/'equipment_inputs.json').read_text())['M4'];mesh=u.load_asset(data['path'])
clip=u.load_asset('/Game/Weapons/M4ContactImpactFinal/A_AKM_idle')
names=list(data['bones'])
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
out['m4_reference']={'bones':data['bones'],'poses':{n:tr(t) for n,t in zip(names,u.AnimationLibrary.get_bone_poses_for_time(clip,names,0.,False,mesh))}}
(O/'game_context.json').write_text(json.dumps(out,indent=2));print('M24_CONTEXT',json.dumps(out['defaults']),flush=True)
