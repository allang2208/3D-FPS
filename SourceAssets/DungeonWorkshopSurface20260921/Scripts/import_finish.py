"""Import newly authored workshop assets without rebuilding any referenced material graph."""
from pathlib import Path
import json, re
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopSurface20260921')
DEST='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopSurface'
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
def link(a,pin,b,target):
    names=list(L.get_material_expression_input_names(b))
    if target not in names and len(names)==1:target=names[0]
    if not L.connect_material_expressions(a,pin,b,target):raise RuntimeError('Material input connection failed '+target)
def multiply(m,source,pin,value):
    n=node(m,u.MaterialExpressionMultiply);link(source,pin,n,'A');link(scalar(m,value),'',n,'B');return n
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
    elif 'Labels' in name:t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
    save(t);return t
for key,recipe in recipes.items():
    name='M_WSFinish_'+key+('_R2' if key=='ToolSteel' else '');path=DEST+'/Materials/'+name;m=u.load_asset(path)
    if not m:
        m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        if recipe.get('two_sided'):m.set_editor_property('two_sided',True)
        if recipe.get('masked'):
            m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
            m.set_editor_property('opacity_mask_clip_value',recipe.get('mask_clip',.333))
        if 'color' in recipe:output(color(m,recipe['color']),'BASE_COLOR')
        if 'emission' in recipe:output(color(m,recipe['emission']),'EMISSIVE_COLOR')
        channels={}
        for ch,filename in recipe.get('maps',{}).items():
            t=texture(filename,'T_WSFinish_'+key+'_'+ch,ch)
            s=node(m,u.MaterialExpressionTextureSample);s.texture=t
            s.sampler_type={'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,
                            'Roughness':u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                            'Metallic':u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                            'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL}[ch]
            pin='R' if ch in ('Roughness','Metallic') else '';source=s
            if ch=='BaseColor' and recipe.get('color_tint'):
                source=node(m,u.MaterialExpressionMultiply);link(s,'',source,'A');link(color(m,recipe['color_tint']),'',source,'B')
            if ch=='Roughness' and 'roughness_scale' in recipe:
                source=multiply(m,s,'R',recipe['roughness_scale']);add=node(m,u.MaterialExpressionAdd);link(source,'',add,'A');link(scalar(m,recipe.get('roughness_bias',0)),'',add,'B');source=add;pin=''
            if ch=='Normal' and 'normal_strength' in recipe:
                mult=node(m,u.MaterialExpressionMultiply);link(s,'',mult,'A');v=recipe['normal_strength'];link(color(m,[v,v,1]),'',mult,'B')
                source=node(m,u.MaterialExpressionNormalize);link(mult,'',source,'VectorInput')
            channels[ch]=(source,pin)
            output(source,{'BaseColor':'BASE_COLOR','Roughness':'ROUGHNESS','Metallic':'METALLIC','Normal':'NORMAL'}[ch],pin)
            if recipe.get('masked') and ch=='BaseColor':output(s,'OPACITY_MASK','A')
        if recipe.get('imperfection_mask'):
            tex=texture(recipe['imperfection_mask'],'T_WSFinish_QuixelImperfection','Mask')
            mask=node(m,u.MaterialExpressionTextureSample);mask.texture=tex;mask.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
            dark=multiply(m,mask,'R',.20);inv=node(m,u.MaterialExpressionOneMinus);link(dark,'',inv,'Input')
            tint=node(m,u.MaterialExpressionMultiply);link(channels['BaseColor'][0],channels['BaseColor'][1],tint,'A');link(inv,'',tint,'B');output(tint,'BASE_COLOR')
            rough=node(m,u.MaterialExpressionLinearInterpolate);link(channels['Roughness'][0],channels['Roughness'][1],rough,'A');link(mask,'G',rough,'B');link(scalar(m,.32),'',rough,'Alpha');output(rough,'ROUGHNESS')
            metal=node(m,u.MaterialExpressionLinearInterpolate);link(channels['Metallic'][0],channels['Metallic'][1],metal,'A');link(scalar(m,.40),'',metal,'B');link(multiply(m,mask,'R',.32),'',metal,'Alpha');output(metal,'METALLIC')
        if 'Roughness' not in recipe.get('maps',{}):output(scalar(m,recipe.get('roughness',.6)),'ROUGHNESS')
        if 'Metallic' not in recipe.get('maps',{}):output(scalar(m,recipe['metallic']),'METALLIC')
        output(scalar(m,.30),'SPECULAR')
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
        path=manifest['material_aliases'].get(slot_name) or receipt['materials'].get(slot_name.removeprefix('WSFinish_'))
        material=u.load_asset(path) if path else None
        if not material:raise RuntimeError('Missing material '+slot_name)
        mesh.set_material(i,material)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;mesh.set_editor_property('nanite_settings',ns)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['meshes'][name]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write()
print('WORKSHOP_SURFACE_ASSETS_SAVED',len(receipt['meshes']),len(receipt['materials']))
