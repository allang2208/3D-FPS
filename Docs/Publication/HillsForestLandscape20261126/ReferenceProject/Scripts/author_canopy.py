"""Author the editable road spline class and the canopy point graph in the study project."""
import unreal as ue

ROOT = "/Game/ForestPathStudy/PCG"
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
ASSETS = ue.EditorAssetLibrary


def new_road_class():
    name = "BP_ForestPathSpline"
    path = f"{ROOT}/{name}"
    if ASSETS.does_asset_exist(path):
        return ue.load_class(None, path + "." + name + "_C")
    factory = ue.BlueprintFactory()
    factory.set_editor_property("parent_class", ue.Actor)
    blueprint = TOOLS.create_asset(name, ROOT, ue.Blueprint, factory)
    subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    parent = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)[0]
    handle, reason = subsystem.add_new_subobject(ue.AddNewSubobjectParams(
        parent_handle=parent, new_class=ue.SplineComponent, blueprint_context=blueprint))
    if not ue.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
        raise RuntimeError(str(reason))
    ue.BlueprintEditorLibrary.compile_blueprint(blueprint)
    if not ASSETS.save_loaded_asset(blueprint):
        raise RuntimeError(path)
    return ue.load_class(None, path + "." + name + "_C")


def canopy_points(road_class):
    name = "PCG_ForestPathCanopyPoints"
    if ASSETS.does_asset_exist(f"{ROOT}/{name}"):
        raise RuntimeError("A saved graph already exists. Keep its hand edits.")
    graph = TOOLS.create_asset(name, ROOT, ue.PCGGraph, ue.PCGGraphFactory())

    def node(settings_class, x, y, **values):
        item, settings = graph.add_node_of_type(settings_class)
        item.set_node_position(x, y)
        for key, value in values.items():
            settings.set_editor_property(key, value)
        return item

    def connect(start, end, pin="In"):
        if not graph.add_edge(start, "Out", end, pin):
            raise RuntimeError(f"Could not connect {start.get_name()} to {end.get_name()}.{pin}")

    graph.get_input_node().set_node_position(-360, -400)
    landscape = node(ue.PCGGetLandscapeSettings, -360, 0)
    surface = node(ue.PCGSurfaceSamplerSettings, -40, -130, unbounded=True,
                   points_per_squared_meter=0.1, point_extents=ue.Vector(100, 100, 100),
                   looseness=1.0, seed=1525505993)
    connect(landscape, surface, "Surface")

    road = node(ue.PCGGetSplineSettings, -360, 340)
    selector = road.get_settings().get_editor_property("actor_selector")
    selector.set_editor_property("actor_filter", ue.PCGActorFilter.ALL_WORLD_ACTORS)
    selector.set_editor_property("actor_selection", ue.PCGActorSelection.BY_CLASS)
    selector.set_editor_property("actor_selection_class", road_class)
    road.get_settings().set_editor_property("actor_selector", selector)
    project = node(ue.PCGProjectionSettings, -30, 310)
    connect(road, project)
    connect(landscape, project, "Projection Target")
    samples = node(ue.PCGSplineSamplerSettings, 240, 300)
    params = samples.get_settings().get_editor_property("sampler_params")
    params.set_editor_property("unbounded", True)
    samples.get_settings().set_editor_property("sampler_params", params)
    connect(project, samples, "Spline")
    extent = node(ue.PCGPointExtentsModifierSettings, 510, 300,
                  mode=ue.PCGPointExtentsModifierMode.MULTIPLY, extents=ue.Vector(1, 50, 50))
    connect(samples, extent)
    diff = node(ue.PCGDifferenceSettings, 810, 0,
                density_function=ue.PCGDifferenceDensityFunction.BINARY)
    connect(surface, diff, "Source")
    connect(extent, diff, "Differences")
    noise = node(ue.PCGAttributeNoiseSettings, 1080, 0, noise_min=0.082293, noise_max=1.0, seed=-610604799)
    connect(diff, noise)
    density = node(ue.PCGDensityFilterSettings, 1360, 0, lower_bound=0.679997, upper_bound=1.0)
    connect(noise, density)
    transform = node(ue.PCGTransformPointsSettings, 1640, 0, absolute_rotation=True,
                     offset_min=ue.Vector(0, 0, -20), offset_max=ue.Vector(0, 0, -20),
                     rotation_min=ue.Rotator(yaw=-360), rotation_max=ue.Rotator(yaw=360),
                     scale_min=ue.Vector(0.8, 0.8, 0.8), scale_max=ue.Vector(1.2, 1.2, 1.2),
                     uniform_scale=True, seed=1471765602)
    connect(density, transform)
    graph.get_output_node().set_node_position(1940, 0)
    connect(transform, graph.get_output_node(), "Out")
    if not ASSETS.save_loaded_asset(graph, False):
        raise RuntimeError(name)


ASSETS.make_directory(ROOT)
canopy_points(new_road_class())
