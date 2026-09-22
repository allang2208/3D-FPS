"""Install authored V2 structure and PBR maps into revision-only UE packages."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
OUT='/Game/Dungeons/AtmosphereV2'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
manifest=json.loads((ROOT/'Authored/structure-manifest.json').read_text(encoding='utf-8'))
textures=json.loads((ROOT/'Authored/material-manifest.json').read_text(encoding='utf-8'))
receipt={'meshes':{},'materials':{},'tests_run':False}

def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Unable to save '+a.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def output(expr,prop,pin=''):
    if not L.connect_material_property(expr,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material connection failed '+prop)

for name,maps in textures.items():
    for channel,filename in maps.items():
        path=OUT+'/Textures/T_'+name+'_'+channel
        if not E.does_asset_exist(path):
            task=u.AssetImportTask();task.filename=filename;task.destination_path=OUT+'/Textures';task.destination_name='T_'+name+'_'+channel
            task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task])
            t=u.load_asset(path)
            if not t:raise RuntimeError('Texture import failed: '+path)
            t.set_editor_property('srgb',channel=='BaseColor')
            if channel=='Normal':
                t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
                t.set_editor_property('flip_green_channel',True)
            elif channel!='BaseColor':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
            save(t)
    path=OUT+'/Materials/M_'+name;m=u.load_asset(path)
    if not m:
        m=A.create_asset('M_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
        for channel,pin in [('BaseColor','BASE_COLOR'),('Roughness','ROUGHNESS'),('Metallic','METALLIC'),('Normal','NORMAL')]:
            n=node(m,u.MaterialExpressionTextureSample)
            n.texture=u.load_asset(OUT+'/Textures/T_'+name+'_'+channel)
            n.sampler_type=(u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else
                            (u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS))
            output(n,pin,'' if channel in ('BaseColor','Normal') else 'R')
        L.layout_material_expressions(m);L.recompile_material(m);save(m)
    receipt['materials'][name]=path
for name,color,rough,emissive in [('WetFloor',(.035,.045,.042),.095,0),('WarmGlass',(1,.52,.16),.5,3),('CoolGlass',(.62,.79,1),.5,3)]:
    path=OUT+'/Materials/M_'+name;m=u.load_asset(path)
    if not m:
        m=A.create_asset('M_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
        c=node(m,u.MaterialExpressionConstant3Vector);c.constant=u.LinearColor(*color,1);output(c,'BASE_COLOR')
        r=node(m,u.MaterialExpressionConstant);r.r=rough;output(r,'ROUGHNESS')
        if emissive:
            em=node(m,u.MaterialExpressionConstant3Vector);em.constant=u.LinearColor(*(v*emissive for v in color),1);output(em,'EMISSIVE_COLOR')
        L.recompile_material(m);save(m)
    receipt['materials'][name]=path

for entry in manifest['objects']:
    name=entry['name'];path=OUT+'/Structure/'+name
    mesh=u.load_asset(path)
    # Reimport this revision's own authored sources so geometry corrections also
    # reach actors already placed in the saved V2 map.
    if True:
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=OUT+'/Structure';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
        options.import_as_skeletal=False;options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+name)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=str(slot.get_editor_property('material_slot_name')).removeprefix('V2_')
        if key not in receipt['materials']:raise RuntimeError('Unmapped authored material '+key)
        mesh.set_material(i,u.load_asset(receipt['materials'][key]))
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;mesh.set_editor_property('nanite_settings',nanite)
    save(mesh)
    b=mesh.get_bounds()
    receipt['meshes'][name]={'path':path,'origin':list(b.origin.to_tuple()),'extent':list(b.box_extent.to_tuple())}
    (ROOT/'Receipts/structure-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('V2_STRUCTURE_IMPORTED',len(receipt['meshes']),'meshes',len(receipt['materials']),'materials')
