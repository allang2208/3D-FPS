"""Save Meteor V5 scorch/normal relief and its single layered spatial sound."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/MeteorImpactWeightV5_20261022"
DEST = "/Game/Skills/FireMagic20260921/MeteorImpactWeightV5"
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary

def node(m, cls, **values):
    obj = L.create_material_expression(m, cls)
    for name,value in values.items(): obj.set_editor_property(name,value)
    return obj

def wire(value, target, pin):
    source,output = value if isinstance(value,tuple) else (value,"")
    if not L.connect_material_expressions(source,output,target,pin):
        raise RuntimeError("Cannot connect "+pin)

def custom(m, code, inputs, width):
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property("input_name",name);pins.append(pin)
    obj=node(m,u.MaterialExpressionCustom,code=code,inputs=pins,
             output_type=getattr(u.CustomMaterialOutputType,"CMOT_FLOAT"+str(width)))
    for name,value in inputs.items():wire(value,obj,name)
    return obj

def scalar(m,name,value):
    return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)

def vector(m,name,value):
    return node(m,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value))

def run():
    OUT.mkdir(parents=True,exist_ok=True);E.make_directory(DEST)
    paths=[DEST+"/"+name for name in ["M_MeteorScorch","S_MeteorImpact","CON_MeteorImpact"]]
    dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(paths):raise RuntimeError("Preserve unsaved Meteor V5 targets")
    m=u.load_asset(paths[0]) if E.does_asset_exist(paths[0]) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_MeteorScorch",DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property("material_domain",u.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property("blend_mode",u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model",u.MaterialShadingModel.MSM_DEFAULT_LIT)
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    seed=scalar(m,"ImpactSeed",.37)
    field=custom(m,(ROOT/"Tools/Skills/meteor_scorch_v5.hlsl").read_text(encoding="utf-8"),{"UV":uv,"Seed":seed},4)
    world=node(m,u.MaterialExpressionWorldPosition)
    center=vector(m,"ImpactCenter",(0,0,0,1));normal=vector(m,"SurfaceNormal",(0,0,1,1))
    fade=scalar(m,"ScarFade",1);heat=scalar(m,"ImpactHeat",1)
    opacity=custom(m,"return F.y*Fade*(1-smoothstep(10,18,abs(dot(World-Center,N))));",
                   {"F":field,"Fade":fade,"World":world,"Center":(center,"RGB"),"N":(normal,"RGB")},1)
    base=custom(m,"return lerp(float3(.047,.036,.027),float3(.014,.012,.011),saturate(F.y*.9+F.x*.7));",{"F":field},3)
    relief=custom(m,"return normalize(float3(F.zw,1));",{"F":field},3)
    glow=custom(m,"return float3(3.8,.26,.018)*F.x*Heat*Fade;",{"F":field,"Heat":heat,"Fade":fade},3)
    exposed=node(m,u.MaterialExpressionEyeAdaptationInverse)
    wire(glow,exposed,str(L.get_material_expression_input_names(exposed)[0]))
    rough=node(m,u.MaterialExpressionConstant,r=.94);spec=node(m,u.MaterialExpressionConstant,r=.05)
    outputs={"BASE_COLOR":base,"NORMAL":relief,"ROUGHNESS":rough,"SPECULAR":spec,"OPACITY":opacity,"EMISSIVE_COLOR":exposed}
    for key,value in outputs.items():
        if not L.connect_material_property(value,"",getattr(u.MaterialProperty,"MP_"+key)):
            raise RuntimeError("Scorch output "+key)
    slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for pin,value in {"BaseColor":base,"Normal":relief,"Roughness":rough,"Specular":spec,"Opacity":opacity,"Emissive Color":exposed}.items():
        wire(value,slab,pin)
    decal=node(m,u.MaterialExpressionSubstrateConvertToDecal)
    wire(slab,decal,str(L.get_material_expression_input_names(decal)[0]))
    if not L.connect_material_property(decal,"",u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError("Scorch Substrate output")
    if not u.DragonBreathAuthorLibrary.compile_material_assets([m]):raise RuntimeError("Scorch material compile failed")

    concurrency=u.load_asset(paths[2]) if E.does_asset_exist(paths[2]) else u.AssetToolsHelpers.get_asset_tools().create_asset(
        "CON_MeteorImpact",DEST,u.SoundConcurrency,u.SoundConcurrencyFactory())
    settings=concurrency.get_editor_property("concurrency")
    settings.set_editor_property("max_count",4);settings.set_editor_property("limit_to_owner",False)
    settings.set_editor_property("resolution_rule",u.MaxConcurrentResolutionRule.STOP_FARTHEST_THEN_OLDEST)
    settings.set_editor_property("voice_steal_release_time",.04);concurrency.set_editor_property("concurrency",settings)
    task=u.AssetImportTask();task.filename=str(OUT/"S_MeteorImpact.wav");task.destination_path=DEST
    task.destination_name="S_MeteorImpact";task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.SoundFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);sound=u.load_asset(paths[1])
    if not isinstance(sound,u.SoundWave):raise RuntimeError("Impact sound import failed")
    sound.set_editor_property("looping",False);sound.set_editor_property("volume",.8)
    sound.set_editor_property("loading_behavior",u.SoundWaveLoadingBehavior.FORCE_INLINE)
    sound.set_editor_property("attenuation_settings",u.load_asset("/Game/Skills/FireMagic20260921/ATT_FireMagic"))
    sound.set_editor_property("override_concurrency",False);sound.set_editor_property("concurrency_set",{concurrency})
    saved=[]
    for asset in [m,concurrency,sound]:
        if not E.save_loaded_asset(asset,False):raise RuntimeError("Cannot save "+asset.get_path_name())
        saved.append(asset.get_path_name())
    receipt=dict(complete=True,saved_assets=saved,scar="Visual relief only, owned by active meteor, no collision changes",
                 sound_concurrency=4,rendered=False,auditioned=False,runtime_tested=False)
    (OUT/"scorch-audio-receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print("METEOR_SCORCH_AUDIO_SAVED "+json.dumps(receipt))

if __name__=="__main__":run()
