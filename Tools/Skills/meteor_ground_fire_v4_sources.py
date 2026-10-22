"""Uneven, low residual flames: patch-stable heat, asynchronous short flares."""
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
               "min(296.0,8.0*float(User.SourceCount))*saturate(User.FuelLevel)")
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
    u.EditorAssetLibrary.set_metadata_tag(system, "MeteorV4.SourceSelectionModule",
                                          u.EditorAssetLibrary.get_metadata_tag(system, spawn_tag))
    u.EditorAssetLibrary.remove_metadata_tag(system, spawn_tag)
    angle = "(float(Particles.UniqueID)*2.39996323)"
    planar = "(Particles.FuelCell.xyz-User.SurfaceNormal*dot(Particles.FuelCell.xyz,User.SurfaceNormal))"
    patch = "frac(sin(dot(Particles.FuelCell.xyz,float3(.073,.117,.031))+User.FieldSeed*17.3)*43758.5453)"
    width = f"min(User.PatchWidth*(.48+.52*{patch})*Particles.FuelCell.a,max(0.0,User.Radius*.96-length({planar})))"
    jitter = f"(User.Side*cos({angle})+User.Forward*sin({angle}))*({width})*sqrt(Particles.FuelSeed)"
    # Preserve the sampled height, while bounding spread by wall clearance and
    # the spell disk. FuelCell.a stores clearance, not optical opacity.
    offset = f"(Particles.FuelCell.xyz+{jitter})"
    origin = f"User.Origin+{offset}+User.Up*max(3.0,User.CellSize*.25)"
    assignments(system, en, "ParticleSpawnScript", {
        "Particles.FireOrigin": (POSITION, origin),
        "Particles.Lifetime": (FLOAT, ".26+.10*Particles.FuelSeed"),
        "Particles.Position": (POSITION, origin),
        "Particles.Velocity": (VEC3, f"User.Up*(22+48*pow({patch},1.6)+10*Particles.FuelSeed)+User.Wind*.12+(User.Side*sin({angle})+User.Forward*cos({angle}))*7"),
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
    phase = f"({patch}*19.73)"
    pulse = f"(.68+.22*sin(User.FieldAge*(1.7+{patch})+{phase})+.10*sin(User.FieldAge*4.1+{phase}*.37))"
    flare = f"(1+.28*step(.82,{patch})*pow(saturate(sin(User.FieldAge*2.2+{phase})),8))"
    ignition = "saturate((User.FieldAge-length(Particles.FuelCell.xyz)/max(1.0,User.Radius)*.18)/.12)"
    strength = f"(.48+.52*pow({patch},1.3))*{pulse}*{flare}*{envelope}*{ignition}"
    expression(system, en, stage, module, "Density", f".032*({strength})")
    expression(system, en, stage, module, "Temperature", f"(3.4+1.6*{patch})*({strength})")
    expression(system, en, stage, module, "Velocity", "Particles.Velocity")
    expression(system, en, stage, module, "Velocity Scale", ".8")
    expression(system, en, stage, module, "Radius", f"max(User.CellSize*1.05,9.0)*(.85+.3*{patch})")
    put(system, en, stage, module, "Divergence", "(Value=0.0)")
    put(system, en, stage, module, "Transform To WorldSpace", "(Value=0)", "/Script/Niagara.NiagaraBool")
