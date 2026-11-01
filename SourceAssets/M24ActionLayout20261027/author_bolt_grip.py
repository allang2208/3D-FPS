"""Fit the larger V9 palm to the measured bolt knob, keeping all mechanical clocks."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;X=O/'Exports/Animations';X.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24Hold20261027/M24_Hold_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
tree=ast.parse((O.parent/'M24CustomScope20261026/author_gameplay.py').read_text())
for name in ('under','twists'):
    exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
report={'clips':{},'basis_unchanged':True,'offset_at_fire_frame_28_m':[.030,-.012,.025]}
hold_tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text())
exec(compile(ast.unparse(next(n for n in hold_tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')),'dense_bake','exec'))
def sample(role):
    a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    rows=[]
    for f in range(round(a.frame_range[1])+1):
        s.frame_set(f);bpy.context.view_layer.update();rows.append({b.name:b.matrix.copy() for b in r.pose.bones})
    return rows
clips={role:sample(role) for role in ('fire','reload_empty','cycle')}
reference=clips['fire'][28]
local_offset=reference['WPN_BoltHandle'].to_quaternion().inverted()@(reference['WPN_root'].to_quaternion()@Vector(report['offset_at_fire_frame_28_m']))
def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def move_right(row,delta):
    old={n:m.copy() for n,m in row.items()};u,l,h='upperarm_r','lowerarm_r','hand_r'
    shoulder=old[u].translation.copy();elbow=old[l].translation;wrist=old[h].translation;goal=wrist+delta
    a=(elbow-shoulder).length;b=(wrist-elbow).length;axis=goal-shoulder
    reach=.985*(a+b)
    if axis.length>reach:shoulder+=axis.normalized()*(axis.length-reach)
    axis=goal-shoulder;d=max(axis.length,abs(a-b)+1.e-6);axis.normalize()
    pole=elbow-shoulder;pole-=axis*pole.dot(axis);pole.normalize()
    along=(a*a-b*b+d*d)/(2*d);ep=shoulder+axis*along+pole*math.sqrt(max(0,a*a-along*along))
    uq=(elbow-old[u].translation).rotation_difference(ep-shoulder)@old[u].to_quaternion()
    lq=(wrist-elbow).rotation_difference(goal-ep)@old[l].to_quaternion()
    um=Matrix.LocRotScale(shoulder,uq,Vector((1,1,1)));lm=Matrix.LocRotScale(ep,lq,Vector((1,1,1)))
    D=Matrix.Translation(delta)
    for n in row:
        if under(n,h):row[n]=D@old[n]
        elif under(n,l):row[n]=lm@old[l].inverted()@old[n]
        elif under(n,u):row[n]=um@old[u].inverted()@old[n]
    row['clavicle_r'].translation+=shoulder-old[u].translation
for role,rows in clips.items():
    shift={'fire':0,'reload_empty':52,'cycle':4}[role]
    for f,row in enumerate(rows):
        t=f-shift;w=ease((t-10)/6)*(1-ease((t-39)/8))
        if w>0:move_right(row,row['WPN_BoltHandle'].to_quaternion()@local_offset*w)
    a=bpy.data.actions['A_M24_'+role];r.animation_data.action=None;bpy.data.actions.remove(a)
    bake(role,rows);a=r.animation_data.action
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    path=X/('A_M24_'+role+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    report['clips'][role]['file']=str(path)
r.animation_data.action=bpy.data.actions['A_M24_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ActionLayout_Editable.blend'))
(O/'grip_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_BOLT_GRIP_EXPORTED',flush=True)
