"""Dense polished magic crystal: explicit coverage, visible body, restrained edges."""
from pathlib import Path
import json
import shutil
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
D='/Game/Weapons/FrostCrystalSword20260915/HighEnergyGlass20261102/'
TARGETS=[D+'M_FrostCrystalSword_HighEnergyGlass',D+'M_FrostCrystalSword_HighEnergyGlass_Preview']
REV='HighEnergyDenseCrystalV4_20261103'

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE active: stop play before compiling and saving dense crystal materials')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in TARGETS:
        raise RuntimeError('Preserve unsaved material '+package.get_path_name())

saved=[]
for path in TARGETS:
    mat=E.load_asset(path)
    if not mat: raise RuntimeError('Missing high-energy crystal material '+path)
    if E.get_metadata_tag(mat,'HighEnergyGlassRevision')==REV:
        saved.append({'asset':path,'saved':True,'already_current':True})
        continue
    disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/disk.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists(): shutil.copy2(disk,backup)
    expressions=list(L.get_material_expressions(mat))

    def node(cls,**props):
        n=L.create_material_expression(mat,cls)
        for key,value in props.items(): n.set_editor_property(key,value)
        return n
    def wire(src,dst,pin,out=''):
        names=[str(x) for x in L.get_material_expression_input_names(dst)]
        norm=lambda x:x.replace(' ','').replace('_','').lower()
        actual=next((x for x in names if norm(x)==norm(pin)),None)
        if actual is None and pin=='Input' and len(names)==1: actual=names[0]
        if actual is None or not L.connect_material_expressions(src,out,dst,actual):
            raise RuntimeError('Cannot connect '+pin+' '+str(names))
    def output(src,field,out=''):
        if not L.connect_material_property(src,out,getattr(u.MaterialProperty,'MP_'+field)):
            raise RuntimeError('Cannot connect '+field)
    def root(field):
        prop=getattr(u.MaterialProperty,'MP_'+field)
        n=L.get_material_property_input_node(mat,prop)
        return n,str(L.get_material_property_input_node_output_name(mat,prop)) if n else ''
    def find(label):
        matches=[n for n in expressions if isinstance(n,u.MaterialExpressionCustom)
                 and str(n.get_editor_property('desc'))=='HighEnergyGlassV2 '+label]
        if len(matches)!=1: raise RuntimeError('Missing source graph '+label+' '+path)
        return matches[0]
    def source(expression,name):
        for pin,src in zip(L.get_material_expression_input_names(expression),L.get_inputs_for_material_expression(mat,expression)):
            if str(pin)==name and src:
                return src,str(L.get_input_node_output_name_for_material_expression(expression,src))
        raise RuntimeError('Missing source input '+name)
    def scalar(v): return node(u.MaterialExpressionConstant,r=float(v))
    def parameter(name,v): return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=float(v))
    def color(v): return node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
    def custom(label,code,width,**inputs):
        n=node(u.MaterialExpressionCustom,desc=REV+' '+label,code=code,
               output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        n.set_editor_property('inputs',pins)
        for name,value in inputs.items():
            src,out=value if isinstance(value,tuple) else (value,'')
            wire(src,n,name,out)
        return n

    preview=path.endswith('_Preview')
    mask=find('original crystal versus opaque bronze seat')
    raw=source(mask,'Base')
    thickness=find('bounded ridge optical thickness cm')
    original_normal=source(find('polished large facets'),'N')
    original_rough=source(find('clean glass roughness'),'R')
    original_base=source(find('preview crystal tint'),'Base') if preview else root('BASE_COLOR')
    original_metal=source(find('dielectric crystal'),'Base') if preview else root('METALLIC')
    original_emission=root('EMISSIVE_COLOR')
    if not original_emission[0]: original_emission=(color((0,0,0)),'')
    if not original_metal[0]: original_metal=(scalar(0),'')
    if not original_base[0]: raise RuntimeError('Missing crystal base colour')

    # Explicit inverse coverage replaces colored-volume transmission. Both the
    # world material and UI capture now retain a readable crystal body.
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    mat.set_editor_property('translucency_pass',u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    mat.set_editor_property('refraction_method',u.RefractionMode.RM_NONE)
    mat.set_editor_property('two_sided',False)
    mat.set_editor_property('screen_space_reflections',not preview)
    mat.set_editor_property('forward_blends_sky_light_cubemaps',True)
    mat.set_editor_property('allow_front_layer_translucency',True)

    facing=node(u.MaterialExpressionFresnel,exponent=4.,base_reflect_fraction=0.)
    core=custom('solid centre and thin edge','return smoothstep(.85,1.85,Thickness);',1,Thickness=thickness)
    tint=custom('deep cyan crystal body',
        'float v=saturate(dot(Raw,float3(.2126,.7152,.0722)));'
        'float grain=smoothstep(.18,.8,v);'
        'float3 body=lerp(float3(.025,.145,.225),float3(.075,.34,.44),saturate(v*1.35+.12));'
        'body=lerp(body,float3(.22,.58,.66),pow(grain,1.8)*.22);'
        'return lerp(body,float3(.18,.48,.57),saturate((1-Core)*.15+Facing*.16));',
        3,Raw=raw,Core=core,Facing=facing)
    coverage=custom('dense crystal coverage',
        'float a=lerp(EdgeCoverage,BodyCoverage,Core)+Facing*.02;'
        'return lerp(1,clamp(a,.86,.99),Mask);',1,
        EdgeCoverage=parameter('CrystalEdgeCoverageV4',.88),BodyCoverage=parameter('CrystalBodyCoverageV4',.97),
        Core=core,Facing=facing,Mask=mask)
    polished=custom('polished readable facets',
        'float strength=lerp(1,Strength,Mask);return normalize(float3(N.xy*strength,lerp(1,N.z,strength)));',3,
        N=original_normal,Strength=parameter('CrystalFacetStrengthV4',.48),Mask=mask)
    rough=custom('broad polished highlights',
        'float v=saturate(dot(Raw,float3(.2126,.7152,.0722)));'
        'float crystal=clamp(Polish+(.5-v)*.045-Facing*.015,.085,.16);return lerp(Base,crystal,Mask);',1,
        Base=original_rough,Raw=raw,Polish=parameter('CrystalPolishV4',.12),Facing=facing,Mask=mask)
    emission=custom('restrained internal crystal light',
        'return Base+Tint*Glow*Mask*(.45+.55*Core)*(1-.4*Facing);',3,
        Base=original_emission,Tint=tint,Glow=parameter('CrystalInnerGlowV4',.12),Mask=mask,Core=core,Facing=facing)
    fields={
        'BASE_COLOR':custom('preserve bronze seat colour','return lerp(Base,Tint,Mask);',3,Base=original_base,Tint=tint,Mask=mask),
        'METALLIC':custom('nonmetal crystal and original seat','return lerp(Base,0,Mask);',1,Base=original_metal,Mask=mask),
        'SPECULAR':custom('strong dielectric polish','return lerp(.5,Specular,Mask);',1,Specular=parameter('CrystalSpecularV4',.9),Mask=mask),
        'ROUGHNESS':rough,'NORMAL':polished,'OPACITY':coverage,'EMISSIVE_COLOR':emission,
    }
    front=node(u.MaterialExpressionSubstrateShadingModels,desc=REV+' surface',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for field,pin in [('BASE_COLOR','BaseColor'),('METALLIC','Metallic'),('SPECULAR','Specular'),('ROUGHNESS','Roughness'),
                      ('NORMAL','Normal'),('OPACITY','Opacity'),('EMISSIVE_COLOR','EmissiveColor')]:
        output(fields[field],field);wire(fields[field],front,pin)
    output(front,'FRONT_MATERIAL')
    # Retain the existing temporal responsiveness and native rune/seat graphs.
    errors=L.recompile_material(mat)
    if errors: raise RuntimeError('Dense crystal shader compilation failed '+str(errors))
    L.get_statistics(mat)
    E.set_metadata_tag(mat,'HighEnergyGlassRevision',REV)
    if not E.save_loaded_asset(mat,False): raise RuntimeError('Cannot save '+path)
    saved.append({'asset':path,'saved':True,'compile_errors':list(errors)})
    print('DENSE_CRYSTAL_SAVED',path)

(P/'material-receipt.json').write_text(json.dumps({
    'revision':REV,'materials':saved,'body_coverage':.97,'thin_edge_coverage':.88,
    'normal_strength':.48,'roughness_base':.12,'inner_glow':.12,
    'appearance':'dense deep cyan polished crystal with visible core and restrained translucent edges',
    'runes_and_bronze_seat_preserved':True,'gameplay_stats_changed':False,
    'gameplay_tested':False,'visual_tested':False,
},indent=2)+'\n',encoding='utf8')
print('HIGH_ENERGY_DENSE_CRYSTAL_V4_COMPLETE')
