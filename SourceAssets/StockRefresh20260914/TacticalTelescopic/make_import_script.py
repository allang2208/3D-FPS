"""Reuse the established receiver shader construction in a standalone import job."""
from pathlib import Path
P=Path(__file__).resolve().parent
source=Path('D:/FPS3D/FPSGAME/SourceAssets/CoreStock20260914/Meshy0914005605/import_assets.py').read_text(encoding='utf-8')
helpers=source[source.index('def save(asset):'):source.index('\ntextures={}')] 
finish=source[source.index('def finish(m,family):'):source.index('\ndef add_normal(m,uv):')]
header='''"""Import the user-selected tactical telescopic stock and its three receiver finishes."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;D='/Game/Weapons/TacticalTelescopicStock20260914'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'stage':'import and save','gameplay_tested':False,'assets':{}}
'''
body='''
textures={}
for key in ['BaseColor','Normal_Game','Roughness','Metallic']:
    t=import_file(P/'Textures'/(key+'.png'),'T_TacticalStock_'+key,D+'/Textures')
    t.srgb=key=='BaseColor';t.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON;t.lod_bias=0
    t.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if key=='Normal_Game' else u.TextureCompressionSettings.TC_DEFAULT if key=='BaseColor' else u.TextureCompressionSettings.TC_MASKS
    if key=='Normal_Game':t.flip_green_channel=True
    save(t);textures[key]=t

def add_normal(m):
    n=sample(m,textures['Normal_Game'],uvcoord(m,0),u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    M.connect_material_property(n,'RGB',u.MaterialProperty.MP_NORMAL)
props={'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Roughness':u.MaterialProperty.MP_ROUGHNESS,'Metallic':u.MaterialProperty.MP_METALLIC,'Specular':u.MaterialProperty.MP_SPECULAR}
surfaces={}
for kind in ['Polymer','Rubber']:
    m=material('M_TacticalStock_'+kind,D);uv=uvcoord(m,0)
    for key,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS)]:
        n=sample(m,textures[key],uv,u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        M.connect_material_property(n,'RGB' if key=='BaseColor' else 'R',prop)
    M.connect_material_property(scalar(m,0),'',u.MaterialProperty.MP_METALLIC);add_normal(m)
    M.recompile_material(m);save(m);surfaces[kind]=m
for family in ['M4','AKM','QBZ191']:
    dest=D+'/'+family;bindings=dict(surfaces)
    for kind in ['Metal','Adapter']:
        m=material('M_TacticalStock_'+kind+'_'+family,dest)
        for key,(node,pin) in finish(m,family).items():M.connect_material_property(node,pin,props[key])
        if kind=='Metal':add_normal(m)
        M.recompile_material(m);save(m);bindings[kind]=m
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_file(P/family/'SM_TacticalTelescopicStock.fbx','SM_TacticalTelescopicStock',dest,opt)
    for i,slot in enumerate(mesh.static_materials):
        name=str(slot.material_slot_name);kind=next(k for k in bindings if k in name);mesh.set_material(i,bindings[kind])
    E.set_metadata_tag(mesh,'SourceAsset','Meshy_AI_Adjustable_Rifle_Stoc_0914030720_generate.fbx')
    E.set_metadata_tag(mesh,'AttachmentId','tactical_telescopic')
    E.set_metadata_tag(mesh,'Authoring','80k game derivative; authored UV0 and PBR, selected high normal bake, receiver coating on UV1, per-rifle mounts')
    save(mesh);report['assets'][family]={'path':mesh.get_path_name(),'triangles':mesh.get_num_triangles(0),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.static_materials}}
    print('TACTICAL_STOCK_SAVED',family,flush=True)
(P/'import_results.json').write_text(json.dumps(report,indent=2));u.log('TACTICAL_STOCK_IMPORT_COMPLETE')
'''
(P/'import_assets.py').write_text(header+helpers+finish+body,encoding='utf-8')
