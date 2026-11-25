"""Author R30 appearance assets from the existing warhorse materials and skeleton."""
import json
import os
import sys
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
from import_horses import DEST,fbx_options,import_file,save

SOURCE=HERE.parents[3]/'SourceAssets/HillsVillageStable/AppearanceR30'
FOLDER=DEST+'/AppearanceR30'
LIB=u.EditorAssetLibrary
MAT=u.MaterialEditingLibrary
PROP=u.MaterialProperty


def build_material(name,hair=False,fade=False):
    path=FOLDER+'/'+name
    mat=LIB.load_asset(path) if LIB.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,FOLDER,u.Material,u.MaterialFactoryNew())
    MAT.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED if hair or fade else u.BlendMode.BLEND_OPAQUE)
    if hair:mat.set_editor_property('opacity_mask_clip_value',.27)
    MAT.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)

    def node(kind):return MAT.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
    def wire(a,b,pin,out=''):
        if not MAT.connect_material_expressions(a,out,b,pin):raise RuntimeError((name,pin,out))
    def output(a,prop,out=''):
        if not MAT.connect_material_property(a,out,prop):raise RuntimeError((name,str(prop)))
    def parameter(key,rgba,index=None):
        n=node('VectorParameter');n.set_editor_property('parameter_name',key);n.set_editor_property('default_value',u.LinearColor(*rgba))
        if index is not None:
            n.set_editor_property('use_custom_primitive_data',True);n.set_editor_property('primitive_data_index',index)
        return n
    def texture(path,kind='SAMPLERTYPE_COLOR'):
        t=node('TextureSample');t.texture=LIB.load_asset(path)
        if not t.texture:raise RuntimeError(path)
        t.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,kind))
        return t
    def custom(title,body,typ,inputs):
        n=node('Custom');n.set_editor_property('description',title);n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+typ))
        pins=[]
        for key,_,_ in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
        n.set_editor_property('inputs',pins);n.set_editor_property('code',body)
        for key,src,channel in inputs:wire(src,n,key,channel)
        return n
    def mask(source,channels):
        n=node('ComponentMask')
        for c in 'rgba':n.set_editor_property(c,c in channels)
        wire(source,n,'');return n
    def constant(v):
        n=node('Constant');n.r=v;return n
    hair_colour=parameter('HairPigment',(.043,.034,.026,1),16)
    settings=parameter('HairCoverage',(.88,.85,.035,1),20)
    alpha=None
    if hair:
        t=texture(DEST+'/ManeR17/T_Warhorse_Mane')
        uv=node('TextureCoordinate')
        phase=node('TextureCoordinate');phase.coordinate_index=1
        # Remap the tapered texture along the lock. Clamp inside the last texel to
        # prevent wrapped roots reappearing at shortened tips. Leave the pelt and tail untouched.
        fibre_uv=custom('Individual mane length',
                        'float y=abs(Phase.y-.5)>.31?min(UV.y/max(.80,Length),.9996):UV.y; return float2(UV.x,y);','2',
                        [('UV',uv,''),('Phase',phase,''),('Length',settings,'A')])
        wire(fibre_uv,t,'')
        colour=custom('Pigment within each fibre',
                      'return Tint * clamp(pow(max(dot(Strand,float3(.25,.60,.15)),.0004)/.04,.66),.14,2.4);','3',
                      [('Tint',hair_colour,'RGB'),('Strand',t,'RGB')])
        output(colour,PROP.MP_BASE_COLOR)
        alpha=custom('Keep whole locks and retain the continuous root pelt',
                     'float group=abs(Phase.y-.5); float keep=group<.08?1.0:step(Phase.x,group<.31?Coverage.y:Coverage.x); return A*keep;','1',
                     [('A',t,'A'),('Phase',phase,''),('Coverage',settings,'RGB')])
        output(constant(.76),PROP.MP_ROUGHNESS);output(constant(.19),PROP.MP_SPECULAR)
        bend=parameter('ManeDisplacement',(0,0,0,0));side=parameter('ManeSideAxis',(1,0,0,0));clock=node('Time')
        wpo=custom('Root-pinned wind along the neck',"""
float group=abs(Phase.y-.5);
float tip=smoothstep(.04,1.,UV.y);
if(group<.31)return 0.; // The undercoat is fixed; tail wisps move with the articulated tail.
float gust=sin(Clock*13.+Phase.x*6.283)+.32*sin(Clock*21.3+Phase.x*11.1);
float3 outward=Side*(Phase.y>.5?1:-1);
float3 drift=Bend-min(0,dot(Bend,outward))*outward;
return tip*tip*(drift*(1.+.14*gust)+float3(0,0,.11*min(length(drift),5.)*gust));""",'3',
                   [('Phase',phase,''),('UV',uv,''),('Bend',bend,'RGB'),('Side',side,'RGB'),('Clock',clock,'')])
        output(wpo,PROP.MP_WORLD_POSITION_OFFSET)
    else:
        t=texture(DEST+'/Surfaces/T_Warhorse_BaseColor')
        packed=texture(DEST+'/Surfaces/T_Warhorse_MetalRough','SAMPLERTYPE_MASKS')
        normal=texture(DEST+'/Surfaces/T_Warhorse_Normal','SAMPLERTYPE_NORMAL')
        output(normal,PROP.MP_NORMAL,'RGB');output(packed,PROP.MP_ROUGHNESS,'G');output(packed,PROP.MP_METALLIC,'B')
        region=texture(FOLDER+'/T_Warhorse_Regions','SAMPLERTYPE_LINEAR_COLOR')
        # Decode reference-space centimetres from the UV atlas of the original scan.
        pattern=parameter('PatternProjection',(.13,.59,.006,.53),12)
        coords=custom('Oblique coat projections',"""
float3 p=Rest*float3(100.,220.,260.)*Frequency;
return float4(p.x+.44*p.y-.73*p.z, p.y+.51*p.z+.32*p.x,
              p.z-.54*p.y+.36*p.x,p.x+.69*p.y+.22*p.z)*.55+float4(Shift,Shift.yx+.37);""",'4',
                      [('Rest',region,'RGB'),('Frequency',pattern,'B'),('Shift',mask(pattern,'rg'),'')])
        noise=[]
        for pair in ('rg','ba'):
            sample=texture(FOLDER+'/T_Warhorse_Pigment','SAMPLERTYPE_MASKS')
            wire(mask(coords,pair),sample,'');noise.append(sample)
        base=parameter('CoatPigment',(.14,.065,.028,1),4);other=parameter('PatchPigment',(.57,.53,.46,1),8)
        colour=custom('Paint only coat and tail fibres',"""
float field=.61*NoiseA+.39*NoiseB;
float pigmentCoverage=smoothstep(Threshold-Softness,Threshold+Softness,field);
float luma=max(.0004,dot(Original,float3(.25,.60,.15)));
float3 coat=lerp(Base,Patch,pigmentCoverage)*clamp(pow(luma/.042,.55),.26,1.7);
float3 tail=Hair*clamp(pow(luma/.035,.65),.13,2.4);
return lerp(lerp(Original,coat,saturate((Area-.51)/.49)),tail,saturate((.49-Area)/.49));""",'3',
                      [('NoiseA',noise[0],'R'),('NoiseB',noise[1],'G'),('Threshold',pattern,'A'),('Softness',settings,'B'),
                       ('Original',t,'RGB'),('Area',region,'A'),('Base',base,'RGB'),('Patch',other,'RGB'),('Hair',hair_colour,'RGB')])
        output(colour,PROP.MP_BASE_COLOR)
    if fade or hair:
        f=node('ScalarParameter');f.set_editor_property('parameter_name','HorseRetreatFade');f.set_editor_property('use_custom_primitive_data',True);f.set_editor_property('primitive_data_index',0)
        inv=node('OneMinus');wire(f,inv,'')
        d=node('MaterialFunctionCall')
        if not d.set_material_function(u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA')):raise RuntimeError('DitherTemporalAA')
        wire(inv,d,MAT.get_material_expression_input_names(d)[0])
        if alpha:
            m=node('Multiply');wire(alpha,m,'A');wire(d,m,'B');d=m
        output(d,PROP.MP_OPACITY_MASK)
    MAT.layout_material_expressions(mat)
    errors=MAT.recompile_material(mat)
    if errors:raise RuntimeError(name+' shader compilation: '+str(errors))
    save(mat)
    return mat


def author():
    LIB.make_directory(FOLDER)
    assets=[]
    for stem in ['T_Warhorse_Regions','T_Warhorse_Pigment']:
        t=import_file(SOURCE/(stem+'.png'),stem,FOLDER)
        t.set_editor_property('srgb',False)
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if stem.endswith('Regions') else u.TextureCompressionSettings.TC_MASKS)
        save(t);assets.append(t.get_path_name())
    for name in ['M_Warhorse_Coat','M_Warhorse_CoatFade','M_Warhorse_Fibres']:
        mat=build_material(name,hair=name.endswith('Fibres'),fade=name.endswith('Fade'))
        assets.append(mat.get_path_name())
    body=LIB.load_asset(DEST+'/SK_StableWarhorse');hair=LIB.load_asset(FOLDER+'/M_Warhorse_Fibres')
    for style in ['Crop','Sweep','Parted']:
        name='SK_Hair_'+style
        options=fbx_options();options.skeleton=body.skeleton;options.create_physics_asset=False
        skin=import_file(SOURCE/(name+'.fbx'),name,FOLDER,options)
        slots=list(skin.materials);slots[0].material_interface=hair;skin.materials=slots
        save(skin);assets.append(skin.get_path_name())
    if os.environ.get('HORSE_APPEARANCE_RECEIPT'):
        Path(os.environ['HORSE_APPEARANCE_RECEIPT']).write_text(json.dumps(assets,indent=2),encoding='utf8')
    u.log('HORSE_APPEARANCE_SAVED '+str(len(assets)))


if __name__=='__main__':
    author()
