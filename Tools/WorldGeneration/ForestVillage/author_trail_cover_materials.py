"""Author the terrain variants for the village level and its forest sublevel."""
import os,json
from pathlib import Path
import unreal as u
ed,lib=u.MaterialEditingLibrary,u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])
batch=Path(os.environ['FPS_FOREST_REFERENCE_BATCH'])
ref='/Game/ForestPathStudy/VillageRegion/Reference'
dest=ref+'/TrailCover'
far='/Game/ForestPathStudy/VillageRegion/FarGrass'
edprop=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES
def save(o):
    if not lib.save_loaded_asset(o,False):raise RuntimeError(o.get_path_name())
def asset(path):return u.load_asset(path)
def dup(a,p):
    return asset(p) if lib.does_asset_exist(p) else lib.duplicate_asset(a.get_path_name(),p)
def import_asset(file,folder,name):
    task=u.AssetImportTask();task.filename=str(src/file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;tools.import_asset_tasks([task])
    for path in task.imported_object_paths:
        o=asset(str(path))
        if isinstance(o,(u.Texture2D,u.StaticMesh)):return o
    raise RuntimeError(file)
def tex(name,where,comp,srgb):
    texture=import_asset(name+'.png',where,name)
    texture.set_editor_property('srgb',srgb)
    texture.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,'TC_'+comp))
    return texture
def node(owner,cls):
    return (ed.create_material_expression if isinstance(owner,u.Material) else ed.create_material_expression_in_function)(owner,cls)
def wire(a,p,b,k):
    if not ed.connect_material_expressions(a,p,b,k):raise RuntimeError(str((a.get_name(),p,b.get_name(),k)))
def inputs(m,n):
    return dict(zip(map(str,ed.get_material_expression_input_names(n)),ed.get_inputs_for_material_expression(m,n)))
def custom(owner,code,pins,tag,outputs=()):
    n=node(owner,u.MaterialExpressionCustom);n.set_editor_property('desc',tag)
    args=[]
    for key in pins:
        a=u.CustomInput();a.set_editor_property('input_name',key);args.append(a)
    n.set_editor_property('inputs',args);n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    args=[]
    for key,width in outputs:
        a=u.CustomOutput();a.set_editor_property('output_name',key);a.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)));args.append(a)
    n.set_editor_property('additional_outputs',args);n.set_editor_property('code',code)
    for k,(a,p) in pins.items():wire(a,p,n,k)
    return n
def object_node(owner,texture,kind):
    n=node(owner,u.MaterialExpressionTextureObject);n.set_editor_property('texture',texture)
    n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
    return n
def compile_mat(m):
    errors=ed.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    save(m)

def author():
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import author_continuous_meadow as meadow
    lib.make_directory(dest)
    soil=tex('T_TrailSoil',dest,'DEFAULT',True);save(soil)
    moss=tex('T_TrailMossIslands',dest,'DEFAULT',True);save(moss)
    packed=tex('T_TrailSoilData',dest,'MASKS',False);save(packed)
    textures=meadow.prepare_textures()
    field=textures[0]
    fn=asset(ref+'/MF_TrailDirt')
    nodes=ed.get_material_function_expressions(fn)
    if not any(n.get_editor_property('desc')=='R21 independent soil and moss' for n in nodes):
        make=next(n for n in nodes if isinstance(n,u.MaterialExpressionMakeMaterialAttributes))
        height=next(n for n in nodes if isinstance(n,u.MaterialExpressionFunctionOutput) and str(n.get_editor_property('output_name'))=='Height')
        p=node(fn,u.MaterialExpressionWorldPosition)
        pins={'P':(p,''),'Eye':(node(fn,u.MaterialExpressionCameraPositionWS),'')}
        normal=asset('/Game/ForestPathStudy/Materials/T_NordicForestGroundRootsCoarse_Normal')
        for name,texture,kind in [('Soil',soil,'COLOR'),('Moss',moss,'COLOR'),('Nrm',normal,'NORMAL'),('Packed',packed,'MASKS')]:
            pins[name]=(object_node(fn,texture,kind),'')
        n=custom(fn,Path(__file__).with_name('trail_soil.ush').read_text(encoding='utf-8-sig'),pins,'R21 independent soil and moss',
                 [('RoadNormal',3),('RoadRoughness',1),('RoadAO',1),('RoadHeight',1)])
        for pin,key in [('BaseColor',''),('Normal','RoadNormal'),('AmbientOcclusion','RoadAO'),('Roughness','RoadRoughness')]:wire(n,key,make,pin)
        zero=node(fn,u.MaterialExpressionConstant);wire(zero,'',make,'Metallic');wire(zero,'',make,'Displacement')
        spec=node(fn,u.MaterialExpressionConstant);spec.set_editor_property('r',.32);wire(spec,'',make,'Specular')
        wire(n,'RoadHeight',height,'')
        ed.update_material_function(fn);save(fn)
    # Same semantic ground-cover atlas and projection on both kinds of terrain.
    land_mi=asset('/Game/ForestPathStudy/Materials/MI_ForestPathForest')
    lm=dup(land_mi.get_base_material(),dest+'/M_ForestVillageLandscape')
    mesh=asset(ref+'/M_ForestReferenceMesh')
    for m in [lm,mesh]:
        nodes=ed.get_material_expressions(m)
        old=next((n for n in nodes if str(n.get_editor_property('desc')) in ('R18 distant grass drifts and road wear','R21 continuous meadow','R24 hillside meadow','R26 continuous ground cover')),None)
        if old:
            shade=old
        else:
            root=ed.get_material_property_input_node(m,edprop);color=inputs(m,root)['BaseColor']
            outpin=str(ed.get_input_node_output_name_for_material_expression(root,color) or '')
            pos=node(m,u.MaterialExpressionWorldPosition)
            uv=node(m,u.MaterialExpressionCustom);arg=u.CustomInput();arg.set_editor_property('input_name','P')
            uv.set_editor_property('inputs',[arg]);uv.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT2)
            uv.set_editor_property('code','return (P.xy+float2(62400.,32000.))/102400.;');wire(pos,'',uv,'P')
            atlas=node(m,u.MaterialExpressionTextureSample);atlas.set_editor_property('texture',field)
            atlas.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(uv,'',atlas,'UVs')
            shade=custom(m,'return C;',{'P':(pos,''),'Eye':(node(m,u.MaterialExpressionCameraPositionWS),''),'F':(atlas,'RGB'),'C':(color,outpin)},'R21 continuous meadow')
            wire(shade,'',root,'BaseColor')
        meadow.apply_surface(m,shade,*textures)
        calls=[n for n in nodes if isinstance(n,u.MaterialExpressionMaterialFunctionCall) and
               isinstance(sc:=inputs(m,n).get('Size'),u.MaterialExpressionScalarParameter) and str(sc.get_editor_property('parameter_name'))=='Size C']
        if len(calls)!=1:raise RuntimeError('No unique painted road in '+m.get_name())
        if calls[0].get_editor_property('material_function')!=fn and not calls[0].set_material_function(fn):raise RuntimeError('Cannot bind C')
        compile_mat(m)
    village=dup(land_mi,dest+'/MI_ForestVillageLandscape');ed.set_material_instance_parent(village,lm);ed.update_material_instance(village);save(village)
    from author_trail_cover_level import fine_mesh,fine_material
    report=dict(landscape=village.get_path_name(),mesh=fine_mesh,material=fine_material)
    (batch/'materials.json').write_text(json.dumps(report,indent=2))
if __name__=="__main__":author()

