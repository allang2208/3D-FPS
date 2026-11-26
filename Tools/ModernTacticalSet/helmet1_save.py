"""Save only the isolated helmet revision, including actual game and UI assets."""
import unreal as u,json,hashlib,gc,importlib.util
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/HelmetDetailR1';DEST='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/HelmetDetailR1'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils;L=u.MaterialEditingLibrary
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
io=module('helmet_static_buffers',P/'Tools/FieldHat/save_icon.py')
receipt=read(R/'saved.json') if (R/'saved.json').exists() else dict(completed=False,materials={},meshes={},textures={})
def record():(R/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(a):
    if not a.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside helmet revision')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def texture(file,ui=False):
    file=Path(file);folder=DEST+('/Icons' if ui else '/Textures');path=folder+'/'+file.stem;fingerprint=sha(file);a=u.load_asset(path)
    if a and E.get_metadata_tag(a,'HelmetSourceSHA')==fingerprint:return a
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=file.stem;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);a=u.load_asset(path)
    if not a:raise RuntimeError('Texture import '+str(file))
    normal=file.stem.endswith('_NormalGL');color=ui or file.stem.endswith('_BaseColor')
    props=dict(srgb=color,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON if ui else u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS)
    if ui:props.update(lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    else:props.update(flip_green_channel=normal,never_stream=False,compression_no_alpha=True,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP,max_texture_size=2048 if 'Composite' in file.stem else 1024)
    for key,v in props.items():a.set_editor_property(key,v)
    E.set_metadata_tag(a,'HelmetSourceSHA',fingerprint);save(a);receipt['textures'][file.stem]=dict(asset=a.get_path_name(),sha256=fingerprint);record();return a
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material link '+pin)
surfaces=read(R/'surfaces.json');materials={}
for name,info in surfaces.items():
    files={c:R/'Textures'/f'H1_{name}_{c}.png' for c in ['BaseColor','NormalGL','ORM']};fingerprint=hashlib.sha256(('helmet1-pbr-v1'+json.dumps(info,sort_keys=True)+''.join(sha(p) for p in files.values())).encode()).hexdigest();path=DEST+'/Materials/M_H1_'+name;mat=u.load_asset(path)
    if not mat or E.get_metadata_tag(mat,'HelmetMaterialSHA')!=fingerprint:
        mats={c:texture(p) for c,p in files.items()};mat=mat or A.create_asset('M_H1_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);mat.set_editor_property('two_sided',False);mat.set_editor_property('use_material_attributes',True);cloth=name in ['Webbing','LoopPile','PadMesh'];mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH if cloth else u.MaterialShadingModel.MSM_DEFAULT_LIT)
        attrs=node(mat,u.MaterialExpressionMakeMaterialAttributes);L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
        for c,t in mats.items():
            sample=node(mat,u.MaterialExpressionTextureSampleParameter2D,parameter_name=c,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if c=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if c=='NormalGL' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            if c=='BaseColor':wire(sample,attrs,'BaseColor','RGB')
            elif c=='NormalGL':wire(sample,attrs,'Normal','RGB')
            else:
                for out,pin in [('R','AmbientOcclusion'),('G','Roughness'),('B','Metallic')]:wire(sample,attrs,pin,out)
        wire(node(mat,u.MaterialExpressionConstant,r=info['specular']),attrs,'Specular')
        if cloth:
            wire(node(mat,u.MaterialExpressionConstant,r=.22 if name=='LoopPile' else .10),attrs,'ClearCoat');wire(node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.12,.09,.055,1)),attrs,'SubsurfaceColor')
        errors=L.recompile_material(mat)
        if errors:raise RuntimeError('Helmet material compile '+str(errors))
        E.set_metadata_tag(mat,'HelmetMaterialSHA',fingerprint);save(mat)
    materials['H1_'+name]=mat;receipt['materials']['H1_'+name]=mat.get_path_name();record()
art=read(R/'artwork.json');jobs=[('Jason',R/'Authored/helmet_Jason_wear.json',DEST+'/Wear/SM_TS01_Helmet_Jason'),('Kaitlin',R/'Authored/helmet_Kaitlin_wear.json',DEST+'/Wear/SM_TS01_Helmet_Kaitlin'),('pickup',Path(art['pickup']),DEST+'/Pickups/SM_TS01_Helmet'),('display',Path(art['icon']['display']),DEST+'/Icons/SM_TS01_Helmet_Display')]
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);receipt['completed']=False
for key,file,path in jobs:
    fingerprint=sha(file)
    if receipt['meshes'].get(key,{}).get('sha256')==fingerprint:continue
    d=read(file);dm=io.dynamic(d);mesh=u.load_asset(path);mats=[materials[n] for n in d['material_slots']]
    opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'])
    if mesh:_,status=G.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
    else:
        mesh,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
        if mesh:mesh.set_editor_property('static_materials',[u.StaticMaterial(material_interface=mat,material_slot_name=slot,imported_material_slot_name=slot) for mat,slot in zip(mats,d['material_slots'])])
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Helmet mesh write '+key)
    # Preserve the detailed author LOD0. Existing distance convention retained.
    reduction=u.StaticMeshReductionOptions();reduction.auto_compute_lod_screen_size=False;reduction.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=r,screen_size=s) for r,s in [(1.,1.),(.7,.18),(.45,.07)]];lod_count=sub.set_lods(mesh,reduction)
    if lod_count!=3:raise RuntimeError('Helmet LOD generation returned '+str(lod_count)+' for '+key)
    E.set_metadata_tag(mesh,'HelmetSourceSHA',fingerprint);E.set_metadata_tag(mesh,'HelmetRevision','HelmetDetailR1');save(mesh);receipt['meshes'][key]=dict(asset=mesh.get_path_name(),sha256=fingerprint,lod_count=lod_count);record();print('HELMET_DETAIL_MESH_SAVED',key,flush=True)
    del d,dm,mesh;gc.collect();u.SystemLibrary.collect_garbage()
icon=texture(art['icon']['png'],True);receipt['icon']=dict(asset=icon.get_path_name(),sha256=sha(art['icon']['png']));receipt['completed']=True;record();print('HELMET_DETAIL_ASSETS_SAVED',flush=True)
