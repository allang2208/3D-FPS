"""Read the head material/pose inputs involved in the reported facial defect."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/JasonFaceRepair20261003')
ROOT.mkdir(parents=True, exist_ok=True)
def path(obj):
    return obj.get_path_name() if obj else None
def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None
result = {'meshes': {}, 'materials': {}, 'runtime': []}
mesh_paths = ['/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head',
              '/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body']
for mesh_path in mesh_paths:
    mesh = u.load_asset(mesh_path)
    result['meshes'][mesh_path] = {'materials': [
        {'slot': str(m.material_slot_name),
         'material': path(m.material_interface)} for m in mesh.materials],
        'post_process': path(prop(mesh, 'post_process_anim_blueprint'))}
for name in ['MI_FaceDown','MI_Face_Skin_Baked_LOD0','MI_Body_Baked','MI_Teeth_Baked','MI_EyeL_Baked','MI_EyeR_Baked']:
    mat = u.load_asset('/Game/AsianMale_Jason/Material/' + name)
    chain = []
    while mat:
        entry = {'path': path(mat), 'class': mat.get_class().get_name()}
        for kind in ['texture', 'scalar', 'vector']:
            params = prop(mat, kind + '_parameter_values')
            if params is not None:
                entry[kind] = {str(p.parameter_info.name): path(p.parameter_value) if kind == 'texture'
                               else str(p.parameter_value) for p in params}
        entry['base_overrides'] = str(prop(mat, 'base_property_overrides'))
        chain.append(entry)
        mat = prop(mat, 'parent')
    result['materials'][name] = chain
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        for comp in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh = comp.skeletal_mesh_asset
            if not mesh or 'Jason' not in mesh.get_name():
                continue
            entry = {'actor': actor.get_name(), 'component': comp.get_name(), 'mesh':path(mesh),
                     'materials': [path(comp.get_material(i)) for i in range(comp.get_num_materials())],
                     'anim_instance': path(comp.get_anim_instance()), 'bones': {}}
            for bone in ['head','neck_01','FACIAL_C_FacialRoot','FACIAL_C_Jaw','FACIAL_L_Eye','FACIAL_R_Eye']:
                if comp.get_bone_index(bone) >= 0:
                    entry['bones'][bone] = str(comp.get_socket_transform(bone,u.RelativeTransformSpace.RTS_COMPONENT))
            result['runtime'].append(entry)
(ROOT/'face_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('JASON_FACE_INPUTS ' + str(ROOT/'face_inputs.json'))
print(json.dumps(result['meshes']))
print(json.dumps(result['runtime']))
