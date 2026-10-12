import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordGripPair20261010')
rows=[]
for world in u.EditorLevelLibrary.get_pie_worlds(True)[:1]:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            parent=comp.get_attach_parent()
            if not comp.static_mesh:continue
            while parent and 'FPSBodyWeaponMeshComponent' not in parent.get_name():parent=parent.get_attach_parent()
            if not parent:continue
            wp=parent.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_WORLD)
            wp.scale3d=u.Vector(1,1,1)
            dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(comp.static_mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(comp.static_mesh.get_path_name())
            _,pv,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
            pv=u.GeometryScript_List.convert_vector_list_to_array(pv)
            t=comp.get_world_transform()
            vals=[wp.inverse_transform_location(t.transform_location(v)) for v in pv]
            rows.append({'asset':comp.static_mesh.get_path_name(),'component':comp.get_name(),'visible':comp.is_visible(),
                'min':[min(getattr(v,k) for v in vals) for k in ('x','y','z')],
                'max':[max(getattr(v,k) for v in vals) for k in ('x','y','z')]})
(out/'handle-parts.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
