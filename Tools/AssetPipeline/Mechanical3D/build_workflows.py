"""Build candidate API workflows only; does not connect to ComfyUI or generate assets."""
import ast
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / 'Saved/PipelineSetup20260913'
OUT = Path(__file__).parent / 'workflows'
OUT.mkdir(exist_ok=True)

def defaults(filename, classname):
    installed = STAGE / 'installed_node_schema.json'
    if filename == 'nodes.py' and installed.exists():
        schema = json.loads(installed.read_text(encoding='utf-8-sig'))[classname]['input']
    else:
        tree = ast.parse((STAGE / filename).read_text(encoding='utf-8-sig'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'INPUT_TYPES')
        schema = ast.literal_eval(next(n.value for n in method.body if isinstance(n, ast.Return)))
    result = {}
    for key, spec in schema['required'].items():
        if len(spec) > 1 and 'default' in spec[1]:
            result[key] = spec[1]['default']
        elif isinstance(spec[0], list):
            result[key] = spec[0][0]
    return result

def node(cls, inputs):
    return {'class_type': cls, 'inputs': inputs}

def save(name, graph):
    (OUT / (name + '.api.json')).write_text(json.dumps(graph, indent=2) + '\n', encoding='utf-8')

def base():
    load = defaults('nodes.py', 'Trellis2LoadModel')
    load.update(backend='sdpa', low_vram=True, keep_models_loaded=False, sparse_backend='xformers')
    graph = {'1': node('Trellis2LoadModel', load)}
    for i, view in enumerate(('front', 'right', 'back'), 10):
        graph[str(i)] = node('LoadImage', {'image': f'mechanical3d/{view}.png'})
        prep = defaults('nodes.py', 'Trellis2PreProcessImage')
        prep.update(image=[str(i), 0], padding=24, max_size=2048, remove_background=True)
        graph[str(i+10)] = node('Trellis2PreProcessImage', prep)
    return graph

def exports(graph, prefix):
    graph['50'] = node('Trellis2MeshWithVoxelToTrimesh', {'mesh': ['4', 0], 'reorient_vertices': '90 degrees'})
    graph['51'] = node('Trellis2ExportMesh', {'trimesh': ['50', 0], 'filename_prefix': prefix + '/raw', 'file_format': 'glb'})
    # Keep a textured master; game decimation is a separate, later operation.
    graph['52'] = node('Trellis2OvoxelExportToGLB', {'mesh': ['4', 0], 'resolution': 1024, 'texture_size': 4096, 'target_face_num': 500000})
    graph['53'] = node('Trellis2ExportMesh', {'trimesh': ['52', 0], 'filename_prefix': prefix + '/textured_master', 'file_format': 'glb'})

for resolution in (32, 64, 128):
    graph = base()
    gen = defaults('nodes.py', 'Trellis2MeshWithVoxelMultiViewGenerator')
    gen.update(pipeline=['1',0], front_image=['20',0], right_image=['21',0], back_image=['22',0], seed=91301,
               pipeline_type='1024_cascade', sparse_structure_steps=16, shape_steps=32, texture_steps=24,
               sparse_structure_resolution=resolution, fill_holes=False, keep_only_shell=False,
               use_tiled_decoder=True)
    graph['4'] = node('Trellis2MeshWithVoxelMultiViewGenerator',gen)
    exports(graph, f'Mechanical3D/trellis_ss{resolution}')
    save(f'trellis_ss{resolution}',graph)

graph = base()
graph['3'] = node('Trellis2LoadMesh', {'glb_path': 'mechanical3d/base_raw.glb', 'only_vertices_and_faces': True})
gen = defaults('refiner.py','Trellis2MeshRefinerMultiView')
gen.update(pipeline=['1',0],trimesh=['3',0],front_image=['20',0],right_image=['21',0],back_image=['22',0],
           seed=91301,resolution=1024,shape_steps=32,texture_steps=24)
graph['4'] = node('Trellis2MeshRefinerMultiView',gen)
exports(graph,'Mechanical3D/refiner')
save('trellis_multiview_refiner',graph)

graph = base()
# Pixal uses projected single-view conditioning here. Do not feed ordinary TRELLIS multiview to it.
for key in ('11','12','21','22'):
    del graph[key]
graph['1']['inputs'].update(modelname='TencentARC/Pixal3D-T')
graph['1']['inputs'].pop('pixal3d_multiview', None)
gen = defaults('nodes.py','Trellis2MeshWithVoxelAdvancedGenerator')
gen.update(pipeline=['1',0],image=['20',0],seed=91301,pipeline_type='1024_cascade',
           sparse_structure_steps=16,shape_steps=32,texture_steps=24, sparse_structure_resolution=32,
           fill_holes=False,keep_only_shell=False,use_tiled_decoder=True)
# Pixal's own guidance defaults, rather than inheriting TRELLIS guidance.
gen.update(sparse_structure_guidance_strength=7.5, sparse_structure_guidance_rescale=0.7,
           sparse_structure_rescale_t=5.0, sparse_structure_guidance_interval_start=0.6,
           shape_guidance_strength=7.5, shape_guidance_rescale=0.5, shape_rescale_t=3.0,
           shape_guidance_interval_start=0.6, texture_guidance_strength=1.0,
           texture_guidance_rescale=0.0, texture_rescale_t=3.0,
           texture_guidance_interval_start=0.6)
graph['4'] = node('Trellis2MeshWithVoxelAdvancedGenerator',gen)
exports(graph,'Mechanical3D/pixal_singleview')
save('pixal_singleview',graph)
