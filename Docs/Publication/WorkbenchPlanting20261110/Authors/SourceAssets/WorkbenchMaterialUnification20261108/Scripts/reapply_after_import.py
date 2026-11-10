"""Required final material-binding step after future mesh reimports.
Only the explicitly registered workbench packages are writable. Run against FPSGAME,
not isolated historical import hosts. Does not import, rebuild, or alter geometry.
"""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/WorkbenchMaterialUnification20261108')
def apply(paths=None, update_palette=True):
 data=json.loads((R/'material_mapping.json').read_text(encoding='utf8'))
 allowed=set(data['target_meshes']); targets=allowed if paths is None else set(paths)
 if not targets <= allowed:raise RuntimeError('Unregistered material reapply target')
 if Path(u.Paths.project_dir()).resolve()!=R.parents[1].resolve():raise RuntimeError('Apply after installing into FPSGAME; preserve isolated import hosts')
 E=u.EditorAssetLibrary;mapping=data['mapping'];loaded={}
 for path in set(mapping.values()):
  mat=u.load_asset(path)
  if not mat or E.get_metadata_tag(mat,'WorkbenchSurfaceRevision')!=data['revision']:raise RuntimeError('Unified material unavailable: '+path)
  loaded[path]=mat
 report={'changed':[],'palette':[], 'tests_run':False,'renders_run':False}
 for path in sorted(targets):
  mesh=u.load_asset(path)
  if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Missing mesh '+path)
  changes=[]
  for i,slot in enumerate(mesh.static_materials):
   old=slot.material_interface.get_path_name() if slot.material_interface else None
   if old in mapping:mesh.set_material(i,loaded[mapping[old]]);changes.append(i)
  if changes:
   if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
   report['changed'].append({'mesh':path,'slots':changes})
 if update_palette:
  palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette');rows=list(palette.components)
  for row in rows:
   id=str(row.get_editor_property('id'))
   if id in data['palette_ids']:
    mat=row.get_editor_property('surface');old=mat.get_path_name() if mat else None
    if old in mapping:row.set_editor_property('surface',loaded[mapping[old]]);report['palette'].append(id)
  if report['palette']:
   palette.modify();palette.set_editor_property('components',rows)
   if not E.save_loaded_asset(palette,False):raise RuntimeError('Palette save failed')
 (R/'Receipts/reapply.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 return report
if __name__=='__main__':print(json.dumps(apply()))
