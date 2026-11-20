"""Save the four helmet mesh roles and inventory texture in a content-only host."""
import gc
import hashlib
import json
import runpy
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[2]
REV=globals().get('HELMET_REVISION','HelmetContourR2')
R=P/'SourceAssets/ModernTacticalSet20261113'/REV
BASE='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113'
DEST=BASE+'/'+REV
E=u.EditorAssetLibrary
G=u.GeometryScript_AssetUtils
dynamic=runpy.run_path(str(P/'Tools/FieldHat/save_icon.py'))['dynamic']
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
art=json.loads((R/'artwork.json').read_bytes())
wear_suffix=globals().get('HELMET_WEAR_SUFFIX','')
jobs=[(rig,R/'Authored'/f'helmet_{rig}_wear.json','Wear/SM_TS01_Helmet_'+rig+wear_suffix) for rig in ['Jason','Kaitlin']]
jobs.extend([('pickup',Path(art['pickup']),'Pickups/SM_TS01_Helmet'),('display',Path(art['icon']['display']),'Icons/SM_TS01_Helmet_Display')])
receipt={'completed':False,'meshes':{}}
wear_only=globals().get('HELMET_WEAR_ONLY',False)
if wear_only:
    receipt=json.loads((R/'saved.json').read_bytes())
    jobs=jobs[:2]
    receipt['completed']=False
def record():
    (R/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
for key,source,relative in jobs:
    raw=source.read_bytes();d=json.loads(raw);digest=hashlib.sha256(raw).hexdigest()
    path=DEST+'/'+relative
    mesh=E.load_asset(path) if E.does_asset_exist(path) else None
    if mesh and E.get_metadata_tag(mesh,'HelmetRevision')!=REV:raise ValueError('Unexpected package '+path)
    if mesh is None or E.get_metadata_tag(mesh,'HelmetSourceSHA')!=digest:
        dm=dynamic(d)
        if dm.get_triangle_count()!=len(d['triangles']):raise RuntimeError('Lost authored triangles for '+key)
        material_revision=globals().get('HELMET_MATERIAL_REVISION','HelmetDetailR1')
        mats=[E.load_asset(BASE+'/'+material_revision+'/Materials/M_'+n) for n in d['material_slots']]
        if not all(mats):raise RuntimeError('Missing PBR material')
        if mesh is None:
            mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
            if mesh:
                mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=m,material_slot_name=n) for m,n in zip(mats,d['material_slots'])])
        else:
            opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'])
            _,status=G.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot create '+path)
        red=u.StaticMeshReductionOptions();red.auto_compute_lod_screen_size=False
        lod_settings=globals().get('HELMET_LOD_SETTINGS',[(1.,1.),(.7,.18),(.45,.07)])
        red.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=r,screen_size=s) for r,s in lod_settings]
        if sub.set_lods(mesh,red)!=3:raise RuntimeError('Cannot save three LODs')
        E.set_metadata_tag(mesh,'HelmetSourceSHA',digest);E.set_metadata_tag(mesh,'HelmetRevision',REV)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+path)
        del dm
    receipt['meshes'][key]={'asset':mesh.get_path_name(),'source_sha':digest,'lods':3}
    if key in ('Jason','Kaitlin'):
        folder=R/'SavedLods';folder.mkdir(exist_ok=True)
        for i in range(3):
            lod,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=i))
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('Unable to read saved LOD')
            Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
            _,vs,_=Q.get_all_vertex_positions(lod,False);vs=L.convert_vector_list_to_array(vs)
            _,fs,_=Q.get_all_triangle_indices(lod,False);fs=L.convert_triangle_list_to_array(fs)
            _,ids,valid=u.GeometryScript_Materials.get_all_triangle_material_i_ds(lod)
            if not valid:raise RuntimeError('No shell ID array '+key)
            material_ids=list(L.convert_index_list_to_array(ids))
            if globals().get('HELMET_RECORD_RENDER_STATS',False):
                entry=receipt['meshes'][key]
                entry.setdefault('render_lods',[]).append(dict(lod=i,vertices=len(vs),triangles=len(fs),
                    sections={slot:material_ids.count(mi) for mi,slot in enumerate(d['material_slots'])}))
            fs=[(t.x,t.y,t.z) for t,m in zip(fs,material_ids) if m==0]
            used=sorted({v for tri in fs for v in tri});remap={v:n for n,v in enumerate(used)}
            shell=dict(positions=[[vs[j].x,vs[j].y,vs[j].z] for j in used],triangles=[[remap[v] for v in tri] for tri in fs],attachment_frame=d['attachment_frame'])
            (folder/f'{key}_LOD{i}.json').write_text(json.dumps(shell,separators=(',',':')),encoding='utf8')
    record();print('HELMET_CONTOUR_SAVED',key,flush=True)
    del d,mesh;gc.collect();u.SystemLibrary.collect_garbage()
if not wear_only:
    png=Path(art['icon']['png']);task=u.AssetImportTask()
    task.filename=str(png);task.destination_path=DEST+'/Icons';task.destination_name=png.stem
    task.automated=True;task.replace_existing=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);texture=E.load_asset(DEST+'/Icons/'+png.stem)
    for k,v in dict(srgb=True,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS).items():texture.set_editor_property(k,v)
    if not E.save_loaded_asset(texture,False):raise RuntimeError('Inventory texture did not save')
    receipt.update(icon=texture.get_path_name(),icon_sha=hashlib.sha256(png.read_bytes()).hexdigest())
receipt['completed']=True;record();print('HELMET_CONTOUR_ASSETS_COMPLETE',flush=True)
