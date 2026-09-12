"""Import surface revision into existing runtime mesh; retain animation skeleton."""
import unreal as u
from pathlib import Path
O=Path(__file__).parent
P='/Game/Weapons/QBZ191'
lib=u.MaterialEditingLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
mesh=u.load_asset(P+'/Calibrated/SK_QBZ191_Manny')
bindings={str(s.material_slot_name):s.material_interface for s in mesh.get_editor_property('materials')}
materials={}
for part,texture_part in [('Body','Body'),('Magazine','Magazine'),('Irons','Body')]:
    name='M_QBZ191_'+part+'_SurfacePolish'
    path=P+'/SurfacePolish/'+name
    m=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else assets.create_asset(name,P+'/SurfacePolish',u.Material,u.MaterialFactoryNew())
    lib.delete_all_material_expressions(m)
    lib.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    def node(cls):return lib.create_material_expression(m,cls)
    def const(value):
        n=node(u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
    def wire(a,out,b,inp):lib.connect_material_expressions(a,out,b,inp)
    for kind,prop in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Metallic',u.MaterialProperty.MP_METALLIC),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Normal',u.MaterialProperty.MP_NORMAL)]:
        tex=u.load_asset(P+'/Textures/T_QBZ191_'+texture_part+'_'+kind)
        n=node(u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        output='RGB' if kind in ('BaseColor','Normal') else 'R'
        if kind=='Roughness':
            # Preserve painted roughness variation, while softening chalky highlights.
            mul=node(u.MaterialExpressionMultiply);wire(n,'R',mul,'A');wire(const(.8),'',mul,'B')
            add=node(u.MaterialExpressionAdd);wire(mul,'',add,'A');wire(const(.06),'',add,'B')
            clamp=node(u.MaterialExpressionClamp);wire(add,'',clamp,'Input')
            clamp.set_editor_property('min_default',.38 if part=='Irons' else .28)
            clamp.set_editor_property('max_default',.78)
            n=clamp;output=''
        elif kind=='Normal':
            # Keep source microdetail; reduce over-strong baked gradients at close range.
            flat=node(u.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',u.LinearColor(0,0,1,1))
            blend=node(u.MaterialExpressionLinearInterpolate);wire(flat,'',blend,'A');wire(n,'RGB',blend,'B')
            wire(const(.65 if part=='Irons' else .85),'',blend,'Alpha')
            n=blend;output=''
        lib.connect_material_property(n,output,prop)
    lib.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m,False);materials[part]=m
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False
opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
opt.skeleton=mesh.skeleton
opt.skeletal_mesh_import_data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
opt.skeletal_mesh_import_data.set_editor_property('normal_generation_method',u.FBXNormalGenerationMethod.MIKK_T_SPACE)
task=u.AssetImportTask();task.filename=str(O/'SK_QBZ191_Manny.fbx')
task.destination_path=P+'/Calibrated';task.destination_name='SK_QBZ191_Manny'
task.automated=True;task.replace_existing=True;task.save=True;task.options=opt
assets.import_asset_tasks([task])
mesh=u.load_asset(P+'/Calibrated/SK_QBZ191_Manny')
slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):
    name=str(s.material_slot_name)
    s.material_interface=materials['Irons'] if 'QBZ191_Irons' in name else materials['Magazine'] if 'QBZ191_Magazine' in name else materials['Body'] if 'QBZ191' in name else bindings[name]
    slots[i]=s
mesh.set_editor_property('materials',slots)
u.EditorAssetLibrary.save_loaded_asset(mesh,False)
u.log('QBZ_SURFACE_IMPORT_COMPLETE')
