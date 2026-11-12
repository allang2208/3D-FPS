"""Read the existing atmosphere and plant interfaces needed for authoring."""
import json
import re
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestAtmosphere20261110')
BASE = '/Game/WorldGeneration/TemperateHills'
LIB = u.MaterialEditingLibrary
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
    u.SystemLibrary.execute_console_command(world, 'Editor.AsyncStaticMeshCompilation 0')
report = {'sky': {}, 'weather': {}, 'meshes': {}, 'materials': {}, 'graphs': {}, 'biome': {}}
for name, key in [('Ultra_Dynamic_Sky', 'sky'), ('Ultra_Dynamic_Weather', 'weather')]:
    obj = u.get_default_object(u.load_class(None, '/Game/UltraDynamicSky/Blueprints/' + name + '.' + name + '_C'))
    raw = Path('D:/FPS3D/FPSGAME/Content/UltraDynamicSky/Blueprints/' + name + '.uasset').read_bytes()
    names = set(dir(obj)) | {s.decode('ascii') for s in re.findall(rb'[ -~]{5,90}',raw)}
    for prop in sorted(names):
        if any(s in prop.lower() for s in ('fog', 'sun ', 'sky light', 'exposure', 'wind', 'contrast', 'saturation')):
            try: report[key][prop] = str(obj.get_editor_property(prop))
            except Exception: pass
da = u.load_asset(BASE + '/DA_TemperateHillsStreaming')
for name in ('valley_fog_density', 'river_mist_density', 'valley_fog_material', 'valley_fog_class'):
    report['biome'][name] = str(da.get_editor_property(name))
for role in ('trees', 'forest_saplings', 'forest_ferns', 'shrubs'):
    for soft in da.get_editor_property(role):
        mesh = u.load_asset(soft.get_path_name())
        if not mesh: continue
        props = {}
        for prop in ('asset_user_data', 'default_animating_rig', 'default_mesh_deformer'):
            try: props[prop] = str(mesh.get_editor_property(prop))
            except Exception: pass
        try:
            props['userdata'] = [{v.get_class().get_name(): {p:str(v.get_editor_property(p)) for p in ('is_enabled','is_ground_cover','gust_attenuation','simulation_groups')}} for v in mesh.get_editor_property('asset_user_data') if v and v.get_class().get_name() == 'DynamicWindSkeletalData']
        except Exception as ex: props['userdata_error'] = str(ex)
        report['meshes'][mesh.get_path_name()] = props
        slots = mesh.get_editor_property('materials' if isinstance(mesh,u.SkeletalMesh) else 'static_materials')
        for slot in slots:
            mat = slot.get_editor_property('material_interface')
            if not mat or mat.get_path_name() in report['materials']: continue
            report['materials'][mat.get_path_name()] = {
                'scalars': {str(p):LIB.get_material_instance_scalar_parameter_value(mat,p) for p in LIB.get_scalar_parameter_names(mat)},
                'switches': {str(p):LIB.get_material_instance_static_switch_parameter_value(mat,p) for p in LIB.get_static_switch_parameter_names(mat)}}
for soft in da.get_editor_property('graphs'):
    graph = u.load_asset(soft.get_path_name())
    nodes=[]
    for node in graph.get_editor_property('nodes'):
        settings=node.get_settings()
        if 'Spawner' in settings.get_class().get_name():
            try: nodes.append(settings.get_editor_property('mesh_selector_parameters').get_editor_property('template_descriptor').export_text())
            except Exception as ex: nodes.append(str(ex))
    report['graphs'][graph.get_path_name()]=nodes
(ROOT/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('FOREST_ATMOSPHERE_INPUTS_READ')
