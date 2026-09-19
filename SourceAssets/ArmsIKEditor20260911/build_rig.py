"""FK source pose plus two-bone positional IK, preserving source bone roll."""
import unreal,json
from pathlib import Path
O=Path(__file__).parent
DEST='/Game/Weapons/M4ArmsIKEditor'
NAME='CR_M4_ArmsIK'
assert not unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+NAME)
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME,DEST,unreal.ControlRigBlueprint,unreal.ControlRigBlueprintFactory())
bp.set_preview_mesh(mesh)
h=bp.hierarchy; hc=bp.get_hierarchy_controller(); hc.import_bones(mesh.skeleton)
c=bp.get_or_create_controller();bp.set_auto_vm_recompile(False)
bones=h.get_bones()
mapping={str(k.name):str(k.name)+'_fk_ctrl' for k in bones}
def key(name):return unreal.RigElementKey(type=unreal.RigElementType.CONTROL,name=name)
for b in bones:
 name=str(b.name); parent=h.get_first_parent(b)
 settings=unreal.RigControlSettings();settings.control_type=unreal.RigControlType.EULER_TRANSFORM
 settings.shape_name='Circle_Thin';settings.shape_color=unreal.LinearColor(.15,.5,1,1) if name.endswith('_l') else unreal.LinearColor(1,.25,.12,1)
 ctrl=hc.add_control(mapping[name],key(mapping[str(parent.name)]) if str(parent.name) in mapping else unreal.RigElementKey(),settings,h.make_control_value_from_euler_transform(unreal.EulerTransform(scale=[1,1,1])))
 h.set_control_offset_transform(ctrl,h.get_local_transform(b,True),True)
 h.set_control_shape_transform(ctrl,unreal.Transform(scale=unreal.Vector(.008,.008,.008)),True)
for side in ['l','r']:
 for name,parent,shape,color in [('hand_'+side+'_ik_ctrl','hand_'+side,'Box_Thin',unreal.LinearColor(0,1,.5,1)),('elbow_'+side+'_pole_ctrl','lowerarm_'+side,'Diamond_Thin',unreal.LinearColor(1,.6,0,1))]:
  s=unreal.RigControlSettings();s.control_type=unreal.RigControlType.EULER_TRANSFORM;s.shape_name=shape;s.shape_color=color
  ctrl=hc.add_control(name,key(mapping[parent]),s,h.make_control_value_from_euler_transform(unreal.EulerTransform(scale=[1,1,1])))
  h.set_control_shape_transform(ctrl,unreal.Transform(scale=unreal.Vector(.035,.035,.035)),True)
def node(struct,name):
 package='RigVM' if struct.startswith('RigVM') else 'ControlRig'
 n=c.add_unit_node_from_struct_path('/Script/'+package+'.'+struct,'Execute',unreal.Vector2D(0,0),name)
 assert n,name
 return n.get_name()
def val(pin,v):assert c.set_pin_default_value(pin,v),pin
def link(a,b):assert c.add_link(a,b),(a,b)
def get(name,typ='Control'):
 n=node('RigUnit_GetTransform','Read_'+name)
 val(n+'.Item',f'(Type={typ},Name="{name}")');return n+'.Transform'
def sub(a,b,name):
 n=node('RigVMFunction_MathVectorSub',name);link(a,n+'.A');link(b,n+'.B');return n+'.Result'
def length(a,name):
 n=node('RigVMFunction_MathVectorLength',name);link(a,n+'.Value');return n+'.Result'
def put(item,typ,source,previous):
 n=node('RigUnit_SetTransform','Set_'+item+'_'+typ)
 val(n+'.Item',f'(Type={typ},Name="{item}")');link(source,n+'.Value');link(previous,n+'.ExecutePin');return n+'.ExecutePin'
forward=node('RigUnit_BeginExecution','Forward')+'.ExecutePin'
backward=node('RigUnit_InverseExecution','Backward')+'.ExecutePin'
for b in bones:
 name=str(b.name)
 forward=put(name,'Bone',get(mapping[name]),forward)
 backward=put(mapping[name],'Control',get(name,'Bone'),backward)
for side in ['l','r']:
 a=get(mapping['upperarm_'+side]); b=get(mapping['lowerarm_'+side]); end=get(mapping['hand_'+side])
 target=get('hand_'+side+'_ik_ctrl');pole=get('elbow_'+side+'_pole_ctrl')
 ab=sub(b+'.Translation',a+'.Translation','OldUpper_'+side)
 bc=sub(end+'.Translation',b+'.Translation','OldLower_'+side)
 solve=node('RigUnit_TwoBoneIKSimpleVectors','SolveArm_'+side)
 link(a+'.Translation',solve+'.Root');link(target+'.Translation',solve+'.Effector');link(pole+'.Translation',solve+'.PoleVector')
 link(length(ab,'UpperLength_'+side),solve+'.BoneALength');link(length(bc,'LowerLength_'+side),solve+'.BoneBLength')
 val(solve+'.bEnableStretch','False')
 for bone,old,oldvec,newvec,pos in [
  ('upperarm_'+side,a,ab,sub(solve+'.Elbow',a+'.Translation','NewUpper_'+side),a+'.Translation'),
  ('lowerarm_'+side,b,bc,sub(solve+'.Effector',solve+'.Elbow','NewLower_'+side),solve+'.Elbow')]:
  delta=node('RigVMFunction_MathQuaternionFromTwoVectors','Delta_'+bone);link(oldvec,delta+'.A');link(newvec,delta+'.B')
  rot=node('RigVMFunction_MathQuaternionMul','Rotate_'+bone);link(delta+'.Result',rot+'.A');link(old+'.Rotation',rot+'.B')
  n=node('RigUnit_SetTransform','IK_'+bone);val(n+'.Item',f'(Type=Bone,Name="{bone}")')
  link(pos,n+'.Value.Translation');link(rot+'.Result',n+'.Value.Rotation');link(old+'.Scale3D',n+'.Value.Scale3D')
  link(forward,n+'.ExecutePin');forward=n+'.ExecutePin'
 n=node('RigUnit_SetTransform','IK_hand_'+side);val(n+'.Item',f'(Type=Bone,Name="hand_{side}")')
 link(solve+'.Effector',n+'.Value.Translation');link(target+'.Rotation',n+'.Value.Rotation');link(end+'.Scale3D',n+'.Value.Scale3D')
 link(forward,n+'.ExecutePin');forward=n+'.ExecutePin'
 # Inverse solve captures the source pose into FK controls; IK offsets become zero.
 for ctrl in ['hand_'+side+'_ik_ctrl','elbow_'+side+'_pole_ctrl']:
  n=node('RigUnit_SetTransform','Reset_'+ctrl);val(n+'.Item',f'(Type=Control,Name="{ctrl}")');val(n+'.Space','LocalSpace')
  link(backward,n+'.ExecutePin');backward=n+'.ExecutePin'
bp.set_auto_vm_recompile(True);bp.recompile_vm()
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
(O/'rig_build.json').write_text(json.dumps({'rig':bp.get_path_name(),'mapping':mapping,'bones':len(bones),'nodes':len(bp.get_model().get_nodes())},indent=2))
unreal.log('ARMS_IK_RIG_BUILD_READY')
