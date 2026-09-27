"""Save the isolated M4 candidate and shared baked material with a commandlet.

No active catalog references, shared naked hands, or animations are changed.
"""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ModularOutfit20260927/TailoredFingerlessCandidate'
DEST='/Game/Characters/ModularOutfit20260927/TailoredFingerlessCandidate'
# The existing native LOD author accepts this equipment root. Keep its contract
# without rebuilding gameplay code merely to save a dated candidate.
MESH_DEST='/Game/Characters/ModularOutfit20260924/TailoredFingerlessCandidate20260927'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)


def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing required source: '+path)
    return asset


def save(asset):
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or E.save_loaded_asset(asset,False)):
        raise RuntimeError('Asset save failed: '+asset.get_path_name())


def material(texture_root=None, asset_folder=None):
    folder=asset_folder or DEST+'/Materials';E.make_directory(folder);textures={}
    texture_root=Path(texture_root) if texture_root else R/'Textures'
    for channel in ('BaseColor','Roughness','Normal'):
        name='T_TailoredFingerless_'+channel
        task=u.AssetImportTask();task.filename=str(texture_root/(name+'.png'))
        task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);tex=load(folder+'/'+name)
        tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);textures[channel]=tex
    path=folder+'/M_TailoredFingerless';mat=u.load_asset(path)
    if not mat:mat=A.create_asset('M_TailoredFingerless',folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(mat):
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        for channel,prop,kind in [
            ('BaseColor',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR),
            ('Roughness',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS),
            ('Normal',u.MaterialProperty.MP_NORMAL,u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
            node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
            node.set_editor_property('parameter_name',channel);node.set_editor_property('texture',textures[channel]);node.set_editor_property('sampler_type',kind)
            if not L.connect_material_property(node,'R' if channel=='Roughness' else 'RGB',prop):raise RuntimeError('Material connection failed: '+channel)
        for value,prop in [(.42,u.MaterialProperty.MP_SPECULAR),(0.,u.MaterialProperty.MP_METALLIC)]:
            node=L.create_material_expression(mat,u.MaterialExpressionConstant);node.set_editor_property('r',value)
            if not L.connect_material_property(node,'',prop):raise RuntimeError('Constant connection failed')
        L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Material build failed: '+str(errors))
    save(mat)
    return mat


def build_mesh(d,assetname,materials,slot_names,destination_root=None):
    source=load(d.get('binding_source',d['source']))
    native,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native binding')
    _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
    vertices=[];normals=[];colors=[];weights=[];triangles=[];lookup={}
    channels=['uv']+sorted((k for k in d if k.startswith('uv') and k!='uv'),key=lambda k:int(k[2:]))
    uvs={k:[] for k in channels}
    for fi,face in enumerate(d['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            n=d['normals'][fi][ci];col=d['colors'][fi][ci] if 'colors' in d else [1,1,1,1]
            coords=[d[k][fi][ci] for k in channels]
            key=(vi,d['triangle_materials'][fi],*[round(v,7) for values in [n,col,*coords] for v in values])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));colors.append(u.LinearColor(*col));weights.append(d['weights'][vi])
                for k,uv in zip(channels,coords):uvs[k].append(u.Vector2D(*uv))
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    params={('uv0' if k=='uv' else k):v for k,v in uvs.items()}
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,vertex_colors=colors,triangles=triangles,**params),0,True)
    if dm.get_triangle_count()!=len(triangles):raise RuntimeError('Import rejected triangles')
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for i,w in enumerate(weights):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=v) for n,v in w.items()])
    for i,mat in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,mat,True)
    u.GeometryScript_MeshRepair.weld_mesh_edges(dm,u.GeometryScriptWeldEdgesOptions(tolerance=.00001,only_unique_pairs=True))
    folder=(destination_root or MESH_DEST)+'/'+d.get('profile','M4');E.make_directory(folder);asset=u.load_asset(folder+'/'+assetname)
    if not asset:asset=A.duplicate_asset(assetname,folder,source)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=materials,new_material_slot_names=slot_names,
        enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opts,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Candidate mesh write failed')
    asset.set_editor_property('physics_asset',None)
    settings=S.get_lod_build_settings(asset,0);settings.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,0,settings)
    save(asset)
    if not (u.FPSModularOutfitComponent.configure_outfit_lods(asset) and S.regenerate_lod(asset,3,True,False)):raise RuntimeError('Candidate LOD build failed')
    E.set_metadata_tag(asset,'SourceContract',d.get('contract','Native LeaderPose; zero animation edits'))
    save(asset);print('TAILORED_CANDIDATE_SAVED',asset.get_path_name(),flush=True)
    return asset


def main():
    mat=material()
    glove=json.loads((R/'M4_worn.json').read_text())
    standalone=build_mesh(glove,'SK_M4_TailoredFingerless',[mat],['FingerlessGloveLeather'])
    skin=json.loads((P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2/SkinCoverage/M4_review.json').read_text())
    source=load(skin['source']);slots=source.get_editor_property('materials');leather_index=len(slots);start=len(skin['positions'])
    skin['positions'].extend(glove['positions']);skin['weights'].extend(glove['weights'])
    skin['triangles'].extend([[v+start for v in f] for f in glove['triangles']]);skin['normals'].extend(glove['normals'])
    skin['triangle_materials'].extend([leather_index]*len(glove['triangles']))
    skin['colors'].extend([[[0,0,0,1]]*3 for _ in glove['triangles']])
    for key in [k for k in skin if k.startswith('uv')]:skin[key].extend(glove.get(key,[[[0,0]]*3 for _ in glove['triangles']]))
    combined=build_mesh(skin,'SK_M4_TailoredFingerlessSkin',[m.material_interface for m in slots]+[mat],[m.material_slot_name for m in slots]+['FingerlessGloveLeather'])
    receipt=dict(stage='saved_representative_candidate',material=mat.get_path_name(),standalone=standalone.get_path_name(),combined=combined.get_path_name(),lods=3,
                 source_profile='M4',new_animations=0,active_equipment_changed=False,runtime_tested=False)
    (R/'saved-assets.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (R/'M4-reference-fragment.json').write_text(json.dumps({'items':{'ue_field_gloves':{'skin_meshes':{'M4':combined.get_path_name()},
        'rig_meshes':{'M4':standalone.get_path_name()},'glove_in_base':True}}},indent=2)+'\n')
    print('TAILORED_CANDIDATE_IMPORT_COMPLETE',flush=True)


if __name__=='__main__':main()
