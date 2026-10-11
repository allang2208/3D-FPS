"""Patch only the authored left-elbow surface, preserving current gun assets."""
import json,itertools
import unreal as u
PATHS=[
    '/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',
    '/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7']
def apply(directory,load,backup,save,receipt):
    patch=json.loads((directory/'bind_surface.json').read_text())
    G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
    edits=patch['edits'];prepared=[]
    def native(p):return (100*p[0],-100*p[1],100*p[2])
    def key(p):return tuple(round(x/.01) for x in p)
    buckets={}
    for e in edits:buckets.setdefault(key(native(e['before'])),[]).append(e)
    for path in PATHS:
        asset=load(path)
        if u.EditorAssetLibrary.get_metadata_tag(asset,'Super90R23LeftElbowSurface')=='20261010':continue
        dm,result=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native source LOD '+path)
        _,points,_=Q.get_all_vertex_positions(dm,False);points=u.GeometryScript_List.convert_vector_list_to_array(points)
        changes=[];found=set()
        for i,p in enumerate(points):
            point=(p.x,p.y,p.z);k=key(point);near=[]
            for d in itertools.product((-1,0,1),repeat=3):near.extend(buckets.get(tuple(k[j]+d[j] for j in range(3)),()))
            for e in near:
                old=native(e['before'])
                if sum((old[j]-point[j])**2 for j in range(3))<.000025:
                    changes.append((i,native(e['after'])));found.add(e['index']);break
        if len(found)!=len(edits):raise RuntimeError('Native left elbow differs; preserve '+path+'; matched '+str(len(found))+'/'+str(len(edits)))
        prepared.append((path,asset,dm,changes))
    for path,asset,dm,changes in prepared:
        backup(path)
        for index,point in changes:
            _,valid=u.GeometryScript_MeshEdits.set_vertex_position(dm,index,u.Vector(*point),True)
            if not valid:raise RuntimeError('Cannot write elbow vertex '+path)
        _,selection=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,[i for i,p in changes],u.GeometryScriptMeshSelectionType.VERTICES)
        u.GeometryScript_Normals.recompute_normals_for_mesh_selection(dm,selection,u.GeometryScriptCalculateNormalsOptions())
        options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,enable_recompute_normals=False,enable_recompute_tangents=False,
            bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
        _,result=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot persist left elbow '+path)
        subsystem=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);count=subsystem.get_lod_count(asset)
        if count>1 and not subsystem.regenerate_lod(asset,count,True,False):raise RuntimeError('Cannot rebuild existing elbow LODs '+path)
        u.EditorAssetLibrary.set_metadata_tag(asset,'Super90R23LeftElbowSurface','20261010')
        save(asset);receipt.setdefault('left_elbow_surface',{})[path]={'vertices':len(changes),'max_displacement_mm':patch['max_displacement_mm']}
