"""Read current weapon/attachment materials for the requested finish review."""
import unreal as u
import json, ast
from pathlib import Path
O=Path(__file__).parent
S=O.parent
L=u.MaterialEditingLibrary
tree=ast.parse((S/'QBZ191Attachments20260913/export_sources.py').read_text())
m4=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='paths' for t in n.targets)))
m4['reargrip']='/Game/Weapons/PhantomRearGrip/M4/SM_PhantomRearGrip'
akm={}
for key in m4:
 if key in ['vertical','canted','angled']:
  p='/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_'+key+('_CompactMount' if key=='canted' else '')
 elif key in ['drum','prism','suppressor','brake','titanium_brake']:
  p='/Game/Weapons/AKMIntegration/SovietFab/Attachments/SM_AKM_'+key
 elif key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']:
  p='/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/'+{'holographic':'SM_AKM_optic','panoramic_red_dot':'SM_PanoramicRedDot','prism_scope_2x':'SM_PrismScope2X','lpvo_1_6x':'SM_LPVO1to6X','lpvo_ring':'SM_LPVORing'}[key]
 elif key=='skeleton':p='/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock'
 elif key=='qr_performance':p='/Game/Weapons/QRPerformanceStock/AKM/SM_QRPerformanceStock'
 else:p='/Game/Weapons/PhantomRearGrip/AKM/SM_PhantomRearGrip'
 akm[key]=p
for key in ['panoramic_red_dot','prism_scope_2x','lpvo_1_6x']:
 akm['mount_'+key]='/Game/Weapons/AKMIntegration/SovietFab/Optics/SM_AKM_Mount_'+key
rifles={'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
        'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
        'QBZ191':'/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny'}
materials={};textures={};report={'rifles':{},'parts':{},'materials':materials,'textures':textures}
def serial(v):
 if isinstance(v,u.Object):return v.get_path_name()
 if isinstance(v,u.LinearColor):return [v.r,v.g,v.b,v.a]
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 return str(v)
def texture(t):
 if not t or t.get_path_name() in textures:return
 d={'srgb':t.get_editor_property('srgb'),'compression':str(t.get_editor_property('compression_settings'))}
 try:d['sources']=list(t.get_editor_property('asset_import_data').extract_filenames())
 except Exception:d['sources']=[]
 textures[t.get_path_name()]=d
def material(m):
 p=m.get_path_name()
 if p in materials:return p
 base=m.get_base_material();d={'class':m.get_class().get_name(),'base':base.get_path_name(),'parameters':{},'expressions':[]};materials[p]=d
 for kind in ['scalar','vector','texture','static_switch']:
  values={}
  for name in getattr(L,'get_'+kind+'_parameter_names')(base):
   method='get_material_instance_' if isinstance(m,u.MaterialInstanceConstant) else 'get_material_default_'
   v=getattr(L,method+kind+'_parameter_value')(m,name);values[str(name)]=serial(v)
   if kind=='texture':texture(v)
  d['parameters'][kind]=values
 for n in L.get_material_expressions(base):
  e={'class':n.get_class().get_name(),'name':n.get_name()}
  for prop in ['texture','coordinate_index','parameter_name','default_value','r','constant','const_a','const_b','const_alpha']:
   try:
    v=n.get_editor_property(prop);e[prop]=serial(v)
    if prop=='texture':texture(v)
   except Exception:pass
  d['expressions'].append(e)
 d['outputs']={str(prop):serial(L.get_material_property_input_node(base,prop)) for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_NORMAL]}
 return p
def slots(mesh):
 return [{'slot':str(s.material_slot_name),'material':material(s.material_interface)} for s in (mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials)]
for family,path in rifles.items():
 mesh=u.load_asset(path)
 if not mesh and family=='AKM':path='/Game/Weapons/AKMIntegration/SovietFab/StockV2/SK_AKM_MannyNative';mesh=u.load_asset(path)
 if not mesh and family=='QBZ191':path='/Game/Weapons/QBZ191/Attachments20260913/SK_QBZ191_Manny';mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 report['rifles'][family]={'path':path,'slots':slots(mesh)}
for family,parts in [('M4',m4),('AKM',akm),('QBZ191',{'reargrip':'/Game/Weapons/PhantomRearGrip/QBZ191/SM_PhantomRearGrip'})]:
 report['parts'][family]={}
 for key,path in parts.items():
  mesh=u.load_asset(path)
  if not mesh:
   report['parts'][family][key]={'path':path,'missing':True}
   continue
  report['parts'][family][key]={'path':path,'slots':slots(mesh),'triangles':mesh.get_num_triangles(0)}
  (O/'before.json').write_text(json.dumps(report,indent=2))
(O/'before.json').write_text(json.dumps(report,indent=2))
u.log('WEAPON_FINISH_REVIEW_COMPLETE')
