"""Save item-specific exposed skin without touching shared naked hand assets."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';ROOT=R/'SkinCoverage'
DEST='/Game/Characters/ModularOutfit20260924/FingerlessHuntV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
def save(asset):
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):raise RuntimeError('Cannot save '+asset.get_path_name())
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world and ('UEDPIE' in world.get_name() or 'PIE_' in world.get_name()):raise RuntimeError('End PIE before saving glove assets')
published={};saved_count=0;receipts=ROOT/'Saved';receipts.mkdir(exist_ok=True)
for entry in json.loads((ROOT/'manifest.json').read_text()):
    name=entry['profile'];raw=(ROOT/(name+'_review.json')).read_bytes();d=json.loads(raw)
    glove_raw=(R/'Authored'/(name+'.json')).read_bytes();glove=json.loads(glove_raw)
    sha=hashlib.sha256(raw+glove_raw+(b'CoupledAssemblyWeld3OriginalWrist' if name=='PKM' else b'CoupledAssemblyWeld1')).hexdigest();receipt=receipts/(name+'.json')
    if receipt.exists():
        before=json.loads(receipt.read_text())
        if before['sha256']==sha and E.does_asset_exist(before['mesh']):published[name]=before['mesh'];continue
    if globals().get('MAX_SAVES',0) and saved_count>=MAX_SAVES:continue
    source=u.load_asset(d['source'])
    source_materials=source.get_editor_property('materials');leather_index=len(source_materials);start=len(d['positions'])
    d['positions'].extend(glove['positions']);d['weights'].extend(glove['weights'])
    d['triangles'].extend([[v+start for v in f] for f in glove['triangles']]);d['normals'].extend(glove['normals'])
    d['triangle_materials'].extend([leather_index]*len(glove['triangles']));d['colors'].extend([[[0,0,0,1]]*3 for _ in glove['triangles']])
    for key in [k for k in d if k.startswith('uv')]:d[key].extend(glove.get(key,[[[0,0]]*3 for _ in glove['triangles']]))
    native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read skin binding '+name)
    _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
    vertices=[];normals=[];colors=[];weights=[];triangles=[];lookup={}
    channels=['uv']+sorted((k for k in d if k.startswith('uv') and k!='uv'),key=lambda k:int(k[2:]));uvs={k:[] for k in channels}
    for fi,face in enumerate(d['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            normal=d['normals'][fi][ci];col=d['colors'][fi][ci];coords=[d[k][fi][ci] for k in channels]
            key=(vi,d['triangle_materials'][fi],*[round(v,7) for values in [normal,col,*coords] for v in values])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*normal));colors.append(u.LinearColor(*col));weights.append(d['weights'][vi])
                for k,uv in zip(channels,coords):uvs[k].append(u.Vector2D(*uv))
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    params={('uv0' if k=='uv' else k):v for k,v in uvs.items()}
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,vertex_colors=colors,triangles=triangles,**params),0,True)
    if dm.get_triangle_count()!=len(triangles):raise RuntimeError('Rejected skin triangles '+name)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for i,w in enumerate(weights):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=v) for n,v in w.items()])
    for i,mat in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,mat,True)
    # A single connected skin/leather surface is simplified once, preserving
    # the same seam at every LOD instead of reducing two separate boundaries.
    u.GeometryScript_MeshRepair.weld_mesh_edges(dm,u.GeometryScriptWeldEdgesOptions(tolerance=.00001,only_unique_pairs=True))
    folder=DEST+'/'+name;assetname='SK_'+name+'_FingerlessSkin';E.make_directory(folder);mesh=u.load_asset(folder+'/'+assetname)
    if not mesh:mesh=A.duplicate_asset(assetname,folder,source)
    materials=source_materials;leather=u.load_asset(DEST+'/Materials/M_FingerlessHunt_Brown')
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[m.material_interface for m in materials]+[leather],new_material_slot_names=[m.material_slot_name for m in materials]+['FingerlessGloveLeather'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write exposed skin '+name)
    mesh.set_editor_property('physics_asset',None);build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,build);save(mesh)
    if not (u.FPSModularOutfitComponent.configure_outfit_lods(mesh) and S.regenerate_lod(mesh,3,True,False)):raise RuntimeError('Cannot save skin LODs '+name)
    save(mesh);published[name]=mesh.get_path_name();receipt.write_text(json.dumps(dict(mesh=mesh.get_path_name(),sha256=sha,lods=3),indent=2))
    print('FINGERLESS_SKIN_SAVED',name,flush=True)
    saved_count+=1
(ROOT/'asset-receipt.json').write_text(json.dumps(dict(profiles=published,complete=len(published)==22),indent=2))
