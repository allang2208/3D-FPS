"""Save three authored staff rune surfaces at existing runtime mesh references."""
import json,shutil,traceback
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
BASE='/Game/Weapons/ApprenticeStaff20260927';DEST=BASE+'/RuneRefinement20261009'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
entries=json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8'))
art=json.loads((ROOT/'Export/artwork.json').read_text(encoding='utf-8'))
palette=json.loads((ROOT/'palette.json').read_text(encoding='utf-8'))
receipt=dict(complete=False,saved_assets=[],installed=[],backups=[],compile_results={},
             runtime_tested=False,rendered=False,icons_changed=False,gameplay_changed=False)
def record():(ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(obj):
    if not obj or not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+str(obj))
    receipt['saved_assets'].append(obj.get_path_name());record()

class Graph:
    def __init__(self,name):
        self.mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        self.mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
        self.mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        self.mat.set_editor_property('two_sided',False)
        self.mat.set_editor_property('opacity_mask_clip_value',.333)
        for exp in list(L.get_material_expressions(self.mat)):L.delete_material_expression(self.mat,exp)
        self.index=0
    def node(self,cls,**props):
        n=L.create_material_expression(self.mat,cls,-1200+self.index%7*185,self.index//7*185);self.index+=1
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def scalar(self,value,name=None):
        return self.node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=float(value)) if name else self.node(u.MaterialExpressionConstant,r=float(value))
    def color(self,value,name=None):
        return self.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1)) if name else self.node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))
    def wire(self,a,b,pin,channel=''):
        if pin=='Input':pin=str(L.get_material_expression_input_names(b)[0])
        if not L.connect_material_expressions(a,channel,b,pin):raise RuntimeError('Cannot connect '+pin)
    def output(self,node,prop,channel=''):
        if not L.connect_material_property(node,channel,prop):raise RuntimeError('Cannot wire output '+str(prop))
    def mul(self,a,b,channel=''):
        n=self.node(u.MaterialExpressionMultiply);self.wire(a,n,'A',channel);self.wire(b,n,'B');return n
    def add(self,a,b):
        n=self.node(u.MaterialExpressionAdd);self.wire(a,n,'A');self.wire(b,n,'B');return n
    def channel(self,source,key):
        n=self.node(u.MaterialExpressionComponentMask,r=key=='R',g=key=='G',b=key=='B',a=key=='A');self.wire(source,n,'Input');return n
    def custom(self,code,output_type,inputs,description):
        node=self.node(u.MaterialExpressionCustom,code=code,output_type=output_type,description=description)
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        node.set_editor_property('inputs',pins)
        for name,source in inputs.items():self.wire(source,node,name)
        return node
    def finish(self):
        errors=L.recompile_material(self.mat)
        receipt['compile_results'][self.mat.get_name()]=[str(e) for e in errors] if errors else [];record()
        if errors:raise RuntimeError('Rune material compile failed '+str(errors))
        save(self.mat);return self.mat

def install():
    targets={folder+'/'+e['name'] for folder in [BASE+'/Meshes',BASE+'/BarkRebuildV21/Meshes'] for e in entries}
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
           if p.get_name() in targets or p.get_name().startswith(DEST+'/')]
    if dirty:raise RuntimeError('Unsaved rune targets preserved: '+', '.join(dirty))
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE is active; rune assets left unchanged')
    for target in sorted(targets):
        old=u.load_asset(target)
        if not old:raise RuntimeError('Missing original rune '+target)
        branch='Runtime' if '/BarkRebuildV21/' not in target else 'AuthorSource'
        backup=DEST+'/Before/'+branch+'/'+old.get_name()
        relative=Path(target.removeprefix('/Game/')+'.uasset');disk=ROOT/'Before/Content'/relative
        if not disk.exists():disk.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content'/relative,disk)
        if not E.does_asset_exist(backup):save(E.duplicate_asset(target,backup))
        receipt['backups'].append(dict(target=target,copy=backup,disk=str(disk)));record()
    materials={}
    for key,source in art.items():
        task=u.AssetImportTask()
        for k,v in dict(filename=source['source'],destination_path=DEST+'/Textures',destination_name=source['texture'],
                        automated=True,replace_existing=True,save=False).items():task.set_editor_property(k,v)
        A.import_asset_tasks([task]);texture=u.load_asset(DEST+'/Textures/'+source['texture'])
        if not texture:raise RuntimeError('Rune artwork import failed '+key)
        texture.set_editor_properties(dict(srgb=False,compression_settings=u.TextureCompressionSettings.TC_GRAYSCALE,
            power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO,max_texture_size=2048,never_stream=False,
            mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP))
        save(texture)
        name='M_StaffRuneCraft_'+key;g=Graph(name)
        uv=g.node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
        tex=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='RuneTexture',texture=texture,
                   sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        rect=source['uv_rect']
        field=g.custom((ROOT/'rune_field.hlsl').read_text(encoding='utf-8'),u.CustomMaterialOutputType.CMOT_FLOAT4,
            dict(UV=uv,RuneTexture=tex,ArtOrigin=g.color([rect[0],rect[1],0],'ArtOrigin'),
                 ArtSize=g.color([rect[2],rect[3],0],'ArtSize'),BevelStrength=g.scalar(.30,'BevelStrength')),
            'StaffRuneCraft: untouched art, derivative feather, shallow engraved edges')
        ink=g.channel(field,'A')
        base=g.color(palette[key]['metal'],'MetalColor')
        g.output(g.mul(base,g.add(g.scalar(.47),g.mul(ink,g.scalar(.53)))),u.MaterialProperty.MP_BASE_COLOR)
        g.output(g.scalar(.72,'Metallic'),u.MaterialProperty.MP_METALLIC)
        g.output(g.add(g.scalar(.265),g.mul(ink,g.scalar(.075))),u.MaterialProperty.MP_ROUGHNESS)
        g.output(g.scalar(.5),u.MaterialProperty.MP_SPECULAR)
        normal=g.custom('return normalize(float3(Field.g,Field.b,1.0));',u.CustomMaterialOutputType.CMOT_FLOAT3,
                        dict(Field=field),'StaffRuneCraft: micro relief on original bark normals')
        g.output(normal,u.MaterialProperty.MP_NORMAL)
        g.output(g.channel(field,'R'),u.MaterialProperty.MP_OPACITY_MASK)
        glow=g.custom((ROOT/'rune_glow.hlsl').read_text(encoding='utf-8'),u.CustomMaterialOutputType.CMOT_FLOAT3,
            dict(UV=uv,Field=field,T=g.node(u.MaterialExpressionTime),PreviewTime=g.scalar(-1,'PreviewTime'),
                 BreathSpeed=g.scalar({'eagle_eye_rune':.96,'crit_rune':1.13,'storm_rune':1.27}[key],'BreathSpeed'),
                 GlowColor=g.color(palette[key]['glow'],'GlowColor'),GlowStrength=g.scalar(.68,'GlowStrength'),
                 EmissionPeak=g.scalar(.85,'EmissionPeak')),
            'StaffRuneCraft: sword-style phase-offset breath; visible metal remains')
        g.output(glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
        materials[name]=g.finish()
    static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:
        options=u.FbxImportUI()
        for k,v in dict(import_mesh=True,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH,
                        automated_import_should_detect_type=False,import_materials=False,import_textures=False).items():options.set_editor_property(k,v)
        data=options.get_editor_property('static_mesh_import_data')
        for k,v in dict(combine_meshes=True,auto_generate_collision=False,import_uniform_scale=1.,convert_scene=True,convert_scene_unit=False,
                        normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(k,v)
        for entry in entries:
            task=u.AssetImportTask()
            for k,v in dict(filename=entry['fbx'],destination_path=DEST+'/Meshes',destination_name=entry['name'],automated=True,
                            replace_existing=True,save=False,options=options).items():task.set_editor_property(k,v)
            A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/Meshes/'+entry['name'])
            if not mesh:raise RuntimeError('Rune mesh import failed '+entry['name'])
            for i,slot in enumerate(mesh.static_materials):
                name=str(slot.get_editor_property('imported_material_slot_name'))
                if name not in materials:raise RuntimeError('Unknown rune material '+name)
                mesh.set_material(i,materials[name])
            settings=static.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True
            settings.recompute_normals=False;settings.recompute_tangents=True
            static.set_lod_build_settings(mesh,0,settings);save(mesh)
        for entry in entries:
            new=u.load_asset(DEST+'/Meshes/'+entry['name'])
            dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(new,u.DynamicMesh(),
                        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy rune mesh')
            slots=list(new.static_materials)
            write=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                replace_materials=True,new_materials=[s.material_interface for s in slots],
                new_material_slot_names=[s.material_slot_name for s in slots],use_build_scale=False)
            for folder in [BASE+'/Meshes',BASE+'/BarkRebuildV21/Meshes']:
                old=u.load_asset(folder+'/'+entry['name'])
                _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,old,write,u.GeometryScriptMeshWriteLOD())
                if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot install '+old.get_path_name())
                old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'],0,'RuneRefinement20261009')
                settings=static.get_lod_build_settings(old,0);settings.use_full_precision_u_vs=True
                settings.recompute_normals=False;settings.recompute_tangents=True
                static.set_lod_build_settings(old,0,settings);save(old)
                receipt['installed'].append(old.get_path_name());record()
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
    receipt['complete']=True;record()
    print('STAFF_RUNE_REFINEMENT_SAVED runtime_meshes=3 source_meshes=3 materials=3 art_textures=3 tested=false rendered=false',flush=True)
try:install()
except Exception:
    receipt['error']=traceback.format_exc();record();raise
