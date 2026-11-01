import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;R=P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(R/'SourceAssets/SteelWarhammer20261014/NormalComboRhythmV7/Warhammer_Combo_Rhythm_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
def sample(name,t):
    a=bpy.data.actions[name];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    f=t*300;scene.frame_set(int(f),subframe=f-int(f))
    w=rig.pose.bones['WPN_root'].matrix.inverted()
    return {s:w@rig.pose.bones['hand_'+s].matrix for s in 'lr'}
out=[]
for stage,turn,span,preload in [(1,1.05,.40,.42),(2,1.35,.25,.27),(3,1.05,.40,.41)]:
    fr=sample(f'A_Warhammer_Slash{stage}',turn)
    errors={s:[] for s in 'lr'}
    for i in range(121):
        t=i/120;alpha=t*t*t*(t*(t*6-15)+10)
        to=sample(f'A_Warhammer_Slash{stage%3+1}',preload*t)
        for s in 'lr':
            a,b=fr[s],to[s];ap,aq,_=a.decompose();bp,bq,_=b.decompose()
            aa,ba=math.atan2(ap.y,ap.x),math.atan2(bp.y,bp.x)
            angle=aa+((ba-aa+math.pi)%(2*math.pi)-math.pi)*alpha
            rad=ap.xy.length+(bp.xy.length-ap.xy.length)*alpha
            loc=Vector((rad*math.cos(angle),rad*math.sin(angle),ap.z+(bp.z-ap.z)*alpha))
            q=aq.slerp(bq,alpha)
            # Compare each endpoint's palm-local contact with the blended shaft.
            ca=a.inverted()@Vector((0,0,ap.z));cb=b.inverted()@Vector((0,0,bp.z))
            palm_contact=loc+q@ca.lerp(cb,alpha)
            err=palm_contact.xy.length
            errors[s].append(err*1000)
    out.append({'transition':str(stage)+'->'+str(stage%3+1),'max_contact_gap_mm':{s:max(es) for s,es in errors.items()}})
(P/'blend_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('GRIP_BLEND '+json.dumps(out))
