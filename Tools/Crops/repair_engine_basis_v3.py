"""Localize UE-invalid LOD shading corners; keep geometry, UVs and original V3."""
import hashlib
import json
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[2]/'SourceAssets/CropsV3_20261022'
source_audit=json.loads((ROOT/'Receipts/fbx-derived-audit.json').read_text())
by_file={r['file']:r for r in source_audit['meshes']}
errors=json.loads((ROOT/'Receipts/ue-render-basis.json').read_text())['errors']
manifest=json.loads((ROOT/'Source/variant_manifest.json').read_text())
out=ROOT/'EngineBasis/Models';out.mkdir(parents=True,exist_ok=True)
repairs=[];plan={}
for error in errors:
    assert error['lod'] in (1,2)
    filename=error['id']+'_LOD'+str(error['lod'])+'.fbx'
    source=ROOT/by_file[filename]['read_path']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');mesh=obj.data
    positions=np.array([obj.matrix_world@v.co for v in mesh.vertices])
    bad_vertices=set()
    for x,y,z in error['invalid_vertices_cm']:
        target=np.array([x/100,-y/100,z/100])
        dist=np.linalg.norm(positions-target,axis=1)
        matches=np.where(dist<5e-6)[0]
        assert len(matches)>0,(filename,target,float(dist.min()))
        bad_vertices.update(int(i) for i in matches)
    normals=[n.vector.copy() for n in mesh.corner_normals]
    bad_faces=[p for p in mesh.polygons if any(v in bad_vertices for v in p.vertices)]
    for polygon in bad_faces:
        polygon.use_smooth=False
        for loop in polygon.loop_indices:normals[loop]=polygon.normal.copy()
    mesh.normals_split_custom_set(normals)
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    assert all(v.vector.length>.5 for v in mesh.corner_normals),filename
    assert all(v.tangent.length>.5 for v in mesh.loops),filename
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    target=out/filename
    bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'MESH'},
        use_mesh_modifiers=False,bake_anim=False,add_leaf_bones=False,
        axis_forward='-Z',axis_up='Y',apply_unit_scale=True,mesh_smooth_type='FACE',
        use_tspace=True,path_mode='RELATIVE')
    repairs.append({'file':filename,'source':str(source.relative_to(ROOT)),
        'affected_vertices':len(bad_vertices),'affected_faces':len(bad_faces),
        'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'derived_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'repair':'Flat split normals on faces incident to UE-invalid vertices; explicit smoothing groups and tangent export. Geometry and UV unchanged.'})
    if error['id'] not in plan:
        asset=next(a for a in manifest['assets'] if a['id']==error['id'])
        signature=hashlib.sha256(''.join(by_file[Path(asset[k]).name]['sha256'] for k in ('mesh_file','lod1_file','lod2_file')).encode()).hexdigest()
        plan[error['id']]={'previous_source_signature':signature,'lods':[]}
    plan[error['id']]['lods'].append(error['lod'])
(ROOT/'Receipts/engine-basis-repairs.json').write_text(json.dumps(repairs,indent=2))
(ROOT/'Receipts/lod-refresh-plan.json').write_text(json.dumps(plan,indent=2))
print('CROPS_ENGINE_BASIS_REPAIR',len(repairs),'LODs',len(plan),'assets')
