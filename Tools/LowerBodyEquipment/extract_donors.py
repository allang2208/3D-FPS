"""Publish converted donor meshes and read their fitting/texture inputs."""
import json, shutil
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/LowerBodyEquipment20261003'
prefix='Characters/ModularOutfit20260924/LowerBodyEquipment20261003/Donors'
for source in (PROJECT/'Tools/LowerBodyEquipment/AuthoringHost/Content'/prefix).glob('*.uasset'):
    dest=PROJECT/'Content'/prefix/source.name
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copyfile(source,dest)
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/'+prefix],True)
if not (ROOT/'donor_skin.json').exists():shutil.copyfile(ROOT/'jeans.json',ROOT/'donor_skin.json')
sources={k:'/Game/'+prefix+'/SK_'+n+'_Donor' for k,n in [('jeans','Jeans'),('cargo','Cargo'),('sneakers','Sneakers')]}
code=(PROJECT/'Tools/LowerBodyEquipment/prepare_sources.py').read_text()
exec('G, B, Q ='+code.split('G, B, Q =',1)[1])
# Preserve UVs for production icon authoring. Runtime meshes retain the originals.
for key,path in sources.items():
    asset=u.load_asset(path)
    dm,_=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    data=json.loads((ROOT/(key+'.json')).read_text())
    data['uv']=[[[v.x,v.y] for v in Q.get_triangle_u_vs(dm,0,i)[:3]] for i in range(dm.get_triangle_count())]
    textures={}
    for m in asset.materials:
        mat=m.material_interface
        if not mat:continue
        if str(m.material_slot_name) in textures:continue
        entry={}
        for name in u.MaterialEditingLibrary.get_texture_parameter_names(mat):
            if str(name).lower() not in ('basecolor','base color','diffuse','normals','normal','srmf','srm','orm','mask'):continue
            tex=u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat,name) if isinstance(mat,u.MaterialInstanceConstant) else u.MaterialEditingLibrary.get_material_default_texture_parameter_value(mat,name)
            if not tex:continue
            if tex.get_name().lower() in ('black_masks','white_masks','flat_normal'):continue
            dest=ROOT/'Textures'/(tex.get_name()+'.tga');dest.parent.mkdir(exist_ok=True)
            task=u.AssetExportTask();task.object=tex;task.filename=str(dest)
            task.automated=True;task.prompt=False;task.replace_identical=False
            if not dest.exists() and not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+tex.get_path_name())
            entry[str(name)]=str(dest)
        textures[str(m.material_slot_name)]=entry
    data['textures']=textures
    (ROOT/(key+'.json')).write_text(json.dumps(data,separators=(',',':')))
print('LOWER_BODY_DONORS_EXPORTED',flush=True)
