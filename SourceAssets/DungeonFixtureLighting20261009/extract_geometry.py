"""Read actual luminous mesh sections and transforms; no scene switch or play."""
from pathlib import Path
import json
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
catalog=json.loads((PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
inventory=json.loads((ROOT/'Receipts/asset-inventory.json').read_text('utf8'))
def v(p):return [p.x,p.y,p.z]
def path(p):return p.get_path_name() if p else None
def transform(t):
    r=t.rotation.rotator()
    return dict(position=v(t.translation),scale=v(t.scale3d),axes=[v(u.MathLibrary.get_forward_vector(r)),v(u.MathLibrary.get_right_vector(r)),v(u.MathLibrary.get_up_vector(r))])
def glowing(name):return any(k in name.lower() for k in ('glass','glow','diffus','lamp','tube','emiss','reflector'))
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
report=dict(meshes={},fixed=[],module_transforms={},variants={},catalog=catalog)
paths={row['path'].split('.')[0] for row in inventory['meshes']}
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    if a.actor_has_tag('DungeonRouteGenerated'):continue
    lights=a.get_components_by_class(u.LocalLightComponent)
    meshes=[]
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m:continue
        if 'fixture' in m.get_name().lower() or any(glowing(str(s.material_slot_name)+' '+str(path(s.material_interface))) for s in m.static_materials):
            paths.add(path(m).split('.')[0]);meshes.append(dict(mesh=path(m).split('.')[0],**transform(c.get_world_transform())))
    if meshes or lights:
        report['fixed'].append(dict(label=a.get_actor_label(),meshes=meshes,lights=[dict(
            path=path(c),type=c.get_class().get_name(),position=v(c.get_world_location()),forward=v(c.get_forward_vector()),
            intensity=c.intensity,units=str(c.intensity_units),radius=c.attenuation_radius,shadows=c.cast_shadows,
            function=path(c.light_function_material),rotation=[c.get_world_rotation().pitch,c.get_world_rotation().yaw,c.get_world_rotation().roll],
            source_radius=c.source_radius if isinstance(c,u.PointLightComponent) else None,
            source_length=c.source_length if isinstance(c,u.PointLightComponent) else None) for c in lights]))
for name in sorted(paths):
    mesh=u.load_asset(name)
    if not mesh:raise RuntimeError(name)
    sections=[]
    for i in range(mesh.get_num_sections(0)):
        slot=mesh.static_materials[i] if i<len(mesh.static_materials) else None
        mat=str(slot.material_slot_name)+' '+str(path(slot.material_interface)) if slot else ''
        if not glowing(mat) and not name.endswith('CeilingFixtures'):continue
        vertices,triangles,normals,uvs,tangents=u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,i)
        sections.append(dict(material=mat,section=i,vertices=[v(p) for p in vertices],triangles=list(triangles)))
    report['meshes'][name]=sections
def part_transform(p):
    rot=u.Rotator(pitch=p.get('pitch',0),yaw=p.get('yaw',0),roll=p.get('roll',0))
    return dict(mesh=p['mesh'].split('.')[0],position=p.get('position',[0,0,0]),scale=p.get('scale',[1,1,1]),
        axes=[v(u.MathLibrary.get_forward_vector(rot)),v(u.MathLibrary.get_right_vector(rot)),v(u.MathLibrary.get_up_vector(rot))])
for m in catalog['modules']:
    report['module_transforms'][m['id']]=[part_transform(p) for p in m['parts'] if p['mesh'].split('.')[0] in paths]
    if m.get('station_workshop'):
        for p in m['station_workshop']['variants'][0]['parts']:
            if 'TaskLamp' in p['mesh']:report['module_transforms'][m['id']].append(part_transform(p))
for gate,themes in catalog['facility_flow']['route_portal_variants'].items():
    report['variants'][gate]={key:[part_transform(p) for p in parts if p['mesh'].split('.')[0] in paths] for key,parts in themes.items()}
(ROOT/'Receipts/geometry.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf8')
print('FIXTURE_GEOMETRY',len(report['meshes']),'meshes;',len(report['fixed']),'fixed actors;',sum(len(s['vertices']) for ss in report['meshes'].values() for s in ss),'vertices')
