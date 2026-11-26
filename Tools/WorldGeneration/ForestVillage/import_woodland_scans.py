"""Import the selected Megascans wood at UE Medium; all opaque variants share one PBR parent."""
import json,os,shutil
from pathlib import Path
import unreal as u
from forest_wood_retirement import retired_meshes

lib=u.EditorAssetLibrary
ed=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
dest='/Game/ForestPathStudy/VillageRegion/WoodlandDressing'
def save(x):
    if not lib.save_loaded_asset(x,False):raise RuntimeError(x.get_path_name())
def imported(file,folder,name=None):
    job=u.AssetImportTask();job.filename=str(file);job.destination_path=folder;job.automated=True;job.save=True
    if name:job.destination_name=name
    tools.import_asset_tasks([job])
    return [u.load_asset(str(p)) for p in job.imported_object_paths]
def rest_log(mesh,role):
    box=mesh.get_bounding_box();extent=box.max-box.min
    if role=='log' and extent.z>1.45*max(extent.x,extent.y):
        api=u.GeometryScript_AssetUtils
        dm,status=api.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(mesh.get_path_name())
        slots=list(mesh.static_materials)
        u.GeometryScript_MeshTransforms.rotate_mesh(dm,u.Rotator(pitch=90,yaw=0,roll=0))
        _,status=api.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD(lod_index=0))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot lay log on its side')
        mesh.set_editor_property('static_materials',slots);save(mesh)
        box=mesh.get_bounding_box();extent=box.max-box.min
    return [extent.x,extent.y,extent.z]

def wood():
    lib.make_directory(dest)
    material_path=dest+'/M_WoodlandScan'
    master=u.load_asset(material_path) if lib.does_asset_exist(material_path) else lib.duplicate_asset('/Game/ForestPathStudy/VillageRegion/Granite/M_Granite',material_path)
    # The source parent is a neutral B/N/ORM pass. Give the wood parent its own defaults below.
    result=[]
    retired=retired_meshes()
    for item in json.loads((src/'selection.json').read_text()):
        role=item['role']
        if role=='leaves':continue
        raw=src/'Fab'/item['uid'];gltf=next(raw.glob('*.gltf'));data=json.loads(gltf.read_text(encoding='utf-8-sig'))
        if len(data['materials'])!=1 or data['materials'][0].get('alphaMode','OPAQUE')!='OPAQUE':raise RuntimeError('Expected an opaque wood scan '+item['title'])
        key=gltf.stem.split('_tier_')[0];folder=dest+'/Wood/'+role+'/'+key
        mesh_path=f'{folder}/{gltf.stem}/StaticMeshes/{gltf.stem}.{gltf.stem}'
        if mesh_path in retired:continue
        lib.make_directory(folder)
        mi_path=folder+'/MI_'+key
        mi=u.load_asset(mi_path) if lib.does_asset_exist(mi_path) else tools.create_asset('MI_'+key,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        ed.set_material_instance_parent(mi,master)
        for ch,typ in [('B','DEFAULT'),('N','NORMALMAP'),('ORM','MASKS')]:
            name='T_'+key+'_'+ch;path=folder+'/'+name
            t=u.load_asset(path) if lib.does_asset_exist(path) else imported(next(raw.rglob('*_'+ch+'.png')),folder,name)[0]
            t.set_editor_property('srgb',ch=='B');t.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,'TC_'+typ))
            cap=(1024 if role in ('stump','branch') else 2048) if ch=='B' else (512 if role=='branch' and ch=='ORM' else 1024)
            t.set_editor_property('max_texture_size',cap);t.set_editor_property('never_stream',False);save(t)
            if not result:
                for n in ed.get_material_expressions(master):
                    if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))==ch:n.set_editor_property('texture',t)
            ed.set_material_instance_texture_parameter_value(mi,ch,t)
        if not result:
            errs=ed.recompile_material(master)
            if errs:raise RuntimeError(str(errs))
            save(master)
        ed.update_material_instance(mi);save(mi)
        meshes=[m for p in lib.list_assets(folder,recursive=True,include_folder=False) if isinstance(m:=u.load_asset(p),u.StaticMesh)]
        if not meshes:
            stage=src/'Geometry'/key;stage.mkdir(exist_ok=True,parents=True)
            for geom in data['meshes']:
                for part in geom['primitives']:part.pop('material',None)
            for k in ('materials','textures','images','samplers'):data.pop(k,None)
            for buf in data['buffers']:
                target=stage/buf['uri'];target.parent.mkdir(exist_ok=True,parents=True)
                if not target.exists():shutil.copy2(raw/buf['uri'],target)
            prepared=stage/gltf.name;prepared.write_text(json.dumps(data));imported(prepared,folder)
            meshes=[m for p in lib.list_assets(folder,recursive=True,include_folder=False) if isinstance(m:=u.load_asset(p),u.StaticMesh)]
        if len(meshes)!=1:raise RuntimeError('Expected one mesh '+key)
        m=meshes[0]
        if not m.static_materials:m.set_editor_property('static_materials',[u.StaticMaterial()])
        for i in range(len(m.static_materials)):m.set_material(i,mi)
        ns=m.get_editor_property('nanite_settings');ns.enabled=True;m.set_editor_property('nanite_settings',ns)
        save(m)
        result.append(dict(role=role,uid=item['uid'],name=item['title'],mesh=m.get_path_name(),size_cm=rest_log(m,role)))
    (src/'wood-palette.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':wood()
