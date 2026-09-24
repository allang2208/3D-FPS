"""Author four dedicated liquid materials. No preview/game/test; no existing assets rebuilt."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir())
OUT=ROOT/'SourceAssets/VenomProjectiles20260924'
DEST='/Game/Fluids/VenomProjectiles20260924'
sys.path.insert(0,str(ROOT/'Tools/Fluids'))
from author_river_pilot import node,wire,prop,scalar,vector,custom
from author_impact_smoke_corrosion import surface,constant
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;SAVED=[]
TAG='VenomProjectiles20260924'

def source(name):return (OUT/(name+'.hlsl')).read_text(encoding='utf8')
def material(name,decal=False,shell=False):
    path=DEST+'/'+name
    m=u.load_asset(path) if E.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    # Keep rooted old expressions on reruns; owned Custom nodes update in place.
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if shell or decal else u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL if decal else u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided',False)
    if shell:
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        m.set_editor_property('allow_front_layer_translucency',False)
        m.set_editor_property('output_translucent_velocity',False)
        m.set_editor_property('disable_depth_test',False)
        m.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
    return m
def save(m):
    errors=L.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(m,False):raise RuntimeError('Save '+m.get_path_name())
    SAVED.append(m.get_path_name());print('VENOM_PROJECTILE_SAVED',m.get_path_name())
def seed(m):
    n=scalar(m,'LiquidSeed',.5)
    n.set_editor_property('use_custom_primitive_data',True)
    n.set_editor_property('primitive_data_index',0)
    return n
def refresh(m,codes):
    owned=[n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
           and n.get_editor_property('description').startswith(TAG+' ') ]
    if not owned:return False
    for n in owned:
        name=n.get_editor_property('description').removeprefix(TAG+' ')
        if name in codes:n.set_editor_property('code',codes[name])
    save(m);return True
def world_position(m,p):
    n=node(m,u.MaterialExpressionTransformPosition)
    n.set_editor_property('transform_source_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    n.set_editor_property('transform_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    wire(p,n,str(L.get_material_expression_input_names(n)[0]));return n
def liquid(name,shell=False,bottle=False):
    m=material(name,shell=shell)
    if refresh(m,{'LiquidFlow':source('LiquidFlow'),'LiquidShape':source('LiquidShape')}):return
    p=node(m,u.MaterialExpressionLocalPosition)
    p.set_editor_property('included_offsets',u.PositionIncludedOffsets.EXCLUDE_OFFSETS)
    clock=node(m,u.MaterialExpressionTime);s=seed(m)
    coords=custom(m,'return P*'+('.10;' if bottle else '.02;'),{'P':p},3)
    field=custom(m,source('LiquidFlow'),{'P':coords,'Clock':clock,'Seed':s},4,TAG+' LiquidFlow')
    tint=custom(m,'return lerp(float3(.023,.060,.005),float3(.115,.225,.026),F.z)+float3(.012,.016,.003)*F.w;',{'F':field},3)
    rough=custom(m,'return .09+.12*F.z+F.w*.05;',{'F':field})
    normal=custom(m,'return normalize(float3(F.xy,1));',{'F':field},3)
    inputs={'BASE_COLOR':tint,'ROUGHNESS':rough,'SPECULAR':constant(m,.60),'NORMAL':normal}
    if shell:
        f=node(m,u.MaterialExpressionFresnel);f.set_editor_property('exponent',2.2);f.set_editor_property('base_reflect_fraction',.04)
        inputs['OPACITY']=custom(m,'return lerp(.92,.48,F)*(.89+.11*D.z);',{'F':f,'D':field})
    surface(m,inputs)
    if bottle:
        shape=custom(m,'float3 q=P;q.z+=smoothstep(7,11,P.z)*.08*sin(P.x*1.1+P.y*.7+Clock*3+Seed*6.28);return q;',{'P':p,'Clock':clock,'Seed':s},3)
    else:
        shape=custom(m,source('LiquidShape'),{'P':p,'Clock':clock,'Seed':s},3,TAG+' LiquidShape')
    displacement=custom(m,'return NewPosition-OldPosition;',{'NewPosition':world_position(m,shape),'OldPosition':world_position(m,p)},3)
    prop(m,displacement,'WORLD_POSITION_OFFSET');save(m)
def pool():
    m=material('M_WitchPoisonPool',decal=True)
    owned=next((n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
                and n.get_editor_property('description')==TAG+' WitchPool'),None)
    reach={f'Reach{i}':(vector(m,f'PoolReach{i}',(1,1,1,1)),'RGBA') for i in range(4)} if not owned else {}
    if owned:
        inputs=list(owned.get_editor_property('inputs'))
        names={str(v.get_editor_property('input_name')) for v in inputs}
        for i in range(4):
            name=f'Reach{i}'
            if name not in names:
                value=u.CustomInput();value.set_editor_property('input_name',name);inputs.append(value)
                reach[name]=(vector(m,f'PoolReach{i}',(1,1,1,1)),'RGBA')
        owned.set_editor_property('inputs',inputs)
        for name,value in reach.items():wire(value,owned,name)
        owned.set_editor_property('code',source('WitchPool'));save(m);return
    p=node(m,u.MaterialExpressionWorldPosition)
    field=custom(m,source('WitchPool'),{'Position':p,'Clock':node(m,u.MaterialExpressionTime),
        'StartTime':scalar(m,'PoolStartTime',0),'Seed':scalar(m,'PoolSeed',.5),'Radius':scalar(m,'PoolRadius',200),
        'Center':(vector(m,'PoolCenter',(0,0,0,0)),'RGB'),'SurfaceNormal':(vector(m,'PoolNormal',(0,0,1,0)),'RGB'),**reach},4,TAG+' WitchPool')
    color=custom(m,'float3 c=lerp(float3(.021,.052,.005),float3(.092,.17,.025),F.y);c=lerp(c,float3(.22,.26,.06),F.z*.4);return lerp(c,c*.64,F.w);',{'F':field},3)
    opacity=custom(m,'return F.x;',{'F':field})
    rough=custom(m,'return lerp(.105+F.y*.11+F.z*.13,.56,F.w);',{'F':field})
    surface(m,{'BASE_COLOR':color,'OPACITY':opacity,'ROUGHNESS':rough,'SPECULAR':constant(m,.58)},decal=True)
    save(m)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active game; author after play stops')
    paths={DEST+'/'+n for n in ['M_VenomBody','M_VenomCore','M_WitchBottleLiquid','M_WitchPoisonPool']}
    if paths.intersection(str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved target liquid materials')
    E.make_directory(DEST)
    liquid('M_VenomBody',shell=True);liquid('M_VenomCore');liquid('M_WitchBottleLiquid',bottle=True);pool()
    u.PoisonMaggotMonster.compile_material_assets([u.load_asset(p) for p in SAVED])
    for path in SAVED:E.save_loaded_asset(u.load_asset(path),False)
    (OUT/'assets-saved.json').write_text(json.dumps({'saved':SAVED,'new_textures':0,'new_meshes':0,
        'runtime_solver':False,'game_tested':False,'visual_tested':False},indent=2),encoding='utf8')
    print('VENOM_PROJECTILE_MATERIALS_COMPLETE',len(SAVED))
if __name__=='__main__':main()
