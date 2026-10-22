"""Meteor V5: contact first, delayed fracture blast, then fine falling dust."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/MeteorImpactWeightV5_20261022"
DEST = "/Game/Skills/FireMagic20260921/MeteorImpactWeightV5"
OLD = "/Game/Skills/FireMagic20260921/RealisticV5"
sys.path[:0] = [str(ROOT / "Tools/Skills"), str(ROOT / "Tools/Fluids")]
u.RainAssetEditor = u.DragonBreathAuthorLibrary
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import expression
from build_fireball_slow_burn import smooth
from fluid_contact_nodes import contact_nodes, clear_contact_tags

VEC4 = "/Script/CoreUObject.Vector4f"
SEED = "frac(float(Particles.UniqueID)*.61803398875+.173)"
VAR = "frac(float(Particles.UniqueID)*.41421356237+.317)"
ANGLE = "(float(Particles.UniqueID)*2.39996323+.4)"
DIR = f"float3(cos({ANGLE}),sin({ANGLE}),0)"
A, N = "Particles.Age", "Particles.NormalizedAge"
R = "User.ImpactRadius"
HEIGHT = "clamp(sqrt(User.ImpactRadius/652.5),.85,1.25)"


def own(source, name):
    path = DEST + "/" + name
    asset = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else \
        u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DEST, u.load_asset(source))
    if not asset:
        raise RuntimeError("Cannot create " + path)
    return asset


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    eal = u.EditorAssetLibrary
    names = ["M_MeteorBlast", "NS_MeteorImpact"]
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(DEST + "/" + name for name in names):
        raise RuntimeError("Preserve unsaved impact edits")
    eal.make_directory(DEST)
    material = own(OLD + "/M_NaturalImpact", names[0])
    # Keep the owned native 12x12 explosion and its opacity/thermal decoding.
    # Increase the short burst before its existing single exposure compensation.
    if not eal.get_metadata_tag(material, "Meteor.ImpactGainV4"):
        exposure = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_EMISSIVE_COLOR)
        if not isinstance(exposure, u.MaterialExpressionEyeAdaptationInverse):
            raise RuntimeError("Expected one existing exposure compensation")
        inputs = LIB.get_inputs_for_material_expression(material, exposure)
        gain = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter)
        gain.set_editor_property("parameter_name", "MeteorImpactGain")
        gain.set_editor_property("default_value", 1.5)
        multiply = LIB.create_material_expression(material, u.MaterialExpressionMultiply)
        for source, output, target, pin in [(inputs[0], "", multiply, "A"), (gain, "", multiply, "B"),
                (multiply, "", exposure, str(LIB.get_material_expression_input_names(exposure)[0]))]:
            if not LIB.connect_material_expressions(source, output, target, pin):
                raise RuntimeError("Impact gain connection failed")
        eal.set_metadata_tag(material, "Meteor.ImpactGainV4", "1.5 before existing exposure")
    material.set_editor_property("enable_responsive_aa", True)
    material.set_editor_property("disable_depth_test", False)
    material.set_editor_property("translucency_pass", u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    if not u.DragonBreathAuthorLibrary.compile_material_assets([material]):
        raise RuntimeError("Impact material compile failed")

    system = own(OLD + "/NS_MeteorNaturalImpact", names[1])
    before = []
    for name in emitters(system):
        before.append({"emitter": name, "renderer": str(API.call_method("GetRendererData", (ref(system, name, renderer=0),)).get_editor_property("property_values"))})
        API.call_method("RemoveEmitter", (ref(system, name),))
    (OUT / "impact-source-renderers.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    defaults = [("ImpactRadius", FLOAT, "(Value=652.5)"), ("LocalUp", VEC3, "(X=0,Y=0,Z=1)"),
                ("SurfaceHit", FLOAT, "(Value=1)"), ("DetailReduction", FLOAT, "(Value=0)"),
                ("Wind", VEC3, "(X=0,Y=0,Z=0)"), ("WetImpact", FLOAT, "(Value=0)")]
    if not u.DragonBreathAuthorLibrary.set_fluid_user_defaults(system, json.dumps([
            {"name": "User."+name, "type": typ, "value": value} for name, typ, value in defaults])):
        raise RuntimeError("Impact defaults failed")
    lifecycle_source = u.load_asset("/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small")
    lifecycle = {key: u.DragonBreathAuthorLibrary.read_input(lifecycle_source, "Explosion", "EmitterUpdateScript", "EmitterState", key)
                 for key in ["Life Cycle Mode", "Loop Behavior"]}
    lifecycle["Life Cycle Mode"] = lifecycle["Life Cycle Mode"].replace("NewEnumerator0", "NewEnumerator1").replace('"System"', '"Self"')
    lifecycle["Loop Behavior"] = lifecycle["Loop Behavior"].replace("NewEnumerator0", "NewEnumerator1").replace('"Infinite"', '"Once"')

    def layer(name, mat, count, delay, life, size, position, color, frames=1, dynamic="float4(0,0,0,0)", dust=False):
        # The isolated author host shares content, not the main project's tool
        # bootstrap. Build this one-shot stack directly from the owned template.
        API.call_method("AddEmitter", (system, u.load_asset("/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core"), name))
        trim(system, name, {"EmitterUpdateScript": ["EmitterState"],
                           "ParticleSpawnScript": ["InitializeParticle"], "ParticleUpdateScript": ["ParticleState"]})
        for script in ["ParticleSpawnScript", "ParticleUpdateScript"]:
            eal.remove_metadata_tag(system, "Fireball.Assignments." + name + "." + script)
        setdata("SetEmitterData", u.NiagaraExt_EmitterData, ref(system, name),
                {"bLocalSpace": True, "SimTarget": "CPUSim", "bInterpolatedSpawning": False})
        setdata("SetRendererData", u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
            "Material": mat.get_path_name(), "MaterialUserParamBinding": {"Parameter": {"Name": "None"}},
            "Alignment": "Unaligned", "FacingMode": "FaceCamera", "SubImageSize": {"X": frames, "Y": frames},
            "bSubImageBlend": frames > 1, "PivotInUVSpace": {"X": .5, "Y": .5},
            "bCastShadows": False, "bUseMaterialCutoutTexture": False, "CutoutTexture": None,
            "bEnableCameraDistanceCulling": True, "MinCameraDistance": 0, "MaxCameraDistance": 10000})
        for key, value in lifecycle.items():
            put(system, name, "EmitterUpdateScript", "EmitterState", key, value, "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum")
        put(system, name, "EmitterUpdateScript", "EmitterState", "Loop Duration", "(Value=2.2)")
        API.call_method("AddModule", (ref(system, name, "EmitterUpdateScript"), u.load_asset("/Niagara/Modules/Emitter/SpawnBurst_Instantaneous")))
        count_expr = str(count)
        if dust:
            count_expr = f"floor({count}*(1-saturate(User.DetailReduction))+.5)"
        if name == "GroundDust":
            count_expr = f"(User.WetImpact<.5 && User.SurfaceHit>.5?{count_expr}:0)"
        expression(system, name, "EmitterUpdateScript", "SpawnBurst_Instantaneous", "Spawn Count", count_expr)
        put(system, name, "EmitterUpdateScript", "SpawnBurst_Instantaneous", "Spawn Time", f"(Value={delay})")
        common = {"Particles.Position": (POSITION, position), "Particles.Velocity": (VEC3, "float3(0,0,0)"),
                  "Particles.SpriteSize": (VEC2, size), "Particles.Color": (COLOR, color),
                  "Particles.SpriteRotation": (FLOAT, "0"), "Particles.SpriteUVScale": (VEC2, "float2(1,1)"),
                  "Particles.SpriteAlignment": (VEC3, "User.LocalUp"),
                  "Particles.SubImageIndex": (FLOAT, f"{frames*frames-1}*saturate({N})"),
                  "Particles.DynamicMaterialParameter": (VEC4, dynamic)}
        assignments(system, name, "ParticleSpawnScript", {"Particles.Lifetime": (FLOAT, life), **common})
        assignments(system, name, "ParticleUpdateScript", common)
        if dust:
            clear_contact_tags(system, name)
            contact_nodes(system, name)

    # Fast central detonation followed by irregular lobes, not a second tall field.
    envelope = "(1-" + smooth(".42", "1.0", N) + ")"
    glow = f"float4(26*pow(1-{N},2)+.2,1,1,1)"
    layer("ContactFlash", material, 1, 0, ".075", f"float2(240,80)*{HEIGHT}*(.3+.7*(1-exp(-{A}*70)))",
          "User.LocalUp*20", f"float4(.5,.38,.27,{envelope})", 12, glow)
    layer("ImpactCore", material, 1, .025, ".29", f"float2(390,310)*{HEIGHT}*(.28+.72*(1-exp(-{A}*36)))",
          f"User.LocalUp*(80+{A}*55)*{HEIGHT}", f"float4(.49,.38,.28,{envelope})", 12, glow)
    layer("BlastLobes", material, 5, .045, f".42+.20*{VAR}",
          f"float2(245,220)*{HEIGHT}*(.72+.35*{VAR})*(.42+.68*(1-exp(-{A}*18)))",
          f"{DIR}*{R}*(.035+(.14+.13*{SEED})*(1-exp(-{A}*9)))+User.LocalUp*(55+{A}*(65+45*{VAR}))*{HEIGHT}",
          f"float4(.47,.36,.27,.92*{envelope})", 12, glow)
    rolling = u.load_asset(OLD + "/M_NaturalRollingFlame")
    layer("ResidualRoll", rolling, 4, .11, f".48+.24*{VAR}",
          f"float2(115,155)*{HEIGHT}*(.7+.45*{SEED})*(.65+.5*{N})",
          f"{DIR}*{R}*(.08+.3*{SEED})*(1-exp(-{A}*8))+User.LocalUp*(30+{A}*35)*{HEIGHT}",
          "float4(1.8,.46,.045,.8*(1-" + smooth(".24", "1.0", N) + "))", 6, f"float4({VAR},.5+{N}*1.4,0,0)")
    smoke = u.load_asset("/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke")
    if not rolling or not smoke:
        raise RuntimeError("Missing existing rolling fire/smoke materials")
    smoke_envelope = smooth("0", ".06", N) + "*(1-" + smooth(".28", "1.0", N) + ")"
    wind = f"User.Wind*({A}-.4*(1-exp(-{A}/.4)))"
    layer("GroundDust", smoke, 9, .012, f".50+.32*{SEED}",
          f"float2(190,62)*(.70+.5*{VAR})*(.55+.65*{N})",
          f"{DIR}*{R}*(.06+(.52+.27*{SEED})*(1-exp(-{A}*7)))+float3(0,0,18+{A}*12)+{wind}",
          f"float4(.18,.145,.105,.52*{smoke_envelope})", dynamic=f"float4({SEED},0,0,0)", dust=True)
    layer("EjectaSmoke", smoke, 4, .14, f".85+.55*{VAR}",
          f"float2(145,175)*(.65+.4*{VAR})*(.65+.65*{N})",
          f"{DIR}*{R}*(.06+.22*{SEED})*(1-exp(-{A}*4))+User.LocalUp*(45+{A}*(55+35*{VAR}))+{wind}",
          f"float4(lerp(float3(.13,.115,.095),float3(.44,.47,.48),saturate(User.WetImpact)),.36*{smoke_envelope})",
          dynamic=f"float4({SEED},0,0,0)", dust=True)
    layer("FallingAsh", smoke, 5, .25, f".75+.45*{VAR}",
          f"float2(48,32)*(.65+.65*{VAR})*(.7+.4*{N})",
          f"{DIR}*{R}*(.12+.38*{SEED})+User.LocalUp*(max(8,100+80*{VAR}-75*{A}))+{wind}",
          f"float4(.22,.20,.17,.15*{smoke_envelope})", dynamic=f"float4({SEED},0,0,0)", dust=True)
    system.set_editor_property("fixed_bounds", u.Box(min=u.Vector(-1400,-1400,-450), max=u.Vector(1400,1400,650)))
    eal.set_metadata_tag(system, "Meteor.Revision", "ContactFractureAndAshV5_20261022")
    if not u.DragonBreathAuthorLibrary.compile_rain(system, True):
        raise RuntimeError("Impact Niagara compile failed")
    saved = []
    for asset in [material, system]:
        if not eal.save_loaded_asset(asset, False):
            raise RuntimeError("Cannot save " + asset.get_path_name())
        saved.append(asset.get_path_name())
    receipt = dict(complete=True, saved_assets=saved, max_particles=29, primary_particles=11, budgeted_smoke_particles=18,
                   max_particle_lifetime=1.4, new_lights=0, rendered=False, runtime_tested=False)
    (OUT / "impact-asset-receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("METEOR_IMPACT_V5_SAVED " + json.dumps(receipt))


if __name__ == "__main__":
    run()
