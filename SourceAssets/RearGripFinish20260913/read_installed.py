"""Requested, scoped material binding and PBR channel readback; no gameplay run."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
source=(O/'read_materials.py').read_text()
exec(source[:source.index('for family,path in rifles.items():')])
installed=json.loads((O/'installed.json').read_text())
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.StaticMeshEditorSubsystem()
for key,info in installed.items():
 mesh=u.load_asset(info['mesh'])
 if not mesh:raise RuntimeError(info['mesh'])
 actual=slots(mesh)
 report['parts'][key]={'path':mesh.get_path_name(),'slots':actual,'uv_channels':sub.get_num_uv_channels(mesh,0),'reference':u.EditorAssetLibrary.get_metadata_tag(mesh,'WeaponFinishReference')}
 report['parts'][key]['has_vertex_colors']=sub.has_vertex_colors(mesh)
 if not report['parts'][key]['has_vertex_colors']:raise RuntimeError('Missing imported region colors: '+key)
 if report['parts'][key]['uv_channels']!=2:raise RuntimeError('Expected original and coating UV: '+key)
 for slot in actual:
  if '/RearGripFinish20260913/'+key.split('_')[0]+'/' not in slot['material']:raise RuntimeError('Wrong rifle material '+key)
  m=u.load_asset(slot['material']);expr=L.get_material_expressions(m.get_base_material())
  if not any(isinstance(n,u.MaterialExpressionTextureCoordinate) and n.coordinate_index==1 for n in expr):raise RuntimeError('Missing coating UV '+key)
  if 'Collar' not in slot['slot'] and not any(isinstance(n,u.MaterialExpressionVertexColor) for n in expr):raise RuntimeError('Missing polymer protection mask '+key)
for family,path in rifles.items():
 mesh=u.load_asset(path)
 report['rifles'][family]={'path':path,'slots':slots(mesh)}
(O/'after.json').write_text(json.dumps(report,indent=2))
u.log('REAR_GRIP_MATERIAL_READBACK_COMPLETE')

