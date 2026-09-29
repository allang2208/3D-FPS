"""Save V2 chainmail in short exclusive UE batches; publish after every save."""
import hashlib
import json
import sys
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailInterlace20260929'
DEST='/Game/Characters/ModularOutfit20260924/ChainmailInterlace20260929'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from import_tailored_fingerless_candidate import load,save as save_package
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)


def save(asset):
    # This family is also authored offline while an unrelated editor is open.
    # Only newly named V2 packages may be written by the background process.
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside chainmail V2 save scope: '+asset.get_path_name())
    save_package(asset)


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def ensure_authoring():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('CHAINMAIL_PIE_ACTIVE: asset authoring needs the current play session to finish')
    read(R/'production.json')


def simple_material(name,color,metallic,roughness):
    folder=DEST+'/Materials';mat=u.load_asset(folder+'/'+name)
    if not mat:mat=A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(mat):
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        rgb=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        rgb.set_editor_property('constant',u.LinearColor(*color,1))
        if not L.connect_material_property(rgb,'',u.MaterialProperty.MP_BASE_COLOR):raise RuntimeError(name+' BaseColor connection')
        for value,prop in [(metallic,u.MaterialProperty.MP_METALLIC),(roughness,u.MaterialProperty.MP_ROUGHNESS),(.5,u.MaterialProperty.MP_SPECULAR)]:
            scalar=L.create_material_expression(mat,u.MaterialExpressionConstant);scalar.set_editor_property('r',value)
            if not L.connect_material_property(scalar,'',prop):raise RuntimeError(name+' scalar connection')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Cuff material compile: '+str(errors))
    save(mat);return mat


def materials():
    import import_chainmail_relief as previous
    previous.R,previous.DEST=R,DEST
    previous.save=save
    previous.material()
    result=read(R/'materials-saved.json');mat=load(result['relief'])
    for expr in L.get_material_expressions(mat):
        if isinstance(expr,u.MaterialExpressionVectorParameter) and str(expr.get_editor_property('parameter_name'))=='TileRepeat25cm':
            expr.set_editor_property('default_value',u.LinearColor(.25/.048,.25/.0176,0,0))
        elif isinstance(expr,u.MaterialExpressionScalarParameter) and str(expr.get_editor_property('parameter_name'))=='RingReliefDepthCm':
            expr.set_editor_property('default_value',.38)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Interlace material compile: '+str(errors))
    save(mat)
    standard=load(result['standard']);L.update_material_instance(standard);save(standard)
    result['cuff_steel']=simple_material('M_CuffForgedSteel',(.32,.34,.36),1.,.34).get_path_name()
    result['binding']=simple_material('M_CuffDarkBinding',(.023,.019,.016),0.,.78).get_path_name()
    write(R/'materials-saved.json',result)
    print('CHAINMAIL_INTERLACE_MATERIALS_SAVED',flush=True)


def build_mesh(data,materials):
    name=data['profile'];source=load(data['binding_source'])
    native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read binding '+name)
    _,bones=B.get_all_bones_info(native);bone_ids={str(b.name):b.index for b in bones}
    vertices,normals,uv0,weights,triangles=[],[],[],[],[];lookup={}
    for fi,face in enumerate(data['triangles']):
        row=[]
        for corner,vi in enumerate(face):
            uv=data['uv'][fi][corner];normal=data['normals'][fi][corner]
            key=(vi,*[round(v,7) for v in (*uv,*normal)])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]))
                normals.append(u.Vector(*normal));uv0.append(u.Vector2D(*uv));weights.append(data['weights'][vi])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv0,triangles=triangles),0,True)
    # Material sections are part of the clothing: the outer weave, solid links,
    # and dark inner/binding surfaces must not receive one global override.
    for ti,slot in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,slot,True)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,bindings in enumerate(weights):
        B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=bone_ids[n],weight=w) for n,w in bindings.items()])
    folder=DEST+'/'+name;mesh_name='SK_'+name+'_ChainmailShirt'
    mesh=u.load_asset(folder+'/'+mesh_name) or A.duplicate_asset(mesh_name,folder,source)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,
        new_material_slot_names=['InterlacedMail','SolidCuffLinks','DarkBinding'],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot build '+name)
    mesh.set_editor_property('physics_asset',None)
    build=S.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,build)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('LOD setup '+name)
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('LOD build '+name)
    E.set_metadata_tag(mesh,'EquipmentDefinition','ue_chainmail_shirt')
    E.set_metadata_tag(mesh,'SourceContract',data['contract']);save(mesh)
    return mesh


def meshes(names):
    mats=read(R/'materials-saved.json')
    for name in names:
        path=R/'Authored'/(name+'.json');raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        receipt=R/'Saved'/(name+'.json')
        old=read(receipt) if receipt.exists() else {}
        if old.get('authored_sha256')==digest and E.does_asset_exist(old['mesh']):continue
        data=json.loads(raw)
        group=[load(mats['standard'] if name=='Body' else mats['relief']),load(mats['cuff_steel']),load(mats['binding'])]
        mesh=build_mesh(data,group)
        write(receipt,dict(mesh=mesh.get_path_name(),authored_sha256=digest,lod0_triangles=len(data['triangles']),
                           lods=3,source=data['binding_source'],skeleton=data['skeleton'],new_animations=0))
        print('CHAINMAIL_INTERLACE_MESH_SAVED',name,flush=True)


def main(stage='materials',names=None):
    ensure_authoring()
    if stage=='materials':materials()
    elif stage=='meshes':meshes(names or [r['profile'] for r in read(R/'manifest.json')])
    else:raise ValueError(stage)


if __name__=='__main__':main()
