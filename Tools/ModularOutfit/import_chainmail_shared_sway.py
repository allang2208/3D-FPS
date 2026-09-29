"""Save shared-offset mail/lining surfaces with zero clothing assets."""
import hashlib,json,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailSharedSway20260929'
BASE=P/'SourceAssets/ChainmailInterlace20260929'
DEST='/Game/Characters/ModularOutfit20260924/ChainmailSharedSway20260929'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from import_tailored_fingerless_candidate import load,save as save_package
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside shared sway save scope')
    save_package(asset)

def material(source,name):
    folder=DEST+'/Materials';mat=u.load_asset(folder+'/'+name) or A.duplicate_asset(name,folder,load(source))
    def node(cls):return L.create_material_expression(mat,cls)
    def wire(a,b,pin,output=''):
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material connection '+pin)
    def mask(value,channels):
        n=node(u.MaterialExpressionComponentMask)
        for c in 'rgba':n.set_editor_property(c,c in channels)
        wire(value,n,'');return n
    if not any(isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='CuffLagLeft' for n in L.get_material_expressions(mat)):
        colors=node(u.MaterialExpressionVertexColor);left=mask(colors,'r');right=mask(colors,'g')
        def field(previous):
            values=[]
            for side,weight in [('Left',left),('Right',right)]:
                p=node(u.MaterialExpressionVectorParameter)
                p.set_editor_property('parameter_name','CuffLag'+('Previous' if previous else '')+side)
                p.set_editor_property('default_value',u.LinearColor(0,0,0,0))
                mul=node(u.MaterialExpressionMultiply);wire(mask(p,'rgb'),mul,'A');wire(weight,mul,'B');values.append(mul)
            total=node(u.MaterialExpressionAdd);wire(values[0],total,'A');wire(values[1],total,'B');return total
        current=field(False);previous=field(True);switch=node(u.MaterialExpressionPreviousFrameSwitch)
        wire(current,switch,'Current Frame');wire(previous,switch,'Previous Frame')
        attrs=next((x for x in L.get_material_expressions(mat) if isinstance(x,u.MaterialExpressionMakeMaterialAttributes)),None)
        if mat.get_editor_property('use_material_attributes'):
            if not attrs:raise RuntimeError('Unsupported material attribute graph '+name)
            wire(switch,attrs,'WorldPositionOffset')
        elif not L.connect_material_property(switch,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET):raise RuntimeError('Missing WPO output '+name)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        mat.set_editor_property('max_world_position_offset_displacement',.12)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Shared sway material compilation '+str(errors))
    save(mat);return mat

def materials():
    old=read(BASE/'materials-saved.json')
    group=[material(old[key],name) for key,name in [('relief','M_Chainmail_SharedSway'),('cuff_steel','M_CuffSteel_SharedSway'),('binding','M_Lining_SharedSway')]]
    write(R/'materials-saved.json',dict(zip(['mail','steel','lining'],[x.get_path_name() for x in group])))
    return group

def build(data,mask,materials):
    name=data['profile'];source=load(data['binding_source'])
    native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native rig '+name)
    _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
    vertices,normals,uv0,weights,colors,triangles=[],[],[],[],[],[];lookup={}
    for fi,face in enumerate(data['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            uv=data['uv'][fi][ci];normal=data['normals'][fi][ci]
            key=(vi,*[round(v,7) for v in (*uv,*normal)])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]))
                normals.append(u.Vector(*normal));uv0.append(u.Vector2D(*uv));weights.append(data['weights'][vi]);colors.append(u.LinearColor(*mask['colors'][vi]))
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(
        vertices=vertices,normals=normals,uv0=uv0,vertex_colors=colors,triangles=triangles),0,True)
    for ti,slot in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,ti,slot,True)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,bindings in enumerate(weights):B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in bindings.items()])
    folder=DEST+'/'+name;mesh_name='SK_'+name+'_ChainmailShirt'
    mesh=u.load_asset(folder+'/'+mesh_name) or A.duplicate_asset(mesh_name,folder,source)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,
        new_material_slot_names=['InterlacedMail','SolidCuffLinks','DarkBinding'],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Mesh production failed '+name)
    mesh.set_editor_property('physics_asset',None)
    settings=S.get_lod_build_settings(mesh,0);settings.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(mesh,0,settings)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('LOD setup '+name)
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('LOD build '+name)
    E.set_metadata_tag(mesh,'EquipmentDefinition','ue_chainmail_shirt')
    E.set_metadata_tag(mesh,'SecondaryMotion','Shared outer/inner vertex mask; max 0.12 cm; no clothing assets')
    save(mesh);return mesh

def main(names=None):
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('Asset save needs play session to end')
    group=materials()
    for record in read(R/'manifest.json'):
        name=record['profile']
        if names and name not in names:continue
        mask=(R/'Masks'/(name+'.json')).read_bytes();original=Path(record['source']).read_bytes()
        digest=hashlib.sha256(mask+original+Path(__file__).read_bytes()).hexdigest();receipt=R/'Saved'/(name+'.json')
        if receipt.exists():
            saved=read(receipt)
            if saved.get('source_sha256')==digest and E.does_asset_exist(saved['mesh']):continue
        mesh=build(json.loads(original),json.loads(mask),group)
        write(receipt,dict(mesh=mesh.get_path_name(),source_sha256=digest,lod0_triangles=record['triangles'],
            clothing_assets=0,lods=3,max_offset_cm=.12,shared_lining=True,new_animations=0,runtime_tested=False))
        print('CHAINMAIL_SHARED_SWAY_SAVED',name,flush=True)
if __name__=='__main__':main()
