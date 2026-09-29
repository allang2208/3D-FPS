"""Import Blender V33 heads/materials, then install into the four existing paths.

Use the mutex bridge if FPSGAME is already open; otherwise run Python commandlet
with D3D12 for production shader compilation. No PIE, previews, or tests.
"""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
BASE='/Game/Weapons/ApprenticeStaff20260927'
DEST=BASE+'/CrystalCraftV33'
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
L=u.MaterialEditingLibrary
entries=json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8'))
recipes=json.loads((ROOT/'Export/materials.json').read_text(encoding='utf-8'))
resume='-crystalcraftresume' in u.SystemLibrary.get_command_line().lower()
receipt={'revision':33,'complete':False,'saved_assets':[],'installed':[],
         'backups':[],'compile_results':{},'runtime_tested':False,'preview_rendered':False}
if resume and (ROOT/'install-receipt.json').exists():
    receipt=json.loads((ROOT/'install-receipt.json').read_text(encoding='utf-8'))


def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name());record()


if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before installing crystal meshes.')
targets={BASE+'/Meshes/'+e['name'] for e in entries}
conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
           if p.get_name() in targets or p.get_name().startswith(DEST+'/')]
if conflicts:raise RuntimeError('Unsaved target crystal assets: '+', '.join(conflicts))


class Graph:
    def __init__(self,name):
        self.mat=u.load_asset(DEST+'/Materials/'+name)
        if not self.mat:
            self.mat=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        if not self.mat:raise RuntimeError('Cannot create '+name)
        # Delete a snapshot: the stock bulk deletion can leave stale expressions.
        for expression in list(L.get_material_expressions(self.mat)):
            L.delete_material_expression(self.mat,expression)
        self.mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
        self.mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        self.mat.set_editor_property('two_sided',False)
        self.index=0

    def node(self,cls,**props):
        n=L.create_material_expression(self.mat,cls,-1100+(self.index%6)*190,(self.index//6)*190)
        self.index+=1
        for k,v in props.items():n.set_editor_property(k,v)
        return n

    def scalar(self,v):return self.node(u.MaterialExpressionConstant,r=float(v))

    def color(self,v):return self.node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))

    def wire(self,a,b,pin,output=''):
        if pin=='Input':pin=str(L.get_material_expression_input_names(b)[0])
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)

    def output(self,n,prop,channel=''):
        if not L.connect_material_property(n,channel,prop):raise RuntimeError('Cannot connect material property '+str(prop))

    def mul(self,a,b,output=''):
        n=self.node(u.MaterialExpressionMultiply)
        self.wire(a,n,'A',output);self.wire(b,n,'B');return n

    def add(self,a,b):
        n=self.node(u.MaterialExpressionAdd);self.wire(a,n,'A');self.wire(b,n,'B');return n

    def channel(self,n,name):
        mask=self.node(u.MaterialExpressionComponentMask,r=name=='R',g=name=='G',b=name=='B',a=False)
        self.wire(n,mask,'Input');return mask

    def finish(self):
        errors=L.recompile_material(self.mat)
        receipt['compile_results'][self.mat.get_name()]=[str(e) for e in errors] if errors else []
        record()
        if errors:raise RuntimeError('Material compilation failed: '+str(errors))
        save(self.mat);return self.mat


textures={}
for kind,recipe in recipes.items():
    textures[kind]={}
    for channel,name in recipe['textures'].items():
        tex=u.load_asset(DEST+'/Textures/'+name) if resume else None
        if tex:
            textures[kind][channel]=tex
            continue
        task=u.AssetImportTask()
        for k,v in {'filename':str(ROOT/'Export/Textures'/(name+'.png')),
                    'destination_path':DEST+'/Textures','destination_name':name,
                    'automated':True,'replace_existing':True,'save':False}.items():
            task.set_editor_property(k,v)
        A.import_asset_tasks([task])
        tex=u.load_asset(DEST+'/Textures/'+name)
        if not tex:raise RuntimeError('Texture import failed '+name)
        tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal'
                                else u.TextureCompressionSettings.TC_MASKS if channel=='RGE'
                                else u.TextureCompressionSettings.TC_DEFAULT)
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        tex.set_editor_property('max_texture_size',1024)
        save(tex);textures[kind][channel]=tex


def sample(g,tex,channel):
    return g.node(u.MaterialExpressionTextureSample,texture=tex,
                  sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal'
                  else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='RGE'
                  else u.MaterialSamplerType.SAMPLERTYPE_COLOR)


def localized_emission(g,kind,mask,inner=False):
    colors={'Ice':(.10,.54,.75),'Magma':(1.,.095,.003),
            'Jade':(.09,.53,.20),'Storm':(.29,.13,1.)}
    tint=g.color(colors[kind])
    time=g.node(u.MaterialExpressionTime)
    sine=g.node(u.MaterialExpressionSine,period=4.8 if kind=='Magma' else 3.7 if kind=='Jade' else 2.9)
    g.wire(time,sine,'Input')
    wave=g.add(g.mul(sine,g.scalar(.5)),g.scalar(.5))
    if kind=='Storm':
        power=g.node(u.MaterialExpressionPower,const_exponent=14.)
        g.wire(wave,power,'Base')
        pulse=g.add(g.mul(power,g.scalar(.96)),g.scalar(.04))
    else:pulse=g.add(g.mul(wave,g.scalar(.20)),g.scalar(.80))
    idle={'Ice':.16,'Magma':4.0,'Jade':.26,'Storm':5.0 if inner else .45}[kind]
    ambient=g.mul(g.mul(mask,g.scalar(idle)),pulse)
    amount=g.node(u.MaterialExpressionScalarParameter,parameter_name='StaffLightAmount',default_value=0.)
    exposure=g.node(u.MaterialExpressionEyeAdaptationInverse,desc='StaffLightExposureV32')
    # Keep the lamp visible without bleaching the whole shell. A restrained floor
    # reveals the crystal body; most brightness stays on baked veins / inner arcs.
    light_mask=g.add(g.mul(mask,g.scalar(.82)),g.scalar(.035 if not inner else .07))
    illumination=g.mul(g.mul(amount,exposure),light_mask)
    g.output(g.mul(tint,g.add(ambient,illumination)),u.MaterialProperty.MP_EMISSIVE_COLOR)


materials={}
for kind,recipe in recipes.items():
    g=Graph(recipe['material'])
    maps={c:sample(g,t,c) for c,t in textures[kind].items()}
    base=maps['BaseColor'];packed=maps['RGE']
    g.output(base,u.MaterialProperty.MP_BASE_COLOR,'RGB')
    g.output(maps['Normal'],u.MaterialProperty.MP_NORMAL,'RGB')
    g.output(packed,u.MaterialProperty.MP_ROUGHNESS,'R')
    g.output(g.scalar(.78 if kind=='Mount' else 0.),u.MaterialProperty.MP_METALLIC)
    g.output(g.scalar(.5),u.MaterialProperty.MP_SPECULAR)
    if kind in ('Ice','Storm'):
        # Standard translucency writes the inverse-alpha coverage used by the
        # workbench/inventory capture, so these heads need no UI-only fallback.
        g.mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        g.mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        g.mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        g.output(packed,u.MaterialProperty.MP_OPACITY,'G')
    elif kind=='Jade':
        g.mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
        g.output(g.mul(base,g.color((.45,.78,.40)),'RGB'),u.MaterialProperty.MP_SUBSURFACE_COLOR)
        g.output(g.scalar(.58),u.MaterialProperty.MP_OPACITY)
    if kind!='Mount':localized_emission(g,kind,g.channel(packed,'B'))
    materials[recipe['material']]=g.finish()

for kind in ('Ice','Storm'):
    name='M_StaffCraft_'+kind+'Inner_V33';g=Graph(name)
    vertex=g.node(u.MaterialExpressionVertexColor)
    mask=g.channel(vertex,'R')
    if kind=='Storm':
        mix=g.node(u.MaterialExpressionLinearInterpolate)
        g.wire(g.color((.013,.007,.03)),mix,'A')
        g.wire(g.color((.18,.09,.42)),mix,'B')
        g.wire(mask,mix,'Alpha');g.output(mix,u.MaterialProperty.MP_BASE_COLOR)
    else:g.output(g.color((.12,.31,.36)),u.MaterialProperty.MP_BASE_COLOR)
    g.output(g.scalar(.34),u.MaterialProperty.MP_ROUGHNESS)
    localized_emission(g,kind,mask,inner=True)
    materials[name]=g.finish()

mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    options=u.FbxImportUI()
    for k,v in {'import_mesh':True,'import_as_skeletal':False,
                'mesh_type_to_import':u.FBXImportType.FBXIT_STATIC_MESH,
                'automated_import_should_detect_type':False,'import_materials':False,'import_textures':False}.items():
        options.set_editor_property(k,v)
    data=options.get_editor_property('static_mesh_import_data')
    for k,v in {'combine_meshes':True,'auto_generate_collision':False,'import_uniform_scale':1.,
                'convert_scene':True,'convert_scene_unit':False,
                'normal_import_method':u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                'vertex_color_import_option':u.VertexColorImportOption.REPLACE}.items():data.set_editor_property(k,v)
    for entry in entries:
        task=u.AssetImportTask()
        for k,v in {'filename':entry['fbx'],'destination_path':DEST+'/Meshes',
                    'destination_name':entry['name'],'automated':True,'replace_existing':True,
                    'save':False,'options':options}.items():task.set_editor_property(k,v)
        A.import_asset_tasks([task])
        mesh=u.load_asset(DEST+'/Meshes/'+entry['name'])
        if not mesh:raise RuntimeError('Mesh import failed '+entry['name'])
        for i,slot in enumerate(mesh.get_editor_property('static_materials')):
            name=str(slot.get_editor_property('imported_material_slot_name'))
            if name not in materials:name=entry['materials'][i]
            mesh.set_material(i,materials[name])
        settings=mesh_editor.get_lod_build_settings(mesh,0)
        settings.use_full_precision_u_vs=True
        mesh_editor.set_lod_build_settings(mesh,0,settings)
        save(mesh)

    # Install only after the complete material and mesh batch has been authored.
    for entry in entries:
        target=BASE+'/Meshes/'+entry['name']
        old=u.load_asset(target)
        if not old:raise RuntimeError('Missing original staff head '+target)
        backup=DEST+'/PreviousMeshes/'+entry['name']
        if not E.does_asset_exist(backup):
            preserved=E.duplicate_asset(target,backup)
            if not preserved:raise RuntimeError('Cannot preserve '+target)
            save(preserved)
        receipt['backups'].append(backup);record()
        mesh=u.load_asset(DEST+'/Meshes/'+entry['name'])
        dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),
            u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy '+target)
        slots=list(mesh.get_editor_property('static_materials'))
        write=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
            replace_materials=True,new_materials=[s.material_interface for s in slots],
            new_material_slot_names=[s.material_slot_name for s in slots],use_build_scale=False)
        _,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,old,write,u.GeometryScriptMeshWriteLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot install '+target)
        old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'],0,'CrystalCraftV33')
        settings=mesh_editor.get_lod_build_settings(old,0);settings.use_full_precision_u_vs=True
        mesh_editor.set_lod_build_settings(old,0,settings)
        save(old);receipt['installed'].append(target);record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
receipt['complete']=True
receipt['active_mesh_root']=BASE+'/Meshes'
receipt['white_quartz_changed']=False
receipt['gameplay_or_cpp_changed']=False
record()
print('STAFF_CRYSTAL_CRAFT_V33_SAVED heads='+str(len(receipt['installed'])))
