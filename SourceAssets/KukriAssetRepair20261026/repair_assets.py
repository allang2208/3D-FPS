"""Rebuild the twelve upgraded Kukri mesh packages from their persistent authoring FBX."""
import sys,json,shutil
from pathlib import Path
from datetime import datetime
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriAssetRepair20261026')
sys.path.insert(0,str(P))
from kukri_mesh_import import import_mesh,require_authoring_context
require_authoring_context()
blades=json.loads((P.parent/'KukriBladeSurfaceV220261026/surfaces.json').read_text(encoding='utf-8'))['variants']
parts=json.loads((P.parent/'KukriComponentVariants20261026/components.json').read_text(encoding='utf-8'))['variants']
targets={e['mesh'].split('.')[0] for e in blades+parts}
conflicts=targets.intersection(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if conflicts:raise RuntimeError('Unsaved target packages: '+', '.join(sorted(conflicts)))
receipt={'complete':False,'started':datetime.now().astimezone().isoformat(),'saved_assets':[],
         'numeric_changes':False,'runtime_tested':False,'meshes':[],
         'authoring_project_directory':u.Paths.convert_relative_path_to_full(u.Paths.project_dir()),
         'published_to_game':Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()==P.parents[1].resolve()}
def record():(P/'repair-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'Before').mkdir(exist_ok=True)
for entry in blades+parts:
    print('KUKRI_REPAIR_IMPORT '+entry['object'],flush=True)
    package=entry['mesh'].split('.')[0]
    source=P.parents[1]/'Content'/(package.removeprefix('/Game/')+'.uasset')
    backup=P/'Before'/source.name
    if not backup.exists():shutil.copy2(source,backup)
    material=u.load_asset(entry['material'])
    if not material:raise RuntimeError('Required baked material missing: '+entry['material'])
    mesh=import_mesh(entry['fbx'],package,material)
    print('KUKRI_REPAIR_SAVE '+entry['object'],flush=True)
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Mesh save failed: '+package)
    receipt['saved_assets'].append(mesh.get_path_name())
    receipt['meshes'].append({'asset':mesh.get_path_name(),'fbx':entry['fbx'],'material':material.get_path_name(),
        'source_description':mesh.get_static_mesh_description(0).get_path_name(),'triangles':mesh.get_num_triangles(0),
        'lods':mesh.get_num_lods(),'uv_channels':mesh.get_num_tex_coords(0),'sections':mesh.get_num_sections(0)})
    record()
receipt['complete']=True;record()
print('KUKRI_PERSISTENT_MESH_REPAIR_SAVED '+str(len(receipt['saved_assets'])))
