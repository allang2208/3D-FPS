"""Read the meshes/material sections involved in the reported equipment fit."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonEquipmentRepair20261003')
ROOT.mkdir(parents=True,exist_ok=True)
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils
def xyz(p):return [p.x,p.y,p.z]
def path(o):return o.get_path_name() if o else None
snapshot=[]
for world in u.EditorLevelLibrary.get_pie_worlds(False):
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for c in actor.get_components_by_class(u.MeshComponent):
            mesh=c.skeletal_mesh_asset if isinstance(c,u.SkeletalMeshComponent) else c.static_mesh if isinstance(c,u.StaticMeshComponent) else None
            if not mesh or not any(t in mesh.get_path_name() for t in ['Jason','Backpack']):continue
            row={'actor':actor.get_name(),'component':c.get_name(),'asset':path(mesh),'parent':path(c.get_attach_parent()),
                 'socket':str(c.get_attach_socket_name()),'relative':str(c.get_relative_transform()),
                 'materials':[path(c.get_material(i)) for i in range(c.get_num_materials())]}
            if isinstance(c,u.SkeletalMeshComponent):
                row['visible_sections']=[c.is_material_section_shown(i,0) for i in range(c.get_num_materials())]
            snapshot.append(row)
(ROOT/'runtime_inputs.json').write_text(json.dumps(snapshot,indent=2))
sources={'backpack':'/Game/Characters/SovietBackpack20261002/SM_SovietBackpack',
         'base':'/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/SK_Jason_Base',
         'chainmail':'/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/SK_Jason_ue_chainmail_shirt',
         'sweater':'/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/SK_Jason_ue_field_sweater'}
for key,p in sources.items():
    mesh=u.load_asset(p)
    if key=='backpack':
        dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        mats=mesh.static_materials
    else:
        dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        mats=mesh.materials
    _,pv,_=Q.get_all_vertex_positions(dm,False); pv=u.GeometryScript_List.convert_vector_list_to_array(pv)
    _,tv,_=Q.get_all_triangle_indices(dm,False);tv=u.GeometryScript_List.convert_triangle_list_to_array(tv)
    mids=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tv))]
    data={'asset':p,'positions':[xyz(v) for v in pv],'triangles':[xyz(t) for t in tv],
          'triangle_materials':mids,'materials':[{'slot':str(m.material_slot_name),'asset':path(m.material_interface)} for m in mats]}
    (ROOT/(key+'.json')).write_text(json.dumps(data,separators=(',',':')))
    print(key+' '+json.dumps({'triangles':len(tv),'materials':data['materials']}))
print('JASON_EQUIPMENT_INPUTS_SAVED '+str(len(snapshot)))
