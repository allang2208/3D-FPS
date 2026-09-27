"""Create/save this revision's models and materials in an isolated UE folder.
Run with UnrealEditor-Cmd -run=pythonscript -script=...; no level/PIE/render work.
"""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/PotionTiersBlender20260926')
SPEC=json.loads((OUT/'design.json').read_text(encoding='utf-8'))
MANIFEST=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
DEST=SPEC['ue_folder']
TOOLS=u.AssetToolsHelpers.get_asset_tools()
LIB=u.MaterialEditingLibrary
EAL=u.EditorAssetLibrary
RECEIPT={'materials':{},'meshes':{},'saved':False,'runtime_tested':False}


def save(asset):
    if not EAL.save_loaded_asset(asset):raise RuntimeError('Save failed: '+asset.get_path_name())


def node(mat,kind):return LIB.create_material_expression(mat,kind)


def connect(a,out,b,pin):
    if not LIB.connect_material_expressions(a,out,b,pin):raise RuntimeError('Could not connect material pin '+pin)


def prop(a,out,kind):
    if not LIB.connect_material_property(a,out,kind):raise RuntimeError('Could not connect material property '+str(kind))


def scalar(mat,value,kind):
    n=node(mat,u.MaterialExpressionConstant);n.r=value;prop(n,'',kind);return n


def color(mat,value):
    n=node(mat,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*value,1);return n


def material(name,base,rough,metal=0,transmission=None,liquid=False):
    path=DEST+'/Materials/M_Potion_'+name
    existing=u.load_asset(path)
    if existing:return existing
    mat=TOOLS.create_asset('M_Potion_'+name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    c=color(mat,base)
    if liquid:
        c=node(mat,u.MaterialExpressionVectorParameter)
        c.set_editor_property('parameter_name','LiquidColor')
        c.set_editor_property('default_value',u.LinearColor(*base,1))
    prop(c,'',u.MaterialProperty.MP_BASE_COLOR)
    scalar(mat,rough,u.MaterialProperty.MP_ROUGHNESS);scalar(mat,metal,u.MaterialProperty.MP_METALLIC)
    if transmission is not None:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        # Hollow glass has both outer and inner geometry; do not double-render backs.
        mat.set_editor_property('two_sided',False)
        thin=node(mat,u.MaterialExpressionThinTranslucentMaterialOutput)
        tint=c if liquid else color(mat,transmission)
        connect(tint,'',thin,str(LIB.get_material_expression_input_names(thin)[0]))
        scalar(mat,0,u.MaterialProperty.MP_OPACITY)
    return mat


def compile_save(mat):
    LIB.recompile_material(mat)
    save(mat);RECEIPT['materials'][mat.get_name()]=mat.get_path_name()


def texture(kind):
    name='T_PotionCork_'+kind;path=DEST+'/Textures/'+name
    tex=u.load_asset(path)
    if not tex:
        task=u.AssetImportTask();task.filename=str(OUT/'Textures'/(name+'.png'))
        task.destination_path=DEST+'/Textures';task.destination_name=name;task.automated=True;task.save=False
        TOOLS.import_asset_tasks([task]);tex=u.load_asset(path)
    if not isinstance(tex,u.Texture2D):raise RuntimeError('Texture import failed: '+name)
    tex.set_editor_property('srgb',kind=='BaseColor')
    if kind=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif kind=='Roughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);return tex


def main():
    materials={
        'Glass':material('Glass',(.965,.985,.99),.075,transmission=(.965,.985,.99)),
        'Liquid':material('Liquid',(.60,.045,.065),.10,transmission=(.60,.045,.065),liquid=True),
        'Cork':material('Cork',(.44,.245,.095),.82),
        'Pewter':material('Pewter',(.46,.48,.50),.29,1),
        'Silver':material('Silver',(.67,.70,.74),.22,1),
        'Brass':material('Brass',(.63,.43,.17),.24,1)
    }
    cork=materials['Cork']
    # Creating this revision only; on a resumable import avoid stacking expressions.
    if LIB.get_num_material_expressions(cork)<6:
        for kind,p in [('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Normal',u.MaterialProperty.MP_NORMAL)]:
            tex=texture(kind);n=node(cork,u.MaterialExpressionTextureSample);n.texture=tex
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            prop(n,'RGB' if kind!='Roughness' else 'R',p)
    for mat in materials.values():compile_save(mat)
    liquid_master=materials['Liquid']
    for family,tint in [('Health',(.60,.045,.065)),('Mana',(.025,.38,.78))]:
        name='MI_Potion_'+family
        mi=u.load_asset(DEST+'/Materials/'+name) or TOOLS.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        LIB.set_material_instance_parent(mi,liquid_master)
        LIB.set_material_instance_vector_parameter_value(mi,'LiquidColor',u.LinearColor(*tint,1))
        LIB.update_material_instance(mi);save(mi)
        RECEIPT['materials'][name]=mi.get_path_name()
        if family=='Health':materials['Liquid']=mi
    for tier,entry in MANIFEST['tiers'].items():
        for part,data in entry['parts'].items():
            name=data['name'];path=DEST+'/'+name
            # A resumed run never deletes a successfully saved revision asset.
            mesh=u.load_asset(path)
            if not mesh:
                opts=u.FbxImportUI();opts.import_mesh=True;opts.import_as_skeletal=False
                opts.import_materials=False;opts.import_textures=False
                opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
                imp=opts.static_mesh_import_data
                imp.combine_meshes=False;imp.import_mesh_lo_ds=True
                imp.auto_generate_collision=False;imp.one_convex_hull_per_ucx=True
                imp.generate_lightmap_u_vs=True
                imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
                task=u.AssetImportTask();task.filename=data['file'];task.destination_path=DEST;task.destination_name=name
                task.automated=True;task.replace_existing=False;task.save=False;task.options=opts
                TOOLS.import_asset_tasks([task]);mesh=u.load_asset(path)
            if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Mesh import failed: '+name)
            for index,slot in enumerate(mesh.static_materials):
                key=str(slot.material_slot_name)
                if key not in materials:raise RuntimeError('Unknown material slot '+key+' on '+name)
                mesh.set_material(index,materials[key])
            nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
            save(mesh)
            RECEIPT['meshes'][name]={'asset':mesh.get_path_name(),'saved':True,'source':data['file'],'lod_count':mesh.get_num_lods(),'tier':tier,'part':part}
            (OUT/'import_receipt.json').write_text(json.dumps(RECEIPT,indent=2),encoding='utf-8')
    RECEIPT['saved']=True
    (OUT/'import_receipt.json').write_text(json.dumps(RECEIPT,indent=2),encoding='utf-8')
    u.log('POTION_TIER_ASSETS_SAVED '+str(len(RECEIPT['meshes'])))


main()
