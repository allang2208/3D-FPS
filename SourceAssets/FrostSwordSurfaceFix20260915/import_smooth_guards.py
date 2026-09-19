"""Import welded guard revisions with one stock-bronze blend material."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).parent
D='/Game/Weapons/FrostCrystalSword20260915/GuardsSmooth20260915'
F='/Game/Weapons/FrostCrystalSword20260915'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
material=u.load_asset(D+'/M_FrostCrystalSword_SeamlessBronze') or A.create_asset('M_FrostCrystalSword_SeamlessBronze',D,u.Material,u.MaterialFactoryNew())
E.delete_all_material_expressions(material)
E.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
def node(cls,**props):
    n=E.create_material_expression(material,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,pin,b,target):
    if target=='Input':target=str(E.get_material_expression_input_names(b)[0])
    if not E.connect_material_expressions(a,pin,b,target):raise RuntimeError('Connect '+target)
uv0=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
uv1=node(u.MaterialExpressionTextureCoordinate,coordinate_index=1)
color=node(u.MaterialExpressionVertexColor)
for label,prop,sampler,channel in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR,'RGB'),('Metallic',u.MaterialProperty.MP_METALLIC,u.MaterialSamplerType.SAMPLERTYPE_MASKS,'R'),('Roughness',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS,'R')]:
    texture=u.load_asset(F+'/T_FrostCrystalSword_'+label)
    a=node(u.MaterialExpressionTextureSample,texture=texture,sampler_type=sampler)
    b=node(u.MaterialExpressionTextureSample,texture=texture,sampler_type=sampler)
    link(uv0,'',a,'UVs');link(uv1,'',b,'UVs')
    blend=node(u.MaterialExpressionLinearInterpolate)
    link(a,channel,blend,'A');link(b,channel,blend,'B');link(color,'R',blend,'Alpha')
    E.connect_material_property(blend,'',prop)
normal=node(u.MaterialExpressionTextureSample,texture=u.load_asset(F+'/T_FrostCrystalSword_Normal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
link(uv0,'',normal,'UVs')
flat=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,0))
blend=node(u.MaterialExpressionLinearInterpolate);link(normal,'RGB',blend,'A');link(flat,'',blend,'B');link(color,'R',blend,'Alpha')
norm=node(u.MaterialExpressionNormalize);link(blend,'',norm,'Input');E.connect_material_property(norm,'',u.MaterialProperty.MP_NORMAL)
E.layout_material_expressions(material);E.recompile_material(material);u.EditorAssetLibrary.save_loaded_asset(material,False)
donor=u.load_asset(F+'/SK_FrostCrystalSword_Manny')
bindings={str(s.material_slot_name):s.material_interface for s in donor.get_editor_property('materials')}
bindings['M_FrostCrystalSword_SeamlessBronze']=material
receipt=[]
for id in ['bastion_guard','riposte_guard','light_guard']:
    for skeletal in [False,True]:
        name=('SK_' if skeletal else 'SM_')+'FrostCrystalSword_'+id
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False
        opt.import_animations=False;opt.create_physics_asset=False
        data=opt.skeletal_mesh_import_data if skeletal else opt.static_mesh_import_data
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        if skeletal:
            opt.skeleton=donor.skeleton;data.set_editor_property('update_skeleton_reference_pose',False)
        else:
            data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        task=u.AssetImportTask();task.filename=str(P/id/(name+'.fbx'));task.destination_path=D+'/'+id;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
        mesh=u.load_asset(D+'/'+id+'/'+name)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Import failed '+name)
        slots=mesh.get_editor_property('materials' if skeletal else 'static_materials')
        for i,slot in enumerate(slots):
            source=str(slot.material_slot_name)
            if source not in bindings:raise RuntimeError('Unmapped material '+source)
            if skeletal:slot.material_interface=bindings[source];slots[i]=slot
            else:mesh.set_material(i,bindings[source])
        if skeletal:
            mesh.set_editor_property('materials',slots)
            mesh.set_editor_property('positive_bounds_extension',u.Vector(120,120,120));mesh.set_editor_property('negative_bounds_extension',u.Vector(120,120,120))
        u.EditorAssetLibrary.save_loaded_asset(mesh,False)
        receipt.append({'source':task.filename,'asset':mesh.get_path_name()})
(P/'guard_import_receipt.json').write_text(json.dumps({'assets':receipt,'material':material.get_path_name(),'skeleton':donor.skeleton.get_path_name()},indent=2))
u.log('FROST_SMOOTH_GUARDS_IMPORTED')
