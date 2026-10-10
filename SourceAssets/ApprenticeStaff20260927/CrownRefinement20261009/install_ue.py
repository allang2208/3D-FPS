"""Compile/import/save four crowns at their stable paths. No test or preview."""
import json, traceback, shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Weapons/ApprenticeStaff20260927'
DEST=BASE+'/CrownRefinement20261009'
E=u.EditorAssetLibrary; A=u.AssetToolsHelpers.get_asset_tools(); L=u.MaterialEditingLibrary
entries=json.loads((ROOT/'Export/meshes.json').read_text(encoding='utf-8'))
specs=json.loads((ROOT/'Export/materials.json').read_text(encoding='utf-8'))
receipt=dict(complete=False,saved_assets=[],installed=[],backups=[],compile_results={},
             runtime_tested=False,rendered=False,icons_changed=False,gameplay_changed=False)
def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+str(asset))
    receipt['saved_assets'].append(asset.get_path_name());record()

class Graph:
    def __init__(self,name):
        self.mat=u.load_asset(DEST+'/Materials/'+name) or A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        self.mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
        self.mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        self.mat.set_editor_property('two_sided',False)
        for e in list(L.get_material_expressions(self.mat)):L.delete_material_expression(self.mat,e)
        self.index=0
    def node(self,cls,**props):
        n=L.create_material_expression(self.mat,cls,-1200+self.index%7*185,self.index//7*190);self.index+=1
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def scalar(self,v):return self.node(u.MaterialExpressionConstant,r=float(v))
    def color(self,v):return self.node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    def wire(self,a,b,pin,channel=''):
        if pin=='Input':pin=str(L.get_material_expression_input_names(b)[0])
        if not L.connect_material_expressions(a,channel,b,pin):raise RuntimeError('Material connection failed '+pin)
    def output(self,n,p,channel=''):
        if not L.connect_material_property(n,channel,p):raise RuntimeError('Material output failed '+str(p))
    def mul(self,a,b,channel=''):
        n=self.node(u.MaterialExpressionMultiply);self.wire(a,n,'A',channel);self.wire(b,n,'B');return n
    def add(self,a,b):
        n=self.node(u.MaterialExpressionAdd);self.wire(a,n,'A');self.wire(b,n,'B');return n
    def mix(self,a,b,t,channel=''):
        n=self.node(u.MaterialExpressionLinearInterpolate);self.wire(a,n,'A');self.wire(b,n,'B');self.wire(t,n,'Alpha',channel);return n
    def finish(self):
        errors=L.recompile_material(self.mat)
        receipt['compile_results'][self.mat.get_name()]=[str(e) for e in errors] if errors else [];record()
        if errors:raise RuntimeError('Material compile failed '+str(errors))
        save(self.mat);return self.mat

def install():
    targets={BASE+'/Meshes/'+e['name'] for e in entries}
    targets|={BASE+'/BarkRebuildV21/Meshes/'+e['name'] for e in entries}
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
           if p.get_name() in targets or p.get_name().startswith(DEST+'/')]
    if dirty:raise RuntimeError('Unsaved crown targets preserved: '+', '.join(dirty))
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE is active; crown installation not started')
    # Freeze all prior packages before any runtime crown is changed.
    for target in sorted(targets):
        old=u.load_asset(target)
        if not old:raise RuntimeError('Missing original crown '+target)
        branch='Runtime' if '/BarkRebuildV21/' not in target else 'AuthorSource'
        backup=DEST+'/Before/'+branch+'/'+old.get_name()
        disk=ROOT/'Before/Content'/Path(target.removeprefix('/Game/')+'.uasset')
        if not disk.exists():
            disk.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PROJECT/'Content'/Path(target.removeprefix('/Game/')+'.uasset'),disk)
        if not E.does_asset_exist(backup):save(E.duplicate_asset(target,backup))
        receipt['backups'].append(dict(target=target,copy=backup,disk=str(disk)));record()
    textures={}
    for name in ['T_Crown_Surface','T_Crown_Normal']:
        task=u.AssetImportTask()
        for k,v in dict(filename=str(ROOT/'Export/Textures'/(name+'.png')),destination_path=DEST+'/Textures',
                        destination_name=name,automated=True,replace_existing=True,save=False).items():task.set_editor_property(k,v)
        A.import_asset_tasks([task]);tex=u.load_asset(DEST+'/Textures/'+name)
        if not tex:raise RuntimeError('Texture import failed '+name)
        tex.set_editor_property('srgb',False)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if name.endswith('Normal') else u.TextureCompressionSettings.TC_MASKS)
        if name.endswith('Normal'):tex.set_editor_property('flip_green_channel',True)
        tex.set_editor_property('max_texture_size',512);save(tex);textures[name]=tex
    materials={}
    for key,s in specs.items():
        name='M_StaffCrown_'+key;g=Graph(name)
        packed=g.node(u.MaterialExpressionTextureSample,texture=textures['T_Crown_Surface'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        normal=g.node(u.MaterialExpressionTextureSample,texture=textures['T_Crown_Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        vc=g.node(u.MaterialExpressionVertexColor)
        color=g.color(s['color'])
        oxide=g.color([v*.34 for v in s['color']])
        patina=g.mul(packed,g.scalar(.46 if s['metallic']>.5 else .19),'G')
        base=g.mix(color,oxide,patina)
        edge=g.color([min(.75,v*1.26+.025) for v in s['color']])
        base=g.mix(base,edge,g.mul(vc,g.scalar(.55),'R'))
        g.output(base,u.MaterialProperty.MP_BASE_COLOR)
        rough=g.add(g.scalar(s['roughness']-.07),g.mul(packed,g.scalar(.14),'R'))
        g.output(g.add(rough,g.mul(packed,g.scalar(.10),'G')),u.MaterialProperty.MP_ROUGHNESS)
        g.output(g.mul(g.scalar(s['metallic']),g.mix(g.scalar(1),g.scalar(.54),patina)),u.MaterialProperty.MP_METALLIC)
        g.output(g.scalar(.5),u.MaterialProperty.MP_SPECULAR)
        g.output(normal,u.MaterialProperty.MP_NORMAL,'RGB')
        if s['emission']:
            glow=g.mul(g.mul(vc,g.scalar(s['emission']),'B'),g.color(s['color']))
            g.output(glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
        materials[name]=g.finish()
    editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:
        options=u.FbxImportUI()
        for k,v in dict(import_mesh=True,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH,
                        automated_import_should_detect_type=False,import_materials=False,import_textures=False).items():options.set_editor_property(k,v)
        data=options.get_editor_property('static_mesh_import_data')
        for k,v in dict(combine_meshes=True,auto_generate_collision=False,import_uniform_scale=1.,convert_scene=True,convert_scene_unit=False,
                        normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                        vertex_color_import_option=u.VertexColorImportOption.REPLACE).items():data.set_editor_property(k,v)
        for entry in entries:
            task=u.AssetImportTask()
            for k,v in dict(filename=entry['fbx'],destination_path=DEST+'/Meshes',destination_name=entry['name'],
                            automated=True,replace_existing=True,save=False,options=options).items():task.set_editor_property(k,v)
            A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/Meshes/'+entry['name'])
            if not mesh:raise RuntimeError('Mesh import failed '+entry['name'])
            for i,slot in enumerate(mesh.static_materials):
                name=str(slot.get_editor_property('imported_material_slot_name'))
                if name not in materials:raise RuntimeError('Unknown crown material slot '+name)
                mesh.set_material(i,materials[name])
            settings=editor.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True
            settings.recompute_normals=False;settings.recompute_tangents=True
            editor.set_lod_build_settings(mesh,0,settings);save(mesh)
        for entry in entries:
            new=u.load_asset(DEST+'/Meshes/'+entry['name'])
            dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(new,u.DynamicMesh(),
                u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot transfer '+entry['name'])
            slots=list(new.static_materials)
            write=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
                replace_materials=True,new_materials=[s.material_interface for s in slots],
                new_material_slot_names=[s.material_slot_name for s in slots],use_build_scale=False)
            for folder in [BASE+'/Meshes',BASE+'/BarkRebuildV21/Meshes']:
                old=u.load_asset(folder+'/'+entry['name'])
                _,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,old,write,u.GeometryScriptMeshWriteLOD())
                if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot install '+old.get_path_name())
                old.get_editor_property('asset_import_data').scripted_add_filename(entry['fbx'],0,'CrownRefinement20261009')
                settings=editor.get_lod_build_settings(old,0);settings.use_full_precision_u_vs=True
                settings.recompute_normals=False;settings.recompute_tangents=True
                editor.set_lod_build_settings(old,0,settings);save(old)
                receipt['installed'].append(old.get_path_name());record()
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
    receipt['complete']=True;record()
    print('STAFF_CROWNS_SAVED runtime_meshes=4 source_meshes=4 materials=7 textures=2 tested=false rendered=false',flush=True)
try:install()
except Exception:
    receipt['error']=traceback.format_exc();record();raise
