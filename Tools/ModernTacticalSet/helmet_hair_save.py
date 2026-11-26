"""Save two new worn meshes; never rewrite the live helmet or native hair."""
import unreal as u,json,hashlib,importlib.util,gc,math
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1'
DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/HelmetHairFitR1'
BASE=DEST.replace('HelmetHairFitR1','HelmetDetailR1')
spec=importlib.util.spec_from_file_location('helmet_static_buffers',P/'Tools/FieldHat/save_icon.py');io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
receipt={'completed':False,'meshes':{},'hair_assets_modified':False,'runtime_tested':False,'game_installed':False,'content_root':str((R/'StageHost/Content').resolve())}
for rig in ['Jason','Kaitlin']:
    file=R/'Authored'/f'helmet_{rig}_wear.json';d=json.loads(file.read_text(encoding='utf-8'))
    if not all(math.isfinite(x) for p in d['positions'] for x in p) or not all(math.isfinite(x) for f in d['normals'] for p in f for x in p):raise RuntimeError('Non-finite authored mesh: '+rig)
    path=DEST+'/Wear/SM_TS01_Helmet_'+rig
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh and E.get_metadata_tag(mesh,'HelmetRevision')!='HelmetHairFitR1':raise RuntimeError('Unowned staged asset: '+path)
    mats=[u.load_asset(BASE+'/Materials/M_'+n) for n in d['material_slots']]
    if not all(mats):raise RuntimeError('Detailed helmet material missing')
    dm=None;count=3
    if not mesh or E.get_metadata_tag(mesh,'HelmetSourceSHA')!=digest:
        dm=io.dynamic(d)
        if dm.get_triangle_count()!=len(d['triangles']):raise RuntimeError('Geometry import dropped triangles: '+rig)
        if mesh:
            opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'])
            _,status=G.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
        else:
            mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
            if mesh:mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=mat,material_slot_name=slot) for mat,slot in zip(mats,d['material_slots'])])
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+path)
        reduction=u.StaticMeshReductionOptions();reduction.auto_compute_lod_screen_size=False
        reduction.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=r,screen_size=s) for r,s in [(1.,1.),(.7,.18),(.45,.07)]]
        count=sub.set_lods(mesh,reduction)
        if count!=3:raise RuntimeError('Cannot build three LODs for '+rig)
        E.set_metadata_tag(mesh,'HelmetSourceSHA',digest);E.set_metadata_tag(mesh,'HelmetRevision','HelmetHairFitR1')
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+path)
    # The user requested both-head inspection. Capture the actual generated
    # render LOD shells for the scoped static hair-clearance calculation.
    folder=R/'SavedLods';folder.mkdir(exist_ok=True)
    for lod in range(3):
        render,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved helmet LOD '+str(lod))
        Q=u.GeometryScript_MeshQueries;Lists=u.GeometryScript_List
        _,vertices,_=Q.get_all_vertex_positions(render,False);vertices=Lists.convert_vector_list_to_array(vertices)
        _,tris,_=Q.get_all_triangle_indices(render,False);tris=Lists.convert_triangle_list_to_array(tris)
        _,ids,valid=u.GeometryScript_Materials.get_all_triangle_material_i_ds(render);ids=Lists.convert_index_list_to_array(ids)
        if not valid:raise RuntimeError('No shell material IDs in render LOD')
        triangles=[[t.x,t.y,t.z] for t,slot in zip(tris,ids) if slot==0]
        used=sorted({i for tri in triangles for i in tri});index={v:i for i,v in enumerate(used)}
        shell={'asset':mesh.get_path_name(),'lod':lod,'positions':[[vertices[i].x,vertices[i].y,vertices[i].z] for i in used],'triangles':[[index[i] for i in tri] for tri in triangles],'attachment_frame':d['attachment_frame']}
        (folder/f'{rig}_LOD{lod}.json').write_text(json.dumps(shell,separators=(',',':')),encoding='utf-8')
    receipt['meshes'][rig]={'asset':mesh.get_path_name(),'sha256':digest,'lod_count':count}
    (R/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('HELMET_HAIR_FIT_SAVED',rig,flush=True)
    del dm,mesh,d;gc.collect();u.SystemLibrary.collect_garbage()
receipt['completed']=True
(R/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
