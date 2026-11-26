"""Import one shared PBR shader and each Quixel granite model into the forest palette."""
import json, os
from pathlib import Path
import unreal as u

lib=u.EditorAssetLibrary
ed=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
base='/Game/ForestPathStudy/VillageRegion/Granite'
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])

def save(obj):
    if not lib.save_loaded_asset(obj,False): raise RuntimeError(obj.get_path_name())

def import_file(file,folder,name=None):
    task=u.AssetImportTask()
    task.filename=str(file);task.destination_path=folder;task.automated=True;task.save=True
    if name: task.destination_name=name
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError(str(file))
    return [u.load_asset(str(p)) for p in task.imported_object_paths]

def tex(file,folder,name,compression):
    asset=u.load_asset(folder+'/'+name) if lib.does_asset_exist(folder+'/'+name) else import_file(file,folder,name)[0]
    asset.set_editor_property('srgb',compression==u.TextureCompressionSettings.TC_DEFAULT)
    asset.set_editor_property('compression_settings',compression)
    if name.endswith('_ORM'):
        asset.set_editor_property('max_texture_size',1024)
        asset.set_editor_property('never_stream',False)
    save(asset)
    return asset

def bind(a,out,prop):
    if not ed.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError(prop)

def granite():
    pool=[]
    for item in sorted(json.loads((batch/'rocks.json').read_text()),key=lambda i:i['uid']):
        raw=src/'Fab'/item['uid']
        for gltf in sorted(raw.glob('*.gltf')):
            key=gltf.stem.split('_tier_')[0]
            folder=base+'/'+key
            lib.make_directory(folder)
            geometries=lib.list_assets(folder,recursive=True,include_folder=False)
            meshes=[m for path in geometries if isinstance(m:=u.load_asset(path),u.StaticMesh)]
            if not meshes:
                data=json.loads(gltf.read_text())
                stage=src/'Geometry'/key
                stage.mkdir(parents=True,exist_ok=True)
                for geom in data['meshes']:
                    for part in geom['primitives']:part.pop('material',None)
                for field in ('images','textures','materials','samplers'):data.pop(field,None)
                for buf in data['buffers']:
                    target=stage/buf['uri']
                    if not target.exists():os.link(raw/buf['uri'],target)
                temp=stage/gltf.name;temp.write_text(json.dumps(data))
                import_file(temp,folder)
                meshes=[m for p in lib.list_assets(folder,recursive=True,include_folder=False) if isinstance(m:=u.load_asset(p),u.StaticMesh)]
            maps={}
            for ch,comp in [('B','DEFAULT'),('N','NORMALMAP'),('ORM','MASKS')]:
                maps[ch]=tex(next(raw.rglob('*_'+ch+'.png')),folder,'T_'+key+'_'+ch,getattr(u.TextureCompressionSettings,'TC_'+comp))
            master=base+'/M_Granite'
            if not lib.does_asset_exist(master):
                mat=tools.create_asset('M_Granite',base,u.Material,u.MaterialFactoryNew())
                mat.set_editor_property('used_with_instanced_static_meshes',True)
                mat.set_editor_property('used_with_nanite',True)
                for i,(ch,typ) in enumerate([('B','COLOR'),('N','NORMAL'),('ORM','MASKS')]):
                    n=ed.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D,-320,i*240)
                    n.set_editor_property('texture',maps[ch]);n.set_editor_property('parameter_name',ch);n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+typ))
                    for pin,prop in {'B':[('RGB','BASE_COLOR')],'N':[('RGB','NORMAL')],'ORM':[('R','AMBIENT_OCCLUSION'),('G','ROUGHNESS'),('B','METALLIC')]}[ch]:bind(n,pin,prop)
                ed.recompile_material(mat);save(mat)
            name='MI_'+key
            mi=u.load_asset(folder+'/'+name) if lib.does_asset_exist(folder+'/'+name) else tools.create_asset(name,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
            ed.set_material_instance_parent(mi,u.load_asset(master))
            for ch,texture in maps.items():ed.set_material_instance_texture_parameter_value(mi,ch,texture)
            ed.update_material_instance(mi);save(mi)
            if not meshes:raise RuntimeError(gltf.name)
            for m in meshes:
                if not m.static_materials:m.set_editor_property('static_materials',[u.StaticMaterial()])
                for i in range(len(m.static_materials)):m.set_material(i,mi)
                ns=m.get_editor_property('nanite_settings');ns.enabled=True;m.set_editor_property('nanite_settings',ns)
                save(m)
                box=m.get_bounding_box();pool.append(dict(listing=item['uid'],mesh=m.get_path_name(),width_cm=max(box.max.x-box.min.x,box.max.y-box.min.y)))
    if set(x['listing'] for x in pool)!=set(x['uid'] for x in json.loads((batch/'rocks.json').read_text())):raise RuntimeError('Incomplete granite library')
    (src/'rock-pool.json').write_text(json.dumps(pool,indent=2))
granite()
