"""Yard-only finish materials. Scanned donors retain their normals, grain and scale."""
import sys
from pathlib import Path
import unreal as u
src=Path(__file__).resolve().parent
sys.path.insert(0,str(src.parents[2]/'Tools/WorldGeneration/OldChapel'))
from chapel_ground_materials import shader,wire,texture as create_sample,MUD
A=u.AssetToolsHelpers.get_asset_tools()
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard/Wear'
FURNACE='/Game/Props/BlastFurnace20260923/Textures/T_BlastFurnace_'
TIMBER='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
SACK='Mil_Trench_Equipment_Sandbag_Canvas_Single'
LINEN=f'/Game/MilitaryTrench/Assets/3D/{SACK}/Textures/T_{SACK}_'

# Engine class defaults can root graph expressions. Reuse the saved expressions on reimport.
pool=[]
def take(kind,match=lambda expr: True):
    cls=getattr(u,'MaterialExpression'+kind)
    for i,expr in enumerate(pool):
        if isinstance(expr,cls) and match(expr):
            return pool.pop(i)
    return None

def node(mat,kind):
    existing=take(kind)
    return existing or L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))

def texture(mat,path,uv):
    asset=u.load_asset(path)
    expr=take('TextureSample',lambda n: n.get_editor_property('texture')==asset)
    if expr:
        wire(uv,expr,'UVs')
        return expr
    return create_sample(mat,path,uv)

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())

def import_field(key):
    task=u.AssetImportTask()
    task.automated=True
    task.replace_existing=True
    task.filename=str(src/'Wear'/(key+'.png'))
    task.destination_path=DEST
    task.destination_name='T_Smith'+key
    A.import_asset_tasks([task])
    tex=next((o for o in task.get_objects() if isinstance(o,u.Texture2D)),None)
    if not tex: raise RuntimeError(task.filename)
    tex.srgb=False
    tex.set_editor_property('virtual_texture_streaming',False)
    tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
    tex.compression_no_alpha=False
    tex.address_x=tex.address_y=u.TextureAddress.TA_CLAMP
    save(tex)

def material(name,decal=False):
    path=DEST+'/'+name
    mat=E.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mat.modify()
    pool[:]=L.get_material_expressions(mat)
    if decal:
        mat.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    uv=node(mat,'TextureCoordinate')
    return mat,uv

def field(mat,name,uv):
    t=texture(mat,DEST+'/T_Smith'+name,uv)
    t.set_editor_property('sampler_source',u.SamplerSourceMode.SSM_FROM_TEXTURE_ASSET)
    return t
def layer(mat,title,body,pins,count):
    label='Smith yard '+title
    expr=take('Custom',lambda n: str(n.get_editor_property('desc'))==label)
    if not expr:
        expr=shader(mat,title,body,pins,count)
        expr.set_editor_property('desc',label)
    else:
        expr.set_editor_property('code',body)
        inputs=[]
        for key in pins:
            pin=u.CustomInput()
            pin.set_editor_property('input_name',key)
            inputs.append(pin)
        expr.set_editor_property('inputs',inputs)
        expr.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(count)))
        for key,value in pins.items():
            wire(value,expr,key)
    return expr

def finish(mat,outputs):
    for key,value in outputs.items():
        expr,pin=value if isinstance(value,tuple) else (value,'')
        if not L.connect_material_property(expr,pin,getattr(u.MaterialProperty,'MP_'+key)):
            raise RuntimeError(mat.get_name()+' '+key)
    errors=L.recompile_material(mat)
    if errors: raise RuntimeError(mat.get_name()+': '+str(errors))
    save(mat)

def surface(name,donor,kind):
    mat,uv=material(name)
    wear=node(mat,'TextureCoordinate')
    wear.coordinate_index=2
    if kind=='linen':
        mask=field(mat,'Roof',wear)
        color=texture(mat,donor+'B',uv)
        normal=texture(mat,donor+'N',uv)
        ar=texture(mat,donor+'ORM',uv)
        result=layer(mat,'LinenAndSmoke',"""
float l=pow(max(.001,dot(C,float3(.299,.587,.114))),.72);
float3 cloth=l*lerp(float3(.80,.64,.42),float3(1.01,.90,.68),M.b);
float3 charred=lerp(float3(.012,.012,.013),float3(.085,.078,.067),sqrt(l));
return lerp(cloth*(1.-.29*M.g),charred,pow(saturate(M.r),.85)*.95);""",
            {'C':(color,'RGB'),'M':(mask,'RGB')},3)
        rough=layer(mat,'Woven nap','return clamp(.26+.55*R+.16*M.r-.15*M.g,.52,.97);',
                    {'M':(mask,'RGB'),'R':(ar,'G')},1)
        finish(mat,{'BASE_COLOR':result,'NORMAL':(normal,'RGB'),'ROUGHNESS':rough,'AMBIENT_OCCLUSION':(ar,'R')})
    elif kind=='wood':
        color=texture(mat,donor+'Color',uv)
        normal=texture(mat,donor+'NormalDX',uv)
        ar=texture(mat,donor+'ARH',uv)
        result=layer(mat,'Polished grain and embedded dirt',"""
float l=dot(C,float3(.299,.587,.114));
float3 wood=lerp(C*float3(.71,.68,.58),float3(l*.98,l*.76,l*.48)+float3(.036,.019,.008),W.x);
return lerp(wood,wood*.40+float3(.010,.009,.006),saturate(W.y*(1.22-.46*H)));""",
          {'C':(color,'RGB'),'W':wear,'H':(ar,'B')},3)
        rough=layer(mat,'Grip gloss','return clamp(.49+.36*R+.11*W.y-.28*W.x,.31,.94);',
                    {'R':(ar,'G'),'W':wear},1)
        finish(mat,{'BASE_COLOR':result,'NORMAL':(normal,'RGB'),'ROUGHNESS':rough,'AMBIENT_OCCLUSION':(ar,'R')})
    else:
        color=texture(mat,donor+'BaseColor',uv)
        normal=texture(mat,donor+'Normal',uv)
        base_r=texture(mat,donor+'Roughness',uv)
        result=layer(mat,'Rim contact and oxide',"""
float l=dot(C,float3(.299,.587,.114));
float oxide=saturate((R-.30)*1.46+.38*W.y-.35*W.x);
float3 iron=lerp(C*.64,float3(.11,.105,.093)*(1.+l),W.x*.85);
return lerp(iron,lerp(float3(.022,.015,.011),float3(.16,.067,.031),saturate(2.4*l)),oxide*.80);""",
          {'C':(color,'RGB'),'R':(base_r,'R'),'W':wear},3)
        rough=layer(mat,'Rubbed rim','return clamp(.22+.59*R+.16*W.y-.21*W.x,.26,.95);',
                    {'R':(base_r,'R'),'W':wear},1)
        metallic=layer(mat,'Exposed iron','return saturate(.81-.48*R-.26*W.y+.28*W.x);',
                       {'R':(base_r,'R'),'W':wear},1)
        finish(mat,{'BASE_COLOR':result,'NORMAL':(normal,'RGB'),'ROUGHNESS':rough,'METALLIC':metallic})

def furnace(name,role):
    mat,uv=material(name)
    base=FURNACE+role+'_'
    color=texture(mat,base+'BaseColor',uv)
    normal=texture(mat,base+'Normal',uv)
    rough=texture(mat,base+'Roughness',uv)
    ao=texture(mat,base+'AO',uv)
    metal=texture(mat,base+'Metallic',uv)
    pos=node(mat,'VertexInterpolator')
    wire(node(mat,'PreSkinnedPosition'),pos,'')
    burn=layer(mat,'Firing bloom',"""
float streak=.56+.21*sin(.19*P.y+.044*P.z)+.13*sin(.37*P.y-.071*P.x)+.10*(1.-R);
float throat=smoothstep(124.,216.,P.z)*(1.-.22*saturate(abs(P.x+18.)/53.));
float2 q=(P.zy-float2(67.,0.))/float2(29.,20.);
float tap=exp(-dot(q,q))*smoothstep(4.,27.,P.x);
return saturate(throat*(.49+.55*streak)+tap*(.32+.46*streak));""",
        {'P':pos,'R':(rough,'R')},1)
    soot=layer(mat,'Carbon on refractory',"""
float l=dot(C,float3(.299,.587,.114));
return lerp(C,float3(.009,.010,.011)+l*float3(.20,.19,.18),B*.88);""",
         {'C':(color,'RGB'),'B':burn},3)
    r=layer(mat,'Dry carbon roughness','return lerp(R,.93,B*.70);',{'R':(rough,'R'),'B':burn},1)
    finish(mat,{'BASE_COLOR':soot,'ROUGHNESS':r,'NORMAL':(normal,'RGB'),'AMBIENT_OCCLUSION':(ao,'R'),'METALLIC':(metal,'R')})

def decal(name,key):
    mat,uv=material(name,True)
    mask=field(mat,key,uv)
    if key=='Apron':
        detail=node(mat,'TextureCoordinate')
        detail.u_tiling=7.3
        detail.v_tiling=5.6
        soil=texture(mat,MUD+'B',detail)
        result=layer(mat,'Mud, fines and cold ash',"""
float l=dot(C,float3(.299,.587,.114));
float3 dirt=lerp(C*.73,C*.40+float3(.012,.009,.005),M.g);
float3 ash=float3(.025,.024,.023)+float3(.35,.32,.30)*l;
return lerp(lerp(dirt,ash,M.r),float3(.095,.077,.057)+.72*C,M.b*.68);""",
                     {'C':(soil,'RGB'),'M':(mask,'RGB')},3)
        rough=layer(mat,'Tyre and heel compression','return clamp(.83+.13*M.r-.51*M.g+.07*M.b,.33,.97);',{'M':(mask,'RGB')},1)
    else:
        result=layer(mat,'Smoke on the facade','return lerp(float3(.012,.013,.014),float3(.077,.073,.066),saturate(M.g*1.7-.28*M.r));',
                     {'M':(mask,'RGB')},3)
        rough=(mask,'B')
    finish(mat,{'BASE_COLOR':result,'OPACITY':(mask,'A'),'ROUGHNESS':rough})

def build(import_fields=True):
    if import_fields:
        for key in ('Roof','Wall','Apron'):
            import_field(key)
    surface('M_SmithSmokeCanvas',LINEN,'linen')
    surface('M_SmithWorkedOak',TIMBER,'wood')
    surface('M_SmithWornIron',FURNACE+'WroughtIron_','iron')
    mat,uv=material('M_SmithSpentCharcoal')
    grain=texture(mat,TIMBER+'ARH',uv)
    carbon=layer(mat,'Carbon and silver ash',
                 'return lerp(float3(.008,.009,.011),float3(.090,.085,.076),pow(saturate(H),3.));',
                 {'H':(grain,'B')},3)
    normal=texture(mat,TIMBER+'NormalDX',uv)
    finish(mat,{'BASE_COLOR':carbon,'NORMAL':(normal,'RGB'),'ROUGHNESS':(grain,'G')})
    furnace('M_SmithFurnaceBrick','Firebrick')
    furnace('M_SmithFurnaceStone','Masonry')
    decal('M_SmithWallBloom','Wall')
    decal('M_SmithApronWear','Apron')
