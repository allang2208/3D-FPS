"""Fresh-process saved-asset inspection requested with the material upgrade. No render/game."""
import unreal as u,json,hashlib
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/WorkbenchMaterialUnification20261108')
a=json.loads((R/'Receipts/audit.json').read_text(encoding='utf8'))
s=json.loads((R/'material_mapping.json').read_text(encoding='utf8')); E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
report={'meshes':[],'materials':[],'palette':[],'missing_textures':[],'errors':[], 'game_tested':False,'visual_tested':False}
for p in s['target_meshes']:
 mesh=u.load_asset(p)
 if not mesh:report['errors'].append('Missing '+p);continue
 old=a['meshes'][p];current=[x.material_interface.get_path_name() if x.material_interface else None for x in mesh.static_materials]
 expected=[s['mapping'].get(x['material'],x['material']) for x in old['slots']]
 if current!=expected:report['errors'].append('Binding mismatch '+p)
 tris=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]
 if tris!=old['triangles']:report['errors'].append('Geometry mismatch '+p)
 report['meshes'].append({'asset':p,'binding_matches':current==expected,'triangles':tris})
for p in sorted(set(s['mapping'].values())):
 m=u.load_asset(p)
 if not m:report['errors'].append('Missing material '+p);continue
 if E.get_metadata_tag(m,'WorkbenchSurfaceRevision')!=s['revision']:report['errors'].append('Wrong revision '+p)
 report['materials'].append(p)
 if isinstance(m,u.Material):
  for n in L.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionTextureSample) and not n.get_editor_property('texture'):report['missing_textures'].append(p+'/'+n.get_name())
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
for row in palette.components:
 id=str(row.get_editor_property('id'))
 if id in s['palette_ids']:
  surf=row.get_editor_property('surface');path=surf.get_path_name() if surf else None
  if path not in set(s['mapping'].values()):report['errors'].append('Palette mismatch '+id)
  report['palette'].append({'id':id,'surface':path})
report['status']='asset_readback_passed' if not report['errors'] and not report['missing_textures'] else 'failed'
(R/'Receipts/readback.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('WORKBENCH_ASSET_READBACK '+json.dumps({'status':report['status'],'meshes':len(report['meshes']),'materials':len(report['materials']),'errors':report['errors'],'missing_textures':report['missing_textures']}))
if report['status']=='failed':raise RuntimeError('Readback failed; see scoped receipt')
