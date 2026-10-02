"""Extract the accepted refined M4 grip as magazine-relative authoring data."""
import bpy,json,sys
import numpy as np
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];S=P/'SourceAssets/M4M16ReloadGripFix20260925'
C=np.diag([100.,-100.,100.,1.])
out={}
for kind,ref in (('reload',76),('reload_empty',80),('old_reload',8),('old_reload_empty',8)):
 old=kind.startswith('old_');k=kind.removeprefix('old_')
 source=P/'SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend' if old else S/('M4Animations/A_M4_ExtContact_'+kind+'.blend')
 bpy.ops.wm.open_mainfile(filepath=str(source))
 rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
 rig.animation_data.action=bpy.data.actions['M4_MAT_'+k if old else 'A_M4_ExtContact_'+kind+'_GripPrecise']
 bpy.context.scene.frame_set(ref);bpy.context.view_layer.update()
 names=[b.name for b in rig.data.bones if b.name.endswith('_l') and b.name.startswith(('hand','thumb','index','middle','ring','pinky'))]
 deform={n:(C@np.array(rig.matrix_world@rig.pose.bones[n].matrix)@np.linalg.inv(np.array(rig.matrix_world@rig.data.bones[n].matrix_local))@np.linalg.inv(C)).tolist() for n in names}
 mr=rig.matrix_world@rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
 mp=rig.matrix_world@rig.pose.bones['WPN_SOCKET_Magazine'].matrix
 D=C@np.array(mp)@np.linalg.inv(np.array(mr))@np.linalg.inv(C)
 mag=bpy.data.objects['M4_Magazine Light.003_Export'];verts=[]
 group=mag.vertex_groups['WPN_SOCKET_Magazine'].index
 for v in mag.data.vertices:
  if sum(g.weight for g in v.groups if g.group==group)>.5:verts.append((C@np.array([*(mag.matrix_world@v.co),1.]))[:3].tolist())
 root=np.array(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local)
 up=(C[:3,:3]@root[:3,2]);up=up/np.linalg.norm(up)
 out[kind]={'frame':ref,'deform':deform,'mag_deform':D.tolist(),'shell':verts,'up':up.tolist()}
(O/'donor.json').write_text(json.dumps(out,separators=(',',':')))
print('HK416_ACCEPTED_M4_GRIP_SOURCE',list(out),flush=True)
