"""Extract actual upper deck triangles under the hand bench and the cutting station."""
import json
import os
import sys
from pathlib import Path
import unreal as u

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from layout import LEVEL, PLACEMENTS

root = here.parents[3]
source = root/'SourceAssets/HillsVillageCarpenter/YardDetail'
plan = json.loads((root/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
house = next(h for h in plan['houses'] if h[0] == plan['carpenter']['house'])
basis = u.Transform(location=(house[3]*100,house[4]*100,4),rotation=u.Rotator(yaw=house[5]))
world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
sub = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
triangles = []
for actor in sub.get_all_level_actors():
    if actor.get_actor_label() not in ('Village_Carpenter_Common','Village_Carpenter_Repaired'):
        continue
    for c in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = c.static_mesh
        if not mesh or not mesh.get_name().startswith('SM_CarpenterDeck'):
            continue
        dyn, status = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(mesh.get_name())
        q = u.GeometryScript_MeshQueries
        _,verts,_ = q.get_all_vertex_positions(dyn,False)
        _,faces,_ = q.get_all_triangle_indices(dyn,False)
        points = list(u.GeometryScript_List.convert_vector_list_to_array(verts))
        polys = list(u.GeometryScript_List.convert_triangle_list_to_array(faces))
        transforms = ([c.get_instance_transform(i,True) for i in range(c.get_instance_count())]
                      if isinstance(c,u.InstancedStaticMeshComponent) else [c.get_world_transform()])
        for transform in transforms:
            local = [u.MathLibrary.inverse_transform_location(basis,u.MathLibrary.transform_location(transform,p)) for p in points]
            for f in polys:
                a,b,d = (local[i] for i in (f.x,f.y,f.z))
                if max(a.z,b.z,d.z)<-8 or min(a.z,b.z,d.z)>5: continue
                if (b.x-a.x)*(d.y-a.y)-(b.y-a.y)*(d.x-a.x) == 0: continue
                for key in ('BenchCurls','SawSlivers'):
                    (x,y,_),_,_ = PLACEMENTS[key]
                    if (min(a.x,b.x,d.x) <= x+61 and max(a.x,b.x,d.x) >= x-61 and
                        min(a.y,b.y,d.y) <= y+86 and max(a.y,b.y,d.y) >= y-86):
                        triangles.append([[round(v.x,4),round(v.y,4),round(v.z,4)] for v in (a,b,d)])
                        break
if not triangles: raise RuntimeError('No saved deck geometry in the two work areas')
(source/'deck-contact.json').write_text(json.dumps(triangles,separators=(',',':')),encoding='utf-8')
(Path(os.environ['CARPENTER_YARD_RUN'])/'floor.json').write_text(json.dumps({'triangles':len(triangles)}),encoding='utf-8')
