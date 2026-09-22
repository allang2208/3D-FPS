"""Import newly authored workshop assets without rebuilding any referenced material graph."""
from pathlib import Path
import json, re
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopSculpt20260921')
DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopSculpt'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Gameplay active; import deferred')
recipes=json.loads((ROOT/'Authored/material-manifest.json').read_text())
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
receipt={'stage':'importing','materials':{},'meshes':{},'tests_run':False,'screenshots_taken':False}
def write():(ROOT/'Receipts/asset-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(o):
    if not E.save_loaded_asset(o,False):raise RuntimeError('Save failed '+o.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def output(n,prop,pin=''):
    if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material connection failed '+prop)
def scalar(m,v):n=node(m,u.MaterialExpressionConstant);n.r=v;return n
def color(m,values):
    n=node(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*values,1));return n
def texture(filename,name,ch):
    folder=DEST+'/Textures';path=folder+'/'+name;t=u.load_asset(path)
    if t:return t
    task=u.AssetImportTask();task.filename=filename;task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);t=u.load_asset(path)
    if not t:raise RuntimeError('Texture import failed '+path)
    t.set_editor_property('srgb',ch=='BaseColor');t.set_editor_property('virtual_texture_streaming',False)
    if ch=='Normal':
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        t.set_editor_property('flip_green_channel',True)
    elif ch!='BaseColor':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(t);return t
for key,recipe in recipes.items():
    name='M_WSSculpt_'+key;path=DEST+'/Materials/'+name;m=u.load_asset(path)
    if not m:
        m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        if recipe.get('two_sided'):m.set_editor_property('two_sided',True)
        if recipe.get('masked'):
            m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
            m.set_editor_property('opacity_mask_clip_value',recipe.get('mask_clip',.333))
        if 'color' in recipe:output(color(m,recipe['color']),'BASE_COLOR')
        if 'emission' in recipe:output(color(m,recipe['emission']),'EMISSIVE_COLOR')
        for ch,filename in recipe.get('maps',{}).items():
            t=texture(filename,'T_WSSculpt_'+key+'_'+ch,ch)
            s=node(m,u.MaterialExpressionTextureSample);s.texture=t
            s.sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,
                            'Roughness':u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                            'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[ch]
            output(s,{'BaseColor':'BASE_COLOR','Roughness':'ROUGHNESS','Normal':'NORMAL'}[ch],'R' if ch=='Roughness' else '')
            if recipe.get('masked') and ch=='BaseColor':output(s,'OPACITY_MASK','A')
        if 'Roughness' not in recipe.get('maps',{}):output(scalar(m,recipe.get('roughness',.6)),'ROUGHNESS')
        output(scalar(m,recipe['metallic']),'METALLIC');output(scalar(m,.30),'SPECULAR')
        L.layout_material_expressions(m);L.recompile_material(m);save(m)
    receipt['materials'][key]=m.get_path_name();write()
for entry in manifest['objects']:
    name=entry['name'];folder=DEST+'/Meshes';path=folder+'/'+name;mesh=u.load_asset(path)
    if not mesh:
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
        options.import_as_skeletal=False;options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=options;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        slot_name=re.sub(r'[._][0-9]{3}$','',str(slot.get_editor_property('material_slot_name')))
        path=manifest['material_aliases'].get(slot_name) or receipt['materials'].get(slot_name.removeprefix('WSSculpt_'))
        material=u.load_asset(path) if path else None
        if not material:raise RuntimeError('Missing material '+slot_name)
        mesh.set_material(i,material)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['meshes'][name]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write()
print('WORKSHOP_COMPONENT_ASSETS_SAVED',len(receipt['meshes']),len(receipt['materials']))
