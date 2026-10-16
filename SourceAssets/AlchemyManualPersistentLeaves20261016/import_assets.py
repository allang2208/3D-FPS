"""Save the skinned sheet template and its fixed-UV materials in the import host."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualPersistentLeaves20261016')
HOST=ROOT.parent/'PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated manual import host')
DEST='/Game/Building/PotionWorkbench20261015/ManualV9'
V5='/Game/Building/PotionWorkbench20261015/ManualV5'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report=dict(complete=False,saved=[],compile_errors={},runtime_tested=False)

def record():(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    if obj.get_path_name() not in report['saved']:report['saved'].append(obj.get_path_name())
    record()
def node(m,kind,**values):
    n=L.create_material_expression(m,kind)
    for key,value in values.items():n.set_editor_property(key,value)
    return n
def wire(a,out,b,pin):
    names=[str(x) for x in L.get_material_expression_input_names(b)]
    if pin not in names and len(names)==1:pin=names[0]
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def prop(n,p,out=''):
    if not L.connect_material_property(n,out,p):raise RuntimeError('Cannot connect material property')
def texture(m,name,kind='color'):
    t=u.load_asset(V5+'/Textures/'+name)
    if not t:raise RuntimeError('Missing paper texture '+name)
    return node(m,u.MaterialExpressionTextureSample,texture=t,sampler_type={
        'color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
        'mask':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[kind])
def material(name):
    m=u.load_asset(DEST+'/Materials/'+name) if E.does_asset_exist(DEST+'/Materials/'+name) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('used_with_skeletal_mesh',True)
    return m
def finish(m):
    errors=[str(x) for x in L.recompile_material(m)];report['compile_errors'][m.get_name()]=errors;record()
    if errors:raise RuntimeError(str(errors))
    save(m)

# Native skinning deforms positions AND tangent frames. There is deliberately no
# WPO, UV animation, time-dependent material, or front/back texture transition.
paper=material('M_BookLeafPaper')
uv=node(paper,u.MaterialExpressionTextureCoordinate)
region=node(paper,u.MaterialExpressionVectorParameter,parameter_name='PageOffset',default_value=u.LinearColor(0,0,0,1))
mask=node(paper,u.MaterialExpressionComponentMask,r=True,g=True,b=False,a=False);wire(region,'RGB',mask,'Input')
mul=node(paper,u.MaterialExpressionMultiply);wire(uv,'',mul,'A');wire(node(paper,u.MaterialExpressionConstant2Vector,r=.5,g=1.),'',mul,'B')
add=node(paper,u.MaterialExpressionAdd);wire(mul,'',add,'A');wire(mask,'',add,'B')
sample=node(paper,u.MaterialExpressionTextureSampleParameter2D,parameter_name='PageTexture',texture=u.load_asset(V5+'/Textures/T_ManualPaper'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
wire(add,'',sample,'UVs');prop(sample,u.MaterialProperty.MP_BASE_COLOR,'RGB')
prop(texture(paper,'T_ManualPaperNormal','normal'),u.MaterialProperty.MP_NORMAL,'RGB')
prop(texture(paper,'T_ManualPaperRoughness','mask'),u.MaterialProperty.MP_ROUGHNESS,'R')
glow=node(paper,u.MaterialExpressionMultiply,const_b=.025);wire(sample,'RGB',glow,'A');prop(glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
prop(node(paper,u.MaterialExpressionConstant,r=.22),u.MaterialProperty.MP_SPECULAR);finish(paper)
edge=material('M_BookLeafEdge')
prop(texture(edge,'T_ManualPageEdges'),u.MaterialProperty.MP_BASE_COLOR,'RGB')
prop(texture(edge,'T_ManualEdgeNormal','normal'),u.MaterialProperty.MP_NORMAL,'RGB')
prop(node(edge,u.MaterialExpressionConstant,r=.87),u.MaterialProperty.MP_ROUGHNESS);finish(edge)

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    for name,skeletal in [('SM_AlchemyManualBinding',False),('SK_BookLeafTemplate',True)]:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.import_mesh=True;opt.import_as_skeletal=skeletal;opt.import_animations=False
        opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
        data=opt.skeletal_mesh_import_data if skeletal else opt.static_mesh_import_data
        data.convert_scene=True;data.convert_scene_unit=True
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        if skeletal:
            data.set_editor_property('preserve_smoothing_groups',True)
            data.set_editor_property('use_t0_as_ref_pose',False)
        else:
            data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        task=u.AssetImportTask();task.filename=str(ROOT/'Export'/(name+'.fbx'))
        task.destination_path=DEST+'/Meshes';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
        A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/Meshes/'+name)
        if not mesh:raise RuntimeError('Import failed '+name)
        if skeletal:
            materials=mesh.get_editor_property('materials')
            for i,slot in enumerate(materials):
                slot.set_editor_property('material_interface',edge if str(slot.material_slot_name)=='M_BookPages' else paper)
                materials[i]=slot
            mesh.set_editor_property('materials',materials)
            save(mesh.skeleton)
            E.set_metadata_tag(mesh,'PaperTemplate','31-bone chain; fixed front/back UV; 0.032 cm thick')
        else:
            source=u.load_asset(V5+'/Meshes/SM_AlchemyManualOpen')
            slots={str(s.material_slot_name):s.material_interface for s in source.static_materials}
            for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,slots[str(slot.material_slot_name)])
            u.load_module('StaticMeshEditor');sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
            settings=sm.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True
            settings.generate_lightmap_u_vs=False;settings.recompute_normals=False;settings.recompute_tangents=True
            sm.set_lod_build_settings(mesh,0,settings)
            E.set_metadata_tag(mesh,'SourceAuthor','evildeer');E.set_metadata_tag(mesh,'SourceLicense','CC BY 4.0')
        save(mesh)
    report['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous));record()
u.log('MANUAL_PERSISTENT_LEAVES_SAVED')
