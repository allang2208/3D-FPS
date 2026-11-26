"""Build village-only Normandy triplanar variants with scan-driven near-field parallax."""
import json
import os
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wall_material_sampling import FLAT, FLAT_RELIEF, enable_flat, share_relief_height

E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
SRC = '/Game/UnrealNormandy/'
DEST = '/Game/WorldGeneration/TemperateHills/VillageMasonry/Relief/'
ROLES = ('MI_Main_StoneWall_00A', 'MI_Main_StoneWall_00B_Gray', 'MI_StoneWall_Pieces_00A', 'MI_Main_Mortar_00A')
outputs = []


def copy(path, name):
    asset = E.duplicate_asset(path, DEST+name)
    if not asset:
        raise RuntimeError('Unable to duplicate '+path)
    asset.modify()
    return asset


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Unable to save '+asset.get_path_name())
    outputs.append(asset.get_path_name().split('.')[0])


def wire(src, target, pin=''):
    if not L.connect_material_expressions(src, '', target, pin):
        raise RuntimeError(f'Unable to wire {src.get_name()} to {target.get_name()}.{pin}')


def add(fn, cls, x, y):
    return L.create_material_expression_in_function(fn, cls, x, y)


def custom(fn, name, code, data, size, x, y):
    n = add(fn, u.MaterialExpressionCustom, x, y)
    n.set_editor_property('desc',name)
    n.set_editor_property('description',name)
    n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for label in data:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',label)
        pins.append(pin)
    n.set_editor_property('inputs',pins)
    for label, src in data.items():
        wire(src,n,label)
    return n


def height_source(name):
    src = 'T_'+name+'_Height'
    obj = copy(SRC+'Textures/'+src,src+'_Relief')
    # Explicit-derivative lookup in the relief node uses a standard linear G8 sampler.
    obj.set_editor_property('virtual_texture_streaming',False)
    obj.set_editor_property('srgb',False)
    obj.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
    obj.set_editor_property('max_texture_size',1024)
    save(obj)
    return obj


def relief_mapping(layer, height):
    fn = copy(SRC+'MaterialFunctions/MF_VTA_TriplanarMapping','MF_ReliefProjection'+layer)
    graph = L.get_material_function_expressions(fn)
    declarations = {str(e.get_editor_property('name')):e for e in graph if isinstance(e,u.MaterialExpressionNamedRerouteDeclaration)}
    inputs = lambda e: L.get_inputs_for_material_function_expression(fn,e)
    uv_nodes = [declarations[axis+' Projection UVs'] for axis in 'XYZ']
    uv = [inputs(node)[0] for node in uv_nodes]
    height_map = add(fn,u.MaterialExpressionTextureObjectParameter,-1600,3600)
    height_map.set_editor_property('parameter_name','VillageHeight'+layer)
    height_map.set_editor_property('texture',height)
    height_map.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    depth = add(fn,u.MaterialExpressionScalarParameter,-1600,3800)
    depth.set_editor_property('parameter_name','VillageReliefCm'+layer)
    depth.set_editor_property('default_value',1.1)
    eye = add(fn,u.MaterialExpressionCameraVectorWS,-1600,4000)
    distance = add(fn,u.MaterialExpressionPixelDepth,-1600,4200)
    # Six base texture reads need not become six ray marches. Find the dominant native
    # plane once, fade the parallax across near-ties, and shift all three projections
    # by the same surface-tangent displacement. Native colour/normal/RHAOM stay registered.
    code = '''
#if VERTEXSHADER
return float3(0,0,0);
#else
// Keep gradients quad-wide across the cutoff and dominant-plane boundaries.
float2 gx=ddx(UVX),gy=ddy(UVX), hx=ddx(UVY),hy=ddy(UVY), jx=ddx(UVZ),jy=ddy(UVZ);
[branch] if(DistanceCm>=1150.0) return float3(0,0,0);
float fade=1.0-smoothstep(350.0,1150.0,DistanceCm);
float3 N=normalize(Norm), weight=abs(N);
float3 a=weight;
float hi=max(a.x,max(a.y,a.z));
float mid=max(min(a.x,a.y),min(max(a.x,a.y),a.z));
float seam=smoothstep(0.02,0.16,hi-mid);
[branch] if(fade*seam*DepthCm<=0.0001) return float3(0,0,0);
float3 V=normalize(Eye);
float facing=saturate(dot(N,V));
bool x=weight.x>=weight.y && weight.x>=weight.z;
bool y=weight.y>=weight.z;
float2 uv=x?UVX:(y?UVY:UVZ);
float h=Texture2DSampleGrad(Height,HeightSampler,uv,x?gx:(y?hx:jx),x?gy:(y?hy:jy)).r;
return (V-N*facing)*((h-0.5)*DepthCm*fade*seam/(max(0.38,facing)*max(1.0,TileCm)));
#endif'''
    offset = custom(fn,'Near-field scan relief',code,dict(Norm=declarations['VertexNormal'],Eye=eye,
                    DistanceCm=distance,Height=height_map,DepthCm=depth,TileCm=declarations['Tile Size'],
                    UVX=uv[0],UVY=uv[1],UVZ=uv[2]),3,-1150,3900)
    for index,(base,dst) in enumerate(zip(uv,uv_nodes)):
        mask,sign=inputs(base)
        channels=''.join(c for c,prop in zip('xyz','rgb') if mask.get_editor_property(prop))
        if len(channels)!=2:
            raise RuntimeError('Expected a two-axis projection in '+fn.get_name())
        shift=custom(fn,'Offset native '+'XYZ'[index]+' projection','return Base + AxisSigns*Shift.'+channels+';',
                     dict(Base=base,AxisSigns=sign,Shift=offset),2,-700,3800+index*180)
        wire(shift,dst)
    L.update_material_function(fn)
    return fn


def redirect(owner, old, new):
    is_material=isinstance(owner,u.Material)
    graph=(L.get_material_expressions if is_material else L.get_material_function_expressions)(owner)
    input_nodes=L.get_inputs_for_material_expression if is_material else L.get_inputs_for_material_function_expression
    count=0
    for call in graph:
        if not isinstance(call,u.MaterialExpressionMaterialFunctionCall):
            continue
        fn=call.get_editor_property('material_function')
        if not fn or fn.get_name()!=old:
            continue
        # A duplicated function receives fresh input IDs. UE can discard inputs
        # on a function substitution even when both pins have the same visible name.
        bindings=dict(zip(L.get_material_expression_input_names(call), input_nodes(owner,call)))
        if not call.set_material_function(new):
            raise RuntimeError('Unable to substitute '+old)
        for pin,node in bindings.items():
            if node:
                wire(node,call,pin)
        count+=1
    if not count:
        raise RuntimeError('No usage of '+old)


def main():
    E.make_directory(DEST.rstrip('/'))
    source={k:u.load_asset(SRC+'MaterialInstances/'+k) for k in ROLES}
    heights={}
    def layer_height(mi,layer):
        name=L.get_material_instance_texture_parameter_value(mi,'TS'+layer+'_RGB').get_name()
        if not name.endswith('_RHAOM'):
            raise RuntimeError('Unexpected packed map '+name)
        family=name[2:-6]
        if family not in heights:
            heights[family]=height_source(family)
        return heights[family]
    master=copy(source[ROLES[0]].parent.get_path_name().split('.')[0],'M_VillageRelief_Triplanar')
    for layer in ('00','01'):
        projection=relief_mapping(layer,layer_height(source[ROLES[0]],layer))
        name='MF_TextureSet'+layer+'_Base_Triplanar'
        ts=copy(SRC+'MaterialFunctions/'+name,'MF_VillageTextureSet'+layer)
        redirect(ts,'MF_VTA_TriplanarMapping',projection)
        share_relief_height(projection, ts)
        save(projection)
        L.update_material_function(ts)
        save(ts)
        redirect(master,name,ts)
    L.recompile_material(master)
    save(master)
    instances={}
    report={}
    for name,src in source.items():
        dst=copy(src.get_path_name().split('.')[0],name)
        L.set_material_instance_parent(dst,instances.get(src.parent.get_name(),master))
        mortar=name==ROLES[-1]
        relief=(.34,.46) if mortar else ((1.35,1.05) if name==ROLES[2] else (1.18,.95))
        strength=(1.32,1.) if mortar else (1.32,2.15)
        for i,layer in enumerate(('00','01')):
            h=layer_height(src,layer)
            L.set_material_instance_texture_parameter_value(dst,'VillageHeight'+layer,h)
            L.set_material_instance_scalar_parameter_value(dst,'VillageReliefCm'+layer,relief[i])
            L.set_material_instance_scalar_parameter_value(dst,'TS'+layer+'_NormalIntensity',strength[i])
        if not mortar:
            L.set_material_instance_scalar_parameter_value(dst,'TS00_Normal_Detail_Intensity',1.5)
        if FLAT in map(str, L.get_static_switch_parameter_names(dst)):
            if name in FLAT_RELIEF and L.get_material_instance_scalar_parameter_value(dst,'NormalGlobal_Intensity') == 0.0:
                enable_flat(dst)
            else:
                L.set_material_instance_static_switch_parameter_value(dst, FLAT, False)
        L.update_material_instance(dst)
        save(dst)
        instances[name]=dst
        for i,layer in enumerate(('00','01')):
            h=L.get_material_instance_texture_parameter_value(dst,'VillageHeight'+layer)
            depth=L.get_material_instance_scalar_parameter_value(dst,'VillageReliefCm'+layer)
            if h!=layer_height(src,layer) or abs(depth-relief[i])>.005:
                raise RuntimeError('Relief parameter mismatch on '+name)
        report[name]=dict(parent=dst.parent.get_name(),height_cm=relief,normal=strength)
    (Path(os.environ['VILLAGE_RELIEF_WORK'])/'saved.json').write_text(json.dumps(dict(packages=outputs,materials=report),indent=2),encoding='utf8')

if __name__=='__main__':
    main()
