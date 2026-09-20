"""Export accepted common bodies and their current material/socket bindings."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;(O/'Sources').mkdir(exist_ok=True)
paths={
'vertical':'/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip',
'tactical_vertical':'/Game/Weapons/TacticalVerticalForegrip20260919/M4/SM_TacticalVerticalForegrip',
'canted':'/Game/Weapons/M4CantedForegrip/SM_CantedForegrip',
'prism':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismHandstop',
'angled':'/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/M4/SM_ResonanceGrip',
'large_drum':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum',
'skeleton':'/Game/Weapons/ReferenceStock5080/SM_SkeletonStock',
'qr_performance':'/Game/Weapons/QRPerformanceStock/Meshy20260913/M4/SM_PerformanceStock',
'core_stock':'/Game/Weapons/CoreStock20260914/Meshy0914005605/M4/SM_CoreStock',
'tactical_telescopic':'/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock',
'phantom_reargrip':'/Game/Weapons/RearGripFinish20260913/M4/phantom/SM_PhantomRearGrip',
'balanced_reargrip':'/Game/Weapons/RearGripFinish20260913/M4/balanced/Seam20260914/SM_BalancedRearGrip',
'stable_antislip_reargrip':'/Game/Weapons/StableAntiSlipRearGrip/Selected91727/M4/SM_StableAntiSlipRearGrip',
'laser':'/Game/Weapons/TacticalDevices20260913/M4/laser/SM_TacticalDevice',
'flashlight':'/Game/Weapons/TacticalDevices20260913/HunyuanV3/M4/flashlight/SM_TacticalDevice',
'tactical_suppressor':'/Game/Weapons/TacticalSuppressor20260913/M4/SM_TacticalSuppressor',
}
for k in ['suppressor','brake','titanium_brake']:paths[k]='/Game/Weapons/M4MuzzlesV1/SM_M4_'+k
for k,n in [('holographic','SM_M4_Holographic'),('panoramic_red_dot','SM_PanoramicRedDot'),('prism_scope_2x','SM_PrismScope2X'),('lpvo_1_6x','SM_LPVO1to6X'),('lpvo_ring','SM_LPVORing')]:paths[k]='/Game/Weapons/AttachmentFinish20260913/M4/Meshes/'+n
result={}
for key,path in paths.items():
 obj=u.load_asset(path)
 if not obj:raise RuntimeError(path)
 task=u.AssetExportTask();task.object=obj;task.filename=str(O/'Sources'/(key+'.fbx'));task.automated=True;task.prompt=False
 task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+key)
 slots=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in obj.static_materials]
 if key=='laser':
  for s in slots:
   if s['slot']=='M_Tactical_laser':s['material']='/Game/Weapons/TacticalDevices20260913/M4/laser/M_M4_laser_Body_OpticalV2'
 if key=='flashlight':
  for s in slots:
   if s['slot']=='M_Tactical_flashlight':s['material']='/Game/Weapons/TacticalDevices20260913/HunyuanV3/M4/flashlight/M_M4_flashlight_Body_MetalTail'
 sockets={}
 for name in ('Emitter','AimGuide'):
  socket=obj.find_socket(name)
  if socket:sockets[name]={'location':list(socket.relative_location.to_tuple()),'rotation':list(socket.relative_rotation.to_tuple())}
 result[key]={'source':path,'fbx':task.filename,'slots':slots,'sockets':sockets}
 (O/'sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('M16_COMMON_SOURCES_EXPORTED')
