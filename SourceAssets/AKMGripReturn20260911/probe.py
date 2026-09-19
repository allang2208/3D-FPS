import bpy,json
from pathlib import Path
O=Path(__file__).parent;B=O.parent/'AKMAttachments20260911';out={}
for clip,end in [('reload',400),('reload_empty',515)]:
 bpy.ops.wm.open_mainfile(filepath=str(B/'AKM_Attachments_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 def at(a,f):
  r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);return r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['hand_l'].matrix
 idle=at(bpy.data.actions['AKM_Native_idle'],0);rows=[]
 for f in range(140,end+1,10):
  h=at(bpy.data.actions['AKM_Native_'+clip],f);rows.append([f,round((h.translation-idle.translation).length,4),list(h.translation)])
 out[clip]=rows
(O/'before.json').write_text(json.dumps(out,indent=2));print('RETURN_PROBE_PASS')
