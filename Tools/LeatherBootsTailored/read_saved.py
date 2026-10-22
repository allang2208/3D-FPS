"""Read fresh saved UE packages for boot-scoped round-trip and material checks."""
import gc,hashlib,json,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;L=u.GeometryScript_List;M=u.MaterialEditingLibrary
saved=read(R/'saved_assets.json');surfaces=read(R/'materials.json');assert saved.get('completed')
result=dict(meshes={},textures=[],materials=[],displays={},runtime_tested=False)
def xyz(v):return [v.x,v.y,v.z]
for profile in ('Jason','Jason_RobeInner'):
    key='ue_leather_boots/'+profile;asset=u.load_asset(saved['saved'][key]['asset']);assert asset
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);count=sub.get_lod_count(asset);assert count==3
    paths=[s.material_interface.get_path_name() for s in asset.materials];expected=surfaces['robe_materials'] if profile.endswith('RobeInner') else surfaces['materials'];assert paths==expected
    slots=[str(s.material_slot_name) for s in asset.materials];assert slots==(['RobeStairHidden_'+str(i) for i in range(7)] if profile.endswith('RobeInner') else SLOTS)
    row=dict(asset=asset.get_path_name(),skeleton=asset.skeleton.get_path_name(),slots=slots,materials=paths,lods=[])
    for lod in range(count):
        spec=u.GeometryScriptMeshReadLOD();spec.lod_index=lod
        if lod:spec.lod_type=u.GeometryScriptLODType.RENDER_DATA
        dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),spec);assert status==u.GeometryScriptOutcomePins.SUCCESS
        _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);ps=[xyz(v) for v in L.convert_vector_list_to_array(vs)];ts=[xyz(v) for v in L.convert_triangle_list_to_array(fs)]
        if lod==0:assert len(ts)==saved['saved'][key]['triangles']
        else:assert len(ts)<row['lods'][-1]['triangles']
        build=sub.get_lod_build_settings(asset,lod);assert build.use_full_precision_u_vs
        row['lods'].append(dict(lod=lod,vertices=len(ps),triangles=len(ts),full_precision_uv=True,geometry_sha256=hashlib.sha256(json.dumps([ps,ts],separators=(',',':')).encode()).hexdigest()))
        if lod==0:
            _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones};row['bone_count']=len(bones)
            if profile=='Jason':
                data=dict(positions=ps,triangles=ts,weights=[],normals=[],uv=[],triangle_materials=[],colors=[])
                for vi in range(len(ps)):
                    _,ws,ok=B.get_vertex_bone_weights(dm,vi);assert ok;data['weights'].append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
                for ti in range(len(ts)):
                    a,b,c,ok=Q.get_triangle_u_vs(dm,0,ti);assert ok;data['uv'].append([[v.x,v.y] for v in (a,b,c)])
                    _,a,b,c,ok=Q.get_triangle_normals(dm,ti);assert ok;data['normals'].append([xyz(v) for v in (a,b,c)]);data['triangle_materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0])
                    _,a,b,c,ok=Q.get_triangle_vertex_colors(dm,ti);assert ok;data['colors'].append([[v.r,v.g,v.b,v.a] for v in (a,b,c)])
                f=R/'SavedRead/Jason.json';f.parent.mkdir(exist_ok=True);f.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8');del data
        del dm,ps,ts;gc.collect();u.SystemLibrary.collect_garbage()
    result['meshes'][profile]=row;print('LEATHER_BOOT_SAVED_MESH_READ',profile,flush=True)
assert result['meshes']['Jason']['skeleton']==result['meshes']['Jason_RobeInner']['skeleton']
assert [x['geometry_sha256'] for x in result['meshes']['Jason']['lods']]==[x['geometry_sha256'] for x in result['meshes']['Jason_RobeInner']['lods']]
for path in surfaces['textures']:
    tex=u.load_asset(path);assert tex;normal='_Normal.' in path;orm='_ORM.' in path
    assert bool(tex.srgb)==(not normal and not orm);assert bool(tex.flip_green_channel)==normal;assert not tex.never_stream
    assert tex.compression_settings==(u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if orm else u.TextureCompressionSettings.TC_DEFAULT)
    assert tex.mip_gen_settings==u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE
    result['textures'].append(dict(asset=path,srgb=bool(tex.srgb),flip_green=bool(tex.flip_green_channel),streaming=True))
for path in surfaces['materials']+surfaces['robe_materials']:
    mat=u.load_asset(path);errors=M.recompile_material(mat);assert not errors,str(errors)
    result['materials'].append(dict(asset=path,compile_errors=[],masked=mat.blend_mode==u.BlendMode.BLEND_MASKED))
for kind,path in saved['displays'].items():
    asset=u.load_asset(path);assert asset;sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);assert sub.get_lod_count(asset)==3
    assert [x.material_interface.get_path_name() for x in asset.static_materials]==surfaces['materials'];result['displays'][kind]=dict(asset=path,lod_count=3)
assert u.load_asset(saved['icon_texture']);result['completed']=True;write(R/'saved_read.json',result);print('LEATHER_BOOT_SAVED_PACKAGES_READ_COMPLETE',flush=True)
