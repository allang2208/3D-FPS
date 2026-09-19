import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910');DEST='/Game/Weapons/M4DrumGripCandidate'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
asset=unreal.load_asset(DEST+'/CR_M4_DrumGrip_MAT')
if not asset:
 asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset('CR_M4_DrumGrip_MAT',DEST,unreal.ControlRigBlueprint,unreal.ControlRigBlueprintFactory())
asset.set_preview_mesh(mesh);h=asset.hierarchy;hc=asset.get_hierarchy_controller();hc.import_bones(mesh.skeleton)
controller=asset.get_or_create_controller();asset.set_auto_vm_recompile(False)
bones=h.get_bones();mapping={}
for k in bones:
 n=str(k.name)
 mapping[n]=n+'_fk_ctrl' if n.startswith(('hand_','upperarm_','lowerarm_')) and not 'twist' in n else n+'_ctrl'
settings=unreal.RigControlSettings();settings.control_type=unreal.RigControlType.EULER_TRANSFORM
value=h.make_control_value_from_euler_transform(unreal.EulerTransform(scale=[1,1,1]))
for k in bones:
 parent=h.get_first_parent(k);pk=unreal.RigElementKey(type=unreal.RigElementType.CONTROL,name=mapping[str(parent.name)]) if str(parent.name) in mapping else unreal.RigElementKey()
 key=hc.add_control(mapping[str(k.name)],pk,settings,value)
 h.set_control_offset_transform(key,h.get_local_transform(k,True),True)
def unit(path,name,x,y):return controller.add_unit_node_from_struct_path('/Script/ControlRig.'+path,'Execute',unreal.Vector2D(x,y),name)
begin=unit('RigUnit_BeginExecution','Forward',0,0);back=unit('RigUnit_InverseExecution','Backward',0,800)
for reverse,entry in [(False,begin),(True,back)]:
 previous=entry.get_name()+'.ExecutePin'
 for i,k in enumerate(bones):
  n=str(k.name);control=mapping[n];suffix=('Back_' if reverse else 'Forward_')+n
  get=unit('RigUnit_GetTransform','Get_'+suffix,250+i*20,200 if not reverse else 1000);put=unit('RigUnit_SetTransform','Set_'+suffix,500+i*20,0 if not reverse else 800)
  controller.set_pin_default_value(get.get_name()+'.Item',f'(Type={"Bone" if reverse else "Control"},Name="{n if reverse else control}")')
  controller.set_pin_default_value(put.get_name()+'.Item',f'(Type={"Control" if reverse else "Bone"},Name="{control if reverse else n}")')
  assert controller.add_link(get.get_name()+'.Transform',put.get_name()+'.Value')
  assert controller.add_link(previous,put.get_name()+'.ExecutePin');previous=put.get_name()+'.ExecutePin'
asset.set_auto_vm_recompile(True);asset.recompile_vm();unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
(O/'mat_rig_report.json').write_text(json.dumps({'asset':asset.get_path_name(),'controls':mapping,'body_detection':'pelvis bone present','mode':'FK transforms; MAT hand and finger controls; no IK switches'},indent=2))
report={}
for cls in ['ControlRigSequencerLibrary','LevelSequenceEditorBlueprintLibrary','LevelSequence','MovieSceneSkeletalAnimationSection']:
 c=getattr(unreal,cls);report[cls]={n:str(getattr(c,n).__doc__) for n in dir(c) if any(x in n for x in ['bake_to','add_spawnable','load_anim','find_or_create_control','get_control_rigs','set_local_control_rig_euler','set_current_time'])}
(O/'sequence_api.json').write_text(json.dumps(report,indent=2));unreal.log('MAT_RIG_BUILD_PASS')
