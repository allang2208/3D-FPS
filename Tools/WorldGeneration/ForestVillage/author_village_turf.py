"""Add the Fab Grass scan beneath the town-only road layer on the R19 reference material."""
from pathlib import Path
import os,unreal as u
ed=u.MaterialEditingLibrary
lib=u.EditorAssetLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
base='/Game/ForestPathStudy/VillageRegion/Reference'
src=Path(os.environ['FPS_FOREST_REFERENCE_SOURCE'])/'Turf'
m=u.load_asset(base+'/M_ForestReferenceMesh')
def save(obj):
    if not lib.save_loaded_asset(obj,False):raise RuntimeError(obj.get_path_name())
def wire(a,p,b,k):
    if not ed.connect_material_expressions(a,p,b,k):raise RuntimeError(str((p,k)))
def ins(node):
    return dict(zip(map(str,ed.get_material_expression_input_names(node)),ed.get_inputs_for_material_expression(m,node)))
def texture(suffix,comp):
    name='T_VillageGrass_'+suffix
    folder=base+'/VillageGrass'
    if not lib.does_asset_exist(folder+'/'+name):
        t=u.AssetImportTask();t.filename=str(src/(name+'.png'));t.destination_path=folder;t.destination_name=name;t.automated=True
        tools.import_asset_tasks([t])
    t=u.load_asset(folder+'/'+name);t.set_editor_property('srgb',suffix=='B')
    t.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,'TC_'+comp));save(t)
    n=ed.create_material_expression(m,u.MaterialExpressionTextureObject)
    n.set_editor_property('texture',t);n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+{'B':'COLOR','N':'NORMAL','ARH':'MASKS'}[suffix]))
    return n
def author():
    tag='R20 Quixel pe1jvwp0 village turf'
    if any(n.get_editor_property('desc') in (tag,'R32 village loess') for n in ed.get_material_expressions(m)):return
    switch=ed.get_material_property_input_node(m,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    town=ins(switch)['True']
    color=ins(town)['BaseColor'];coverage=ins(color)['Alpha'];interior=ins(coverage)['A']
    split=ins(color)['A']
    def node(cls):return ed.create_material_expression(m,cls)
    inputs={'P':node(u.MaterialExpressionWorldPosition),'V':node(u.MaterialExpressionCameraVectorWS),
            'Eye':node(u.MaterialExpressionCameraPositionWS),'Albedo':texture('B','DEFAULT'),
            'Nrm':texture('N','NORMALMAP'),'Data':texture('ARH','MASKS')}
    grass=node(u.MaterialExpressionCustom)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    grass.set_editor_property('inputs',pins);grass.set_editor_property('desc',tag)
    outputs=[]
    for name,t in [('GrassNormal','FLOAT3'),('GrassRoughness','FLOAT1'),('GrassAO','FLOAT1')]:
        pin=u.CustomOutput();pin.set_editor_property('output_name',name);pin.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_'+t));outputs.append(pin)
    grass.set_editor_property('additional_outputs',outputs);grass.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    grass.set_editor_property('code',"""
float2 uv=P.xy/42.+.045*sin(P.yx*.007+P.xy*.003);
float2 dx=ddx(uv),dy=ddy(uv);
float strength=1.-smoothstep(250.,1100.,distance(Eye,P));
float2 ray=clamp(V.xy/max(.33,abs(V.z)),-2.,2.)*(.95/42.)*strength;
[branch] if(strength>0.001){
    float h=Texture2DSampleGrad(Data,DataSampler,uv,dx,dy).b-.386988;
    float h2=Texture2DSampleGrad(Data,DataSampler,uv+ray*h,dx,dy).b-.386988;
    uv+=ray*.5*(h+h2);
}
float3 packed=Texture2DSampleGrad(Data,DataSampler,uv,dx,dy).rgb;
GrassAO=packed.r; GrassRoughness=packed.g;
GrassNormal=UnpackNormalMap(Texture2DSampleGrad(Nrm,NrmSampler,uv,dx,dy));
return Texture2DSampleGrad(Albedo,AlbedoSampler,uv,dx,dy).rgb;
""")
    for k,a in inputs.items():wire(a,'',grass,k)
    for prop,ch in [('BaseColor',''),('Normal','GrassNormal'),('Roughness','GrassRoughness'),('AmbientOcclusion','GrassAO')]:
        blend=node(u.MaterialExpressionLinearInterpolate)
        wire(split,prop,blend,'A');wire(grass,ch,blend,'B');wire(interior,'',blend,'Alpha')
        if prop!='AmbientOcclusion':wire(blend,'',ins(town)[prop],'A')
        else:
            # The original road keeps its own AO at the same road/soil coverage.
            ao=node(u.MaterialExpressionLinearInterpolate)
            wire(blend,'',ao,'A');wire(split,prop,ao,'B');wire(coverage,'',ao,'Alpha');wire(ao,'',town,prop)
    errors=ed.recompile_material(m)
    if errors:raise RuntimeError(str(errors))
    save(m)
author()
