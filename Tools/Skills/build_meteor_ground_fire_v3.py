"""Author a dedicated ground-fire solver/material; save only MeteorGroundFireV3."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "SourceAssets/MeteorGroundFireV3_20261020"
DEST = "/Game/Skills/FireMagic20260921/MeteorGroundFireV3"
SOURCE = "/Game/Skills/FireMagic20260921/MeteorFilledVolumeV2/NS_MeteorGroundVolume"
GRID = "Grid3D_Gas_Master_Emitter"
sys.path.insert(0, str(ROOT / "Tools/Skills"))
if not hasattr(u, "DragonBreathAuthorLibrary"):
    raise RuntimeError("Use the existing DragonBreathAuthor background host")
u.RainAssetEditor = u.DragonBreathAuthorLibrary
from build_fireball_assets import LIB, API, ref, setdata
from build_fireball_flames import FLOAT, VEC3, POSITION, COLOR
from meteor_ground_fire_v3_sources import build_sources, SOURCE_COUNT


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    eal = u.EditorAssetLibrary
    names = ["NS_MeteorGroundVolume", "M_MeteorGroundFlame", "MI_MeteorGroundFlame"]
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(DEST + "/" + name for name in names):
        raise RuntimeError("Preserve unsaved V3 target edits")
    source = u.load_asset(SOURCE)
    if not source:
        raise RuntimeError("Current meteor source missing")
    # Actual saved stack before authoring, for diagnosis/provenance, without
    # activating a system, rendering a preview or changing its source package.
    (OUT / "source-fluid-inputs.json").write_text(u.DragonBreathAuthorLibrary.describe_fluid_inputs(source), encoding="utf-8")
    eal.make_directory(DEST)

    def own(original, name):
        asset = u.load_asset(DEST + "/" + name) if eal.does_asset_exist(DEST + "/" + name) else \
            u.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DEST, original)
        if not asset:
            raise RuntimeError("Cannot create " + name)
        return asset

    system = own(source, names[0])
    source_mi = u.load_asset("/Game/Skills/DragonBreath20261013/VolumeV8/MI_DragonVolumeFlame_R2")
    material = own(source_mi.get_editor_property("parent"), names[1])
    instance = own(source_mi, names[2])
    LIB.set_material_instance_parent(instance, material)
    LIB.update_material_instance(instance)
    if not u.DragonBreathAuthorLibrary.compile_material_assets([material, instance]):
        raise RuntimeError("Ground fire material compilation failed")
    u.DragonBreathAuthorLibrary.prepare_fluid_stack(system)
    defaults = [
        ("Radius", FLOAT, "(Value=558)"), ("PatchWidth", FLOAT, "(Value=69.75)"),
        ("FuelLevel", FLOAT, "(Value=1)"), ("VisualFade", FLOAT, "(Value=1)"),
        ("FieldAge", FLOAT, "(Value=1)"), ("Origin", POSITION, "(X=0,Y=0,Z=-78)"),
        ("Side", VEC3, "(X=1,Y=0,Z=0)"), ("Forward", VEC3, "(X=0,Y=1,Z=0)"),
        ("Up", VEC3, "(X=0,Y=0,Z=1)"), ("SurfaceNormal", VEC3, "(X=0,Y=0,Z=1)"),
        ("Wind", VEC3, "(X=0,Y=0,Z=0)"), ("CellSize", FLOAT, "(Value=9.96875)"),
        ("WorldSpaceSize", VEC3, "(X=1276,Y=1276,Z=360)"),
        ("ResolutionMaxAxis", "/Script/Niagara.NiagaraInt32", "(Value=128)"),
        ("SourceCount", "/Script/Niagara.NiagaraInt32", "(Value=1)"),
    ] + [(f"FuelCell{i}", COLOR, "(R=0,G=0,B=0,A=1)") for i in range(SOURCE_COUNT)]
    if not u.DragonBreathAuthorLibrary.set_fluid_user_defaults(system, json.dumps([
            {"name": "User." + name, "type": typ, "value": value} for name, typ, value in defaults])):
        raise RuntimeError("Cannot install ground fire parameters")
    build_sources(system)
    changes = []

    def value(module, name, text):
        changes.append(dict(emitter=GRID, module=module, input=name, value=text))

    def number(module, name, number):
        value(module, name, f"(Value={number})")

    def expression(module, name, text):
        changes.append(dict(emitter=GRID, module=module, input=name, expression=text))

    quality = "Grid3D_Gas_QualityOverrides"
    for name in ("Resolution Max Axis", "Override.Resolution Max Axis"):
        expression(quality, name, "User.ResolutionMaxAxis")
    for name in ("Pressure Solve Iterations", "Override.Pressure Solve Iterations"):
        number(quality, name, 6)
    expression("Grid3D_Gas_InitializeEmitter", "World Size", "User.WorldSpaceSize")
    expression("Grid3D_Gas_MaterialControls", "Density Gain", ".075*saturate(User.VisualFade)")
    expression("Grid3D_Gas_MaterialControls", "Temperature Color Gain", ".4*saturate(User.VisualFade)")
    expression("Grid3D_Gas_MaterialControls", "Temperature Opacity Gain", "1.15*saturate(User.VisualFade)")
    number("Grid3D_Gas_Buoyancy", "TemperatureBuoyancy", .18)
    number("DissipateVector", "DissipationRate", .65)
    number("Grid3D_Advect_FluidAttribute", "Dissipation Rate Density", 1.8)
    number("Grid3D_Advect_FluidAttribute", "Dissipation Rate Temperature", 1.2)
    value("Grid3D_Turbulence001", "Turbulence Gain", "(X=35,Y=35,Z=55)")
    value("Grid3D_Turbulence001", "Turbulence Frequency", "(X=.22,Y=.22,Z=.22)")
    number("Grid3D_Turbulence001", "Turbulence Speed", .45)
    number("Grid3D_SmallScaleForce", "Gain", 8)
    if not u.DragonBreathAuthorLibrary.configure_fluid_inputs(system, json.dumps(changes)):
        raise RuntimeError("Incomplete ground-fire solver configuration")
    setdata("SetRendererData", u.NiagaraExt_RendererData, ref(system, GRID, renderer=0), {"bIsEnabled": False})
    setdata("SetRendererData", u.NiagaraExt_RendererData, ref(system, GRID, renderer=1),
            {"StepFactor": .85, "LightingDownsampleFactor": 2., "ShadowStepFactor": 3., "Material": instance.get_path_name()})
    system.set_editor_property("fixed_bounds", u.Box(min=u.Vector(-1080,-1080,-180), max=u.Vector(1080,1080,180)))
    eal.set_metadata_tag(system, "Meteor.Revision", "SurfacePatchesV3_20261020")
    eal.set_metadata_tag(system, "Meteor.Source", SOURCE)
    if not u.DragonBreathAuthorLibrary.compile_rain(system, True):
        raise RuntimeError("Ground fire Niagara compilation failed")
    saved = []
    for asset in (material, instance, system):
        if not eal.save_loaded_asset(asset, False):
            raise RuntimeError("Failed saving " + asset.get_path_name())
        saved.append(asset.get_path_name())
    receipt = dict(complete=True, saved_assets=saved, source=SOURCE, max_surface_patches=SOURCE_COUNT,
                   max_fuel_rate=444, max_fuel_lifetime=.46, grid_max_axis_local=128, grid_max_axis_remote=96,
                   pressure_iterations=6, visible_flame_sprites=0, added_lights=0,
                   rendered=False, runtime_tested=False, visual_acceptance=False)
    (OUT / "asset-receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("METEOR_GROUND_V3_SAVED " + json.dumps(receipt))


if __name__ == "__main__":
    run()
