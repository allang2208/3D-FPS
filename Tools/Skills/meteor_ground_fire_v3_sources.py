"""Surface-anchored, independently pulsing fuel patches for Meteor Ground Fire V3."""
import unreal as u
from build_fireball_assets import API, ref, setdata, assignments, put
from build_fireball_flames import trim, FLOAT, VEC3, POSITION, COLOR
from build_fireball_flight import expression

SOURCE_COUNT = 37


def build_sources(system):
    en = "ParticleSourceEmitter"
    trim(system, en, {"EmitterUpdateScript": ["EmitterState", "SpawnRate"],
                     "ParticleSpawnScript": ["InitializeParticle"], "ParticleUpdateScript": ["ParticleState"]})
    spawn_tag = "Fireball.Assignments." + en + ".ParticleSpawnScript"
    for stage in ("ParticleSpawnScript", "ParticleUpdateScript"):
        u.EditorAssetLibrary.remove_metadata_tag(system, "Fireball.Assignments." + en + "." + stage)
    setdata("SetEmitterData", u.NiagaraExt_EmitterData, ref(system, en),
            {"bLocalSpace": False, "SimTarget": "GPUComputeSim", "InterpolatedSpawnMode": "NoInterpolation"})
    top = API.call_method("GetEmitterTopology", (ref(system, en),))
    for renderer in reversed(top.get_editor_property("renderers")):
        API.call_method("RemoveRenderer", (ref(system, en, renderer=renderer.get_editor_property("renderer_index")),))

    # Each validated patch gets the same bounded sampling rate. Adding ground
    # sources never pushes all existing fuel outwards as the previous Spread did.
    expression(system, en, "EmitterUpdateScript", "SpawnRate", "SpawnRate",
               "min(444.0,12.0*float(User.SourceCount))*saturate(User.FuelLevel)")
    index = "fmod(float(Particles.UniqueID),max(1.0,float(User.SourceCount)))"
    chosen = "User.FuelCell36"
    for i in reversed(range(SOURCE_COUNT - 1)):
        chosen = f"({index}<{i + .5:.1f}?User.FuelCell{i}:{chosen})"
    assignments(system, en, "ParticleSpawnScript", {
        "Particles.FuelCell": (COLOR, chosen),
        "Particles.FuelSeed": (FLOAT, "frac((float(Particles.UniqueID)+.5)*.7548776662)"),
    })
    # A second set-parameters module reads the selected cell from the first.
    # A single map-set cannot safely read values it is simultaneously assigning.
    u.EditorAssetLibrary.set_metadata_tag(system, "MeteorV3.SourceSelectionModule",
                                          u.EditorAssetLibrary.get_metadata_tag(system, spawn_tag))
    u.EditorAssetLibrary.remove_metadata_tag(system, spawn_tag)
    angle = "(float(Particles.UniqueID)*2.39996323)"
    planar = "(Particles.FuelCell.xyz-User.SurfaceNormal*dot(Particles.FuelCell.xyz,User.SurfaceNormal))"
    width = f"min(User.PatchWidth*Particles.FuelCell.a,max(0.0,User.Radius*.96-length({planar})))"
    jitter = f"(User.Side*cos({angle})+User.Forward*sin({angle}))*({width})*sqrt(Particles.FuelSeed)"
    # Preserve the sampled height, while bounding spread by wall clearance and
    # the spell disk. FuelCell.a stores clearance, not optical opacity.
    offset = f"(Particles.FuelCell.xyz+{jitter})"
    origin = f"User.Origin+{offset}+User.Up*max(3.0,User.CellSize*.25)"
    assignments(system, en, "ParticleSpawnScript", {
        "Particles.FireOrigin": (POSITION, origin),
        "Particles.Lifetime": (FLOAT, ".30+.16*Particles.FuelSeed"),
        "Particles.Position": (POSITION, origin),
        "Particles.Velocity": (VEC3, f"User.Up*(135+85*Particles.FuelSeed)+User.Wind*.18+(User.Side*sin({angle})+User.Forward*cos({angle}))*10"),
        "Particles.Color": (COLOR, "float4(1,1,1,1)"),
    })
    # The source stays on its ground patch; only the injected gas rises.
    assignments(system, en, "ParticleUpdateScript", {
        "Particles.Position": (POSITION, "Particles.FireOrigin"),
    })
    API.call_method("AddModule", (ref(system, en, "ParticleUpdateScript"),
                                 u.load_asset("/NiagaraFluids/Modules/Particles/SetFluidSourceAttributes")))
    stage, module = "ParticleUpdateScript", "SetFluidSourceAttributes"
    envelope = "(smoothstep(0.0,.16,Particles.NormalizedAge)*(1-smoothstep(.62,1.0,Particles.NormalizedAge)))"
    phase = "dot(Particles.FuelCell.xy,float2(.017,.013))"
    pulse = f"(.82+.18*sin(User.FieldAge*2.6+{phase}))"
    ignition = "saturate((User.FieldAge-length(Particles.FuelCell.xyz)/max(1.0,User.Radius)*.18)/.12)"
    strength = f"(.86+.22*sin({phase}+1.7))*{pulse}*{envelope}*{ignition}"
    expression(system, en, stage, module, "Density", f".045*({strength})")
    expression(system, en, stage, module, "Temperature", f"(6.0+2.0*Particles.FuelSeed)*({strength})")
    expression(system, en, stage, module, "Velocity", "Particles.Velocity")
    expression(system, en, stage, module, "Velocity Scale", ".9")
    expression(system, en, stage, module, "Radius", "max(User.CellSize*1.25,12.0)")
    put(system, en, stage, module, "Divergence", "(Value=0.0)")
    put(system, en, stage, module, "Transform To WorldSpace", "(Value=0)", "/Script/Niagara.NiagaraBool")
