"""Import, build and save the revised assets in a background UE commandlet."""
import hashlib
import json
import re
import sys
from pathlib import Path
_current = Path(__file__).resolve().parents[3] / 'SourceAssets/CyberpunkApartmentRebuild20261022'
if (_current / 'installed.json').exists():
    import runpy
    runpy.run_path(str(_current / 'import_assets.py'), run_name='__main__')
    raise SystemExit(0)
sys.path.insert(0, str(Path(__file__).parent))
from playable_config import ROOT, DEST, COMPLEX
import unreal as u

E=u.EditorAssetLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
src=ROOT/'export/CyberpunkApartmentPlayable.gltf'
digest=hashlib.sha256(src.read_bytes()+(ROOT/'export/CyberpunkApartmentPlayable.bin').read_bytes()).hexdigest()
out=ROOT/'import_saved.json'
report={'source_sha256':digest,'stage':'importing','meshes':{},'errors':[]}
def persist():out.write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(asset):
    asset.modify()
    if not E.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed: '+asset.get_path_name())

try:
    previous=json.loads(out.read_text()) if out.exists() else {}
    if previous.get('source_sha256')==digest and previous.get('import_completed'):
        report=previous
    else:
        task=u.AssetImportTask()
        task.filename=str(src)
        task.destination_path=DEST
        task.automated=True
        task.replace_existing=True
        task.save=True
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        report['imported_paths']=[str(x) for x in task.imported_object_paths]
        if not report['imported_paths']:raise RuntimeError('Import returned no assets')
        report['import_completed']=True
        persist()
    paths=E.list_assets(DEST, recursive=True, include_folder=False)
    meshes={}
    for path in paths:
        if '/StaticMeshes/' not in path:continue
        mesh=E.load_asset(path)
        if isinstance(mesh,u.StaticMesh):meshes[mesh.get_name()]=mesh
    authored=json.loads((ROOT/'authoring.json').read_text())
    source_gltf=json.loads(src.read_text())
    transparent={m['name'] for m in source_gltf['materials'] if m.get('alphaMode','OPAQUE')!='OPAQUE'
                 or 'KHR_materials_transmission' in m.get('extensions',{})}
    for row in authored['meshes']:
        name=re.sub(r'[^\w\-]', '_', row['name'])
        mesh=meshes.get(name)
        if not mesh:raise RuntimeError('Missing imported mesh '+name)
        if name in report['meshes']:continue
        mesh.modify()
        body=mesh.get_editor_property('body_setup')
        if not body:raise RuntimeError('No BodySetup '+name)
        SM.remove_collisions(mesh)
        if name.startswith('DoorAsset_') and name.endswith('_Leaf'):
            SM.add_simple_collisions(mesh,u.ScriptingCollisionShapeType.BOX)
            flag=u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX
            collision='simple box'
        elif name in COMPLEX or name.endswith('_Frame'):
            flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            collision='complex geometry; no enclosing convex hull'
        else:
            flag=u.CollisionTraceFlag.CTF_USE_DEFAULT
            collision='disabled at component'
        body.set_editor_property('collision_trace_flag',flag)
        body.set_editor_property('double_sided_geometry',True)
        settings=mesh.get_editor_property('nanite_settings').copy()
        translucent=bool(set(row['materials']) & transparent)
        use_nanite=row['triangles']>=10000 and not translucent and not name.startswith('DoorAsset_')
        settings.enabled=use_nanite
        if use_nanite:
            settings.explicit_tangents=True
            settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
            settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
            settings.fallback_percent_triangles=1.0
            settings.fallback_relative_error=0.0
        mesh.set_editor_property('nanite_settings',settings)
        if use_nanite and not u.PlazaInstanceTools.build_nanite_data(mesh):
            raise RuntimeError('Nanite build failed '+name)
        # Keep near geometry intact; mixed transparent furniture remains on the
        # raster path, with conservative distance LODs (no collision LOD change).
        if not use_nanite and row['triangles']>=15000 and not name.startswith('DoorAsset_'):
            opt=u.StaticMeshReductionOptions()
            opt.auto_compute_lod_screen_size=False
            opt.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s)
                                    for p,s in ((1.,1.),(.65,.10),(.35,.035))]
            SM.set_lods(mesh,opt)
        slots=mesh.get_editor_property('static_materials')
        if not slots or any(s.material_interface is None for s in slots):
            raise RuntimeError('Missing material slot '+name)
        save(mesh)
        report['meshes'][name]={'path':mesh.get_path_name(),'collision':collision,
            'nanite':use_nanite,'transparent':translucent,'lods':SM.get_lod_count(mesh),
            'source_triangles':row['triangles'],'material_slots':len(slots)}
        report['stage']='configuring'
        persist()
    # Nanite builds may set material usage. Save only this revision's dependencies.
    for path in paths:
        if '/Materials/' in path:
            save(E.load_asset(path))
    report['stage']='assets_saved'
    report['errors']=[]
except Exception as exc:
    report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['stage']='failed'
    persist()
    raise
persist()
u.log('CYBERPUNK_PLAYABLE_ASSETS_SAVED '+str(len(report['meshes'])))
