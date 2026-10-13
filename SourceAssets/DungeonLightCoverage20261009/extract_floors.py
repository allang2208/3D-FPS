"""Read saved light recipes and imported supporting surfaces without switching maps."""
from pathlib import Path
import json,re
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OUT=ROOT/'Receipts';OUT.mkdir(parents=True,exist_ok=True)

def v(p):return [p.x,p.y,p.z]
def floor_mesh(path):
    name=path.rsplit('/',1)[-1].split('.')[0].lower()
    # Match mesh suffixes, not room names such as StairDrop/RouteRamp.
    if any(k in name for k in ('floor','paving','gallerydeck','platformdeck','bridgedecks','recoverysteps','terracefinish')):return not any(k in name for k in ('guid','marking','floordrain','joint','detail'))
    if 'bathroominterior' in name or name=='sm_startservicetransition':return True
    return bool(re.search(r'_(structure|b1structure.*|slab|galleryslab|mezzaninestructure|platforms|stairs.*|stairwest|staireast|radialstairs|sidestairs|stairtreads|stairlandings|landings|steps|bridge|trackbed|terraces|gallery|approach|passageopenrear|throat)$',name))
def tr(t):
    r=t.rotation.rotator()
    return dict(position=v(t.translation),scale=v(t.scale3d),axes=[v(u.MathLibrary.get_forward_vector(r)),v(u.MathLibrary.get_right_vector(r)),v(u.MathLibrary.get_up_vector(r))])
def part(p):
    r=u.Rotator(pitch=p.get('pitch',0),yaw=p.get('yaw',0),roll=p.get('roll',0))
    return dict(mesh=p['mesh'].split('.')[0],position=p.get('position',[0,0,0]),scale=p.get('scale',[1,1,1]),axes=[v(u.MathLibrary.get_forward_vector(r)),v(u.MathLibrary.get_right_vector(r)),v(u.MathLibrary.get_up_vector(r))])

world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
generator=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
catalog=json.loads(generator.get_editor_property('module_catalog_json'))
report=dict(catalog=catalog,modules={},meshes={},fixed=dict(parts=[],lights=[],all_meshes=[]),portal_variants={})
for m in catalog['modules']:
    report['modules'][m['id']]=[part(p) for p in m['parts'] if floor_mesh(p['mesh'])]
for gate,themes in catalog['facility_flow']['route_portal_variants'].items():
    report['portal_variants'][gate]={theme:[part(p) for p in parts if floor_mesh(p['mesh'])] for theme,parts in themes.items()}
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    if a.actor_has_tag('DungeonRouteGenerated'):continue
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if c.static_mesh:report['fixed']['all_meshes'].append(dict(label=a.get_actor_label(),mesh=c.static_mesh.get_path_name().split('.')[0]))
        if c.static_mesh and floor_mesh(c.static_mesh.get_path_name()):
            report['fixed']['parts'].append(dict(mesh=c.static_mesh.get_path_name().split('.')[0],**tr(c.get_world_transform())))
    for c in a.get_components_by_class(u.LocalLightComponent):
        report['fixed']['lights'].append(dict(id=a.get_actor_label(),type=c.get_class().get_name(),position=v(c.get_world_location()),forward=v(c.get_forward_vector()),intensity=c.intensity,radius=c.attenuation_radius,cast_shadows=c.cast_shadows))
paths={p['mesh'] for parts in report['modules'].values() for p in parts}
paths.update(p['mesh'] for p in report['fixed']['parts'])
paths.update(p['mesh'] for themes in report['portal_variants'].values() for parts in themes.values() for p in parts)
for path in sorted(paths):
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing floor mesh '+path)
    faces=[]
    for section in range(mesh.get_num_sections(0)):
        verts,indices,normals,uvs,tangents=u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)
        for j in range(0,len(indices),3):
            ids=indices[j:j+3]
            # All authored floor assemblies are unpitched; imported normals avoid winding assumptions.
            if sum(normals[i].z for i in ids)/3>.55:
                faces.append([v(verts[i]) for i in ids])
    report['meshes'][path]=faces
(OUT/'floor-geometry.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf8')
print('COVERAGE_FLOORS',len(paths),'meshes',sum(len(x) for x in report['meshes'].values()),'upward triangles',sum(len(m['lights']) for m in catalog['modules']),'catalog lights',len(report['fixed']['lights']),'fixed lights')
