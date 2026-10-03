"""Produce the dedicated close-view finishes and softer container post-process."""
from pathlib import Path
import unreal as u

def build_materials(root,base):
    E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();made=[]
    colors=dict(JugPlastic=((.105,.35,.61),.18),JugWater=((.025,.25,.43),.08),
        CueMaple=((.54,.36,.18),.38),CueGrip=((.045,.038,.026),.75),CueTip=((.025,.19,.35),.86),
        PoolIvory=((.88,.86,.75),.19),PoolBlue=((.015,.11,.55),.16),PoolRed=((.52,.018,.014),.18),
        TVGlass=((.009,.018,.025),.085),CarpetBinding=((.008,.021,.048),.92))
    for key,(color,rough) in colors.items():
        path=base+'/Materials/M_Staff_'+key+'_V4';mat=u.load_asset(path)
        if not mat:
            folder,name=path.rsplit('/',1);E.make_directory(folder)
            mat=A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
            if key in ('JugPlastic','JugWater'):
                mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
                mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
                n=M.create_material_expression(mat,u.MaterialExpressionConstant,-250,250)
                n.set_editor_property('r',.34 if key=='JugPlastic' else .42)
                M.connect_material_property(n,'',u.MaterialProperty.MP_OPACITY)
            n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-250,0)
            n.set_editor_property('constant',u.LinearColor(*color,1));M.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
            n=M.create_material_expression(mat,u.MaterialExpressionConstant,-250,100);n.set_editor_property('r',rough)
            M.connect_material_property(n,'',u.MaterialProperty.MP_ROUGHNESS)
            n=M.create_material_expression(mat,u.MaterialExpressionConstant,-250,180);n.set_editor_property('r',.65)
            M.connect_material_property(n,'',u.MaterialProperty.MP_SPECULAR)
            if key in ('CueMaple','CueGrip','CarpetBinding'):
                coord=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-800,360)
                custom=M.create_material_expression(mat,u.MaterialExpressionCustom,-500,360)
                inp=u.CustomInput();inp.set_editor_property('input_name','UV');custom.set_editor_property('inputs',[inp])
                custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
                custom.set_editor_property('code','float grain=.91+.09*sin(UV.x*105+sin(UV.y*19)*2);return float3(.54,.36,.18)*grain;' if key=='CueMaple'
                    else 'float w=.84+.16*sin(UV.x*170)*sin(UV.y*170);return float3'+str(color)+'*w;')
                M.connect_material_expressions(coord,'',custom,'UV');M.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
            errors=M.recompile_material(mat)
            if errors:raise RuntimeError('Material production failed '+path+str(errors))
            M.get_statistics(mat)
            if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
        made.append(path)
    # Reuse the proven graph wiring, with this batch's shader and gentler colors.
    script=root/'Scripts/build_container_outline_v1.py';code=script.read_text('utf8')
    code=code.replace('M_Staff_ContainerOutline_V1','M_Staff_ContainerOutline_V4')
    code=code.replace('SearchContainersV1/container_outline.hlsl','ScenePolishV4/container_outline.hlsl')
    code=code.replace("'default_value',1.6","'default_value',2.2")
    code=code.replace('(.08,1,.19,1)','(.10,.80,.24,1)').replace('(1,.77,.055,1)','(.93,.69,.12,1)')
    env={};exec(compile(code,str(script),'exec'),env);outline=env['build_outline'](root,base)
    return made,outline
