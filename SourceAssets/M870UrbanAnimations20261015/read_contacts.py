import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;sys.path.insert(0,str(O))
from read_inputs import smd
clip=smd(O/'Original/870/anims/reloadinsert.smd')
g0=clip['rows'][0]['870_parent']
for f,row in enumerate(clip['rows']):
    print('SOURCE',f,{n:[round(x,4) for x in (row['870_parent'].inverted()@row[n]).translation] for n in ['ValveBiped.Bip01_R_Hand','870_shell2','870_loadingport','870_slide']})
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M870Tactical20261015/M870_Gameplay_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
r.animation_data.action=bpy.data.actions['A_M870_reload_continuous'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(44)
row={n:r.matrix_world@r.pose.bones[n].matrix for n in r.pose.bones.keys()}
shell=next(o for o in s.objects if o.name.startswith('M870_ReloadShell'))
centre=sum((shell.matrix_world@v.co for v in shell.data.vertices),Vector())/len(shell.data.vertices)
rest=r.matrix_world@r.data.bones['WPN_Shell'].matrix_local
centrelocal=rest.inverted()@centre
data=dict(shell_center_local=list(centrelocal),shell_feed_pose=[list(v) for v in row['WPN_root'].inverted()@row['WPN_Shell']],shell_centre_at_feed=list(row['WPN_root'].inverted()@row['WPN_Shell']@centrelocal))
(O/'contacts.json').write_text(json.dumps(data,indent=2))
print('TARGET_SHELL',json.dumps(data))
