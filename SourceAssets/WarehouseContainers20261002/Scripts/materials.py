"""Own coating materials and physically proportioned logistics labels."""
from pathlib import Path
import hashlib
import unreal as u

def create(root,base,report):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
    E.make_directory(base+'/Materials');E.make_directory(base+'/Textures')
    source=root/'Authored/T_Warehouse_Labels.png';path=base+'/Textures/T_Warehouse_Labels';tex=u.load_asset(path)
    if not tex:
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=base+'/Textures';task.destination_name='T_Warehouse_Labels'
        task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(path)
        if not tex:raise RuntimeError('Shipping label import failed')
        tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',False)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        if not E.save_loaded_asset(tex,False):raise RuntimeError('Shipping label save failed')
    label=base+'/Materials/M_Warehouse_Labels';mat=u.load_asset(label)
    if not mat:
        mat=A.create_asset('M_Warehouse_Labels',base+'/Materials',u.Material,u.MaterialFactoryNew());mat.set_editor_property('used_with_nanite',True)
        n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        r=M.create_material_expression(mat,u.MaterialExpressionConstant);r.set_editor_property('r',.78)
        M.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
        errors=list(M.recompile_material(mat))
        if errors:raise RuntimeError('Label material compile failed '+str(errors))
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Label material save failed')
    report['materials']=[label]
    for key,color,metallic,rough in [('PolymerGreen',(.13,.20,.145),0.,.61),('PolymerBlue',(.055,.14,.23),0.,.60),
        ('PolymerGray',(.24,.25,.23),0.,.65),('ToolPaint',(.10,.17,.15),.12,.46),('CasePaint',(.16,.18,.20),.55,.40)]:
        path=base+'/Materials/M_Warehouse_'+key;mat=u.load_asset(path)
        if not mat:
            mat=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            mat.set_editor_property('used_with_nanite',True)
            uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-900,0)
            wear=M.create_material_expression(mat,u.MaterialExpressionCustom,-650,0)
            inp=u.CustomInput();inp.set_editor_property('input_name','UV');wear.set_editor_property('inputs',[inp])
            wear.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
            wear.set_editor_property('code','float2 q=floor(UV*91);float n=frac(sin(dot(q,float2(127.1,311.7)))*43758.5453);float s=sin(UV.x*109+sin(UV.y*39));return saturate(n*.3+s*.1+.2);')
            M.connect_material_expressions(uv,'',wear,'UV')
            c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-700,180)
            c.set_editor_property('constant',u.LinearColor(*color,1))
            lerp=M.create_material_expression(mat,u.MaterialExpressionLinearInterpolate,-350,150)
            dark=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-700,260)
            dark.set_editor_property('constant',u.LinearColor(*(v*.68 for v in color),1))
            M.connect_material_expressions(c,'',lerp,'A');M.connect_material_expressions(dark,'',lerp,'B')
            M.connect_material_expressions(wear,'',lerp,'Alpha');M.connect_material_property(lerp,'',u.MaterialProperty.MP_BASE_COLOR)
            for value,prop,yy in [(metallic,u.MaterialProperty.MP_METALLIC,360),(rough,u.MaterialProperty.MP_ROUGHNESS,440)]:
                n=M.create_material_expression(mat,u.MaterialExpressionConstant,-350,yy);n.set_editor_property('r',value);M.connect_material_property(n,'',prop)
            grain=M.create_material_expression(mat,u.MaterialExpressionCustom,-350,550)
            inp=u.CustomInput();inp.set_editor_property('input_name','UV');grain.set_editor_property('inputs',[inp])
            grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
            grain.set_editor_property('code','float f=1-smoothstep(.04,.24,length(fwidth(UV))*900);float2 g=sin(UV*3100+sin(UV.yx*800));return normalize(float3(g*.018*f,1));')
            M.connect_material_expressions(uv,'',grain,'UV');M.connect_material_property(grain,'',u.MaterialProperty.MP_NORMAL)
            errors=list(M.recompile_material(mat))
            if errors:raise RuntimeError('Warehouse coating compile failed '+key+' '+str(errors))
            if not E.save_loaded_asset(mat,False):raise RuntimeError('Warehouse coating save failed '+key)
        report['materials'].append(path)
    report['label_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
