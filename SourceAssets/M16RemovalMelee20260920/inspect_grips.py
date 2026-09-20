import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;S=O.parent;out={}
def read(path,action=None):
 bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False);r=bpy.data.objects['SK_M4_Infima']
 if action:r.animation_data.action=bpy.data.actions[action];r.animation_data.action_slot=r.animation_data.action.slots[0]
 bpy.context.scene.frame_set(0);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
for fam in ['base','drum','vertical','canted','prism','angled']:
 profile=fam.title();d=read(S/'M4QuickMeleeRefine20260919N'/profile/f'M4_QuickCombat_{profile}_Editable.blend')
 source=S/'M16Gameplay20260919/M16_Manny_Editable.blend' if fam=='base' else S/'M16UniversalAttachments20260920'/f'M16_{fam}_Animations_Editable.blend'
 p=read(source,'M16_idle' if fam=='base' else f'M16_{fam}_idle');out[fam]={}
 for side in ['l','r']:
  h='hand_'+side;delta=p['WPN_root'].inverted()@p[h]@(d['WPN_root'].inverted()@d[h]).inverted()
  out[fam][side]={'mm':[1000*x for x in delta.translation],'degrees':math.degrees(delta.to_quaternion().angle),'matrix':[list(x) for x in delta]}
(O/'grip_registration.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:{s:{x:y for x,y in v.items() if x!='matrix'} for s,v in vs.items()} for k,vs in out.items()}),flush=True)
