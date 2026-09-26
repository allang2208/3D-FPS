"""Import actual cut tree sections and author their matching hinge profiles/materials."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent/'FellingCut';SRC=ROOT/'Delivery';DEST='/Game/Items/HarvestTimber'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
def create(name,cls,factory):return u.load_asset(DEST+'/'+name) or A.create_asset(name,DEST,cls,factory)
def node(mat,cls,**props):
    n=L.create_material_expression(mat,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,out,b,pin):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(n,pin,prop):
    if not L.connect_material_property(n,pin,prop):raise RuntimeError('Cannot connect material output')
reference=u.load_asset(DEST+'/T_PoplarEndReference')
for name,fade in [('M_TreeCutSurface',False),('M_FallingCutEnd',True)]:
    material=create(name,u.Material,u.MaterialFactoryNew())
    for n in list(L.get_material_expressions(material)):L.delete_material_expression(material,n)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('used_with_skeletal_mesh',fade)
    # 使用标志必须和实际渲染路径一致，否则游戏里会被替换成默认材质：
    # 上半段是 Nanite 骨骼网格（断面材质挂在槽 2），树桩切面画在静态实例上。
    material.set_editor_property('used_with_nanite',fade)
    material.set_editor_property('used_with_instanced_static_meshes',not fade)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED if fade else u.BlendMode.BLEND_OPAQUE)
    uv=node(material,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    scale=node(material,u.MaterialExpressionConstant2Vector,r=.28,g=.56)
    multiply=node(material,u.MaterialExpressionMultiply);link(uv,'',multiply,'A');link(scale,'',multiply,'B')
    offset=node(material,u.MaterialExpressionConstant2Vector,r=.65,g=.27)
    add=node(material,u.MaterialExpressionAdd);link(multiply,'',add,'A');link(offset,'',add,'B')
    tex=node(material,u.MaterialExpressionTextureSample,texture=reference)
    link(add,'',tex,str(L.get_material_expression_input_names(tex)[0]));output(tex,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    rough=node(material,u.MaterialExpressionConstant,r=.83);output(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    if fade:
        amount=node(material,u.MaterialExpressionScalarParameter,parameter_name='HarvestFade',default_value=1)
        pins=[]
        for name_in in ('UV','Fade'):
            p=u.CustomInput();p.set_editor_property('input_name',name_in);pins.append(p)
        mask=node(material,u.MaterialExpressionCustom,code='return step(frac(sin(dot(UV,float2(127.1,311.7)))*43758.5453),Fade);',
            output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,inputs=pins)
        link(uv,'',mask,'UV');link(amount,'',mask,'Fade');output(mask,'',u.MaterialProperty.MP_OPACITY_MASK)
    L.recompile_material(material);save(material)
master=u.load_asset(DEST+'/M_CutUpperMotion') or E.duplicate_asset(DEST+'/M_FallingPoplar',DEST+'/M_CutUpperMotion')
for n in L.get_material_expressions(master):
    if isinstance(n,u.MaterialExpressionCustom):
        code=n.get_editor_property('code')
        if 'step(H,P.z)*' in code:n.set_editor_property('code',code.replace('step(H,P.z)*',''))
master.set_editor_property('used_with_instanced_static_meshes',True)
L.recompile_material(master);save(master)
for kind in ('Bark','Foliage'):
    mi=u.load_asset(DEST+'/MI_CutUpper_'+kind) or E.duplicate_asset(DEST+'/MI_FallingPoplar_'+kind,DEST+'/MI_CutUpper_'+kind)
    L.set_material_instance_parent(mi,master);save(mi)
end=u.load_asset(DEST+'/M_TreeCutSurface');fallend=u.load_asset(DEST+'/M_FallingCutEnd')
report={};author=json.loads((SRC/'authoring.json').read_text())
for name,info in author.items():
    upper=info['upper'];kind=name[-1]
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.generate_lightmap_u_vs=False
    task=u.AssetImportTask();task.filename=str(SRC/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.options=opt;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not mesh:raise RuntimeError('Cannot import '+name)
    slots=mesh.static_materials
    for i,slot in enumerate(slots):
        label=str(slot.material_slot_name)
        if 'CutEndGrain' in label:mat=fallend if upper else end
        else:
            part='Foliage' if 'Foliage' in label else 'Bark'
            mat=u.load_asset(DEST+'/MI_CutUpper_'+part) if upper else u.load_asset('/Game/WorldGeneration/TemperateHills/MI_BlackPoplarPCG_'+part)
        slot.material_interface=mat;slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    if upper:
        nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True
        nanite.shape_preservation=u.NaniteShapePreservation.PRESERVE_AREA
        nanite.fallback_percent_triangles=.01;mesh.set_editor_property('nanite_settings',nanite)
    save(mesh)
    entry={'path':mesh.get_path_name(),'upper':upper,'materials':[s.material_interface.get_path_name() for s in slots]}
    if not upper:
        # Read in UE centimetres after import, avoiding FBX axis/unit assumptions.
        read=u.GeometryScriptMeshReadLOD();read.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        dynamic,result=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
        if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot author rim profile '+name)
        _,positions,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dynamic,True)
        vectors=u.GeometryScript_List.convert_vector_list_to_array(positions)
        unique={(round(p.x,4),round(p.y,4)) for p in vectors if abs(p.z-42)<.01}
        if len(unique)<3:raise RuntimeError('Missing cut rim '+name)
        profile_class=u.load_class(None,'/Script/FPSGAME.ProductionTreeCutProfile')
        if not profile_class:raise RuntimeError('Native tree-cut profile class is not loaded')
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',profile_class)
        profile=create('DA_TreeCut_'+kind,u.DataAsset,factory)
        profile.set_editor_property('rim',[u.Vector2D(x,y) for x,y in sorted(unique)]);save(profile)
        entry['rim_points']=len(unique)
    report[name]=entry
(ROOT/'import.json').write_text(json.dumps(report,indent=2))
u.log('MATCHED_TREE_SECTIONS_IMPORTED count='+str(len(report)))
import runpy
runpy.run_path(str(Path(__file__).parent/'build_falling_assemblies.py'))
