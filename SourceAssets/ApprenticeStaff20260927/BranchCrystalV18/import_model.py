"""Import V18 dependencies, preserve old mesh packages, update the active objects.
Runs in the existing editor via the batch mutex, or a background commandlet.
No PIE, screenshot, render, or asset acceptance pass is performed.
"""
import json,re
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
BASE='/Game/Weapons/ApprenticeStaff20260927'
DEST=BASE+'/BranchCrystalV18'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt_path=ROOT/'import-receipt.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'revision':18,'saved_assets':[],'installed':[],'backups':[]}
receipt.update({'complete':False,'tested':False,'rendered':False,'editor_started':False})
entries=json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before installing the staff model; no game session was stopped.')
targets={BASE+'/Meshes/'+e['name'] for e in entries}
conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if conflicts:raise RuntimeError('Unsaved staff meshes: '+', '.join(conflicts))

def record():receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    path=asset.get_path_name()
    if path not in receipt['saved_assets']:receipt['saved_assets'].append(path)
    record()
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def out(n,prop,channel=''):
    if not L.connect_material_property(n,channel,prop):raise RuntimeError('Material output failed: '+str(prop))
def wire(n,channel,target,pin):
    if not L.connect_material_expressions(n,channel,target,pin):raise RuntimeError('Material input failed: '+pin)
def scalar(m,v):return node(m,u.MaterialExpressionConstant,r=v)
def color(m,v):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
def finish(m):
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compilation failed: '+str(errors))
    save(m)
def import_new(source,name,destination,options=None):
    found=u.load_asset(destination+'/'+name)
    if found:return found
    task=u.AssetImportTask()
    for k,v in {'filename':str(source),'destination_path':destination,'destination_name':name,
        'automated':True,'replace_existing':False,'save':False}.items():task.set_editor_property(k,v)
    if options:task.set_editor_property('options',options)
    A.import_asset_tasks([task]);asset=u.load_asset(destination+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name)
    return asset

textures={}
for key in ('base_color','roughness','metallic','normal'):
    name='T_Staff_Branch_'+key
    asset=import_new(ROOT/f'Meshy/staff/downloads/texture_urls_0_{key}.png',name,DEST+'/Textures')
    asset.set_editor_property('srgb',key=='base_color')
    if key=='normal':
        asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        asset.set_editor_property('flip_green_channel',True)
    elif key!='base_color':
        asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        asset.set_editor_property('max_texture_size',2048)
    save(asset);textures[key]=asset

materials={}
for name,tint in [('M_Staff_BranchWoodV18',(1,1,1)),('M_Staff_PineV18',(.93,.82,.6)),('M_Staff_SandalV18',(.63,.37,.24))]:
    path=DEST+'/Materials/'+name;m=u.load_asset(path)
    if not m:
        m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        for key,prop in [('base_color',u.MaterialProperty.MP_BASE_COLOR),('roughness',u.MaterialProperty.MP_ROUGHNESS),('normal',u.MaterialProperty.MP_NORMAL)]:
            n=node(m,u.MaterialExpressionTextureSample,texture=textures[key],sampler_type=
                u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='base_color' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            if key=='base_color' and tint!=(1,1,1):
                multiply=node(m,u.MaterialExpressionMultiply);wire(n,'RGB',multiply,'A');wire(color(m,tint),'',multiply,'B');out(multiply,prop)
            else:out(n,prop,'RGB' if key in ('base_color','normal') else 'R')
        out(scalar(m,0),u.MaterialProperty.MP_METALLIC);finish(m)
    materials[name]=m
for name,cloud in [('M_Staff_QuartzV18',False),('M_Staff_QuartzInclusionV18',True)]:
    m=u.load_asset(DEST+'/Materials/'+name)
    if not m:
        m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('two_sided',cloud)
        out(color(m,(.79,.83,.79) if cloud else (.90,.93,.91)),u.MaterialProperty.MP_BASE_COLOR)
        out(scalar(m,0),u.MaterialProperty.MP_METALLIC)
        out(scalar(m,.34 if cloud else .105),u.MaterialProperty.MP_ROUGHNESS)
        out(scalar(m,.55),u.MaterialProperty.MP_SPECULAR)
        fresnel=node(m,u.MaterialExpressionFresnel,exponent=4.2,base_reflect_fraction=.03)
        scale=node(m,u.MaterialExpressionMultiply,const_b=.10 if cloud else .42);wire(fresnel,'',scale,'A')
        add=node(m,u.MaterialExpressionAdd,const_b=.055 if cloud else .13);wire(scale,'',add,'A');out(add,u.MaterialProperty.MP_OPACITY)
        # Restrained screen-space refraction for the near-camera crystal.
        out(scalar(m,1 if cloud else 1.025),u.MaterialProperty.MP_REFRACTION);finish(m)
    materials[name]=m
name='M_Staff_HempV18';m=u.load_asset(DEST+'/Materials/'+name)
if not m:
    m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    out(color(m,(.34,.235,.12)),u.MaterialProperty.MP_BASE_COLOR)
    out(scalar(m,.84),u.MaterialProperty.MP_ROUGHNESS);out(scalar(m,0),u.MaterialProperty.MP_METALLIC)
    out(scalar(m,.25),u.MaterialProperty.MP_SPECULAR);finish(m)
materials[name]=m
for name in ('M_Staff_ice','M_Staff_fire','M_Staff_light','M_Staff_electric','M_Staff_metal','M_Staff_RuneV2'):
    materials[name]=u.load_asset(BASE+'/Materials/'+name)
    if not materials[name]:raise RuntimeError('Existing option material missing: '+name)

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI()
    for k,v in {'import_mesh':True,'import_as_skeletal':False,'mesh_type_to_import':u.FBXImportType.FBXIT_STATIC_MESH,
        'automated_import_should_detect_type':False,'import_materials':False,'import_textures':False}.items():opt.set_editor_property(k,v)
    data=opt.get_editor_property('static_mesh_import_data')
    for k,v in {'combine_meshes':True,'auto_generate_collision':False,'import_uniform_scale':1,
        'convert_scene':True,'convert_scene_unit':False,'normal_import_method':u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}.items():data.set_editor_property(k,v)
    for entry in entries:
        new=import_new(entry['fbx'],entry['name'],DEST+'/Meshes',opt)
        for i,slot in enumerate(new.get_editor_property('static_materials')):
            name=str(slot.get_editor_property('imported_material_slot_name'))
            if name not in entry['materials']:name=entry['materials'][min(i,len(entry['materials'])-1)]
            name=re.sub(r'\.\d{3}$','',name)
            if name not in materials:raise RuntimeError('Unmapped source material '+name)
            new.set_material(i,materials[name])
        save(new)
    # Install after every versioned dependency has actually been imported/saved.
    # Copy geometry into the existing objects: no deletion, redirectors, live
    # reference changes, or reimport-unit multiplication.
    for entry in entries:
        if entry['name'] in receipt['installed']:continue
        path=BASE+'/Meshes/'+entry['name'];old=u.load_asset(path)
        backup=DEST+'/PreviousMeshes/'+entry['name']
        if old and not E.does_asset_exist(backup):
            preserved=E.duplicate_asset(path,backup)
            if not preserved:raise RuntimeError('Cannot preserve old staff mesh: '+path)
            save(preserved);receipt['backups'].append(backup);record()
        new=u.load_asset(DEST+'/Meshes/'+entry['name'])
        if old:
            read=u.GeometryScriptCopyMeshFromAssetOptions()
            dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(new,u.DynamicMesh(),read,u.GeometryScriptMeshReadLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot transfer imported geometry: '+path)
            slots=list(new.get_editor_property('static_materials'))
            write=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],use_build_scale=False)
            _,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,old,write,u.GeometryScriptMeshWriteLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write active mesh: '+path)
            old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'],0,'BranchCrystalV18')
        else:
            old=E.duplicate_asset(new.get_path_name(),path)
            if not old:raise RuntimeError('Cannot install '+path)
        save(old);receipt['installed'].append(entry['name']);record()
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt.update({'complete':True,'design':'Natural wood, clear quartz, upper hemp only','grip_source':'Preserved four existing grip meshes',
    'active_mesh_root':BASE+'/Meshes','versioned_mesh_root':DEST+'/Meshes','reference_views':'Design/staff_three_views.png'})
record()
print('STAFF_BRANCH_V18_SAVED meshes='+str(len(receipt['installed']))+' dependencies='+str(len(receipt['saved_assets'])))
