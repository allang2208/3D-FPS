"""Put each current host into its runtime attachment frame and measure contact."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/BlessedLaser20261006/Model';R=O/'MountRepair'
hosts=json.loads((R/'Hosts/hosts.json').read_text());auth=json.loads((O/'authoring.json').read_text())
S=Matrix.Diagonal((1,-1,1,1));report={}
def matrix(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:]))
def basis(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();y=z.cross(x).normalized()
    return Matrix((x,y,z)).transposed().to_4x4()
for family,e in auth.items():
    h=hosts[family];bones={n:matrix(v) for n,v in h['bones'].items()};root=bones['WPN_root']
    if family=='HK416':mount=Matrix.Identity(4)
    elif family=='RSH12':
        f=Vector((0,.9980492592,-.0624317825));up=Vector((0,.0624317825,.9980492592));origin=Vector((-.0001100056,.1150264516,-.0183265284))
        rel=basis(f,up);rel.translation=origin+f*.1395+up*.0194712;mount=root@rel@Matrix.Diagonal((.01,.01,.01,1))
    elif family=='ASH12':
        rear=bones['WPN_RearSight'];f=bones['WPN_FrontSight'].translation-rear.translation
        rotation=basis(f,rear.to_quaternion()@Vector((0,0,1)))
        mount=rotation@Matrix.Rotation(math.pi,4,'X');mount.translation=rear.translation+rotation.to_3x3()@Vector((29.5,-3.19,-8.25))
    elif family in ('M1911','G18','PitViper2011','DanWesson715'):
        up=root.to_quaternion()@Vector((0,0,1));f=bones['WPN_FrontSight'].translation-bones['WPN_RearSight'].translation;f-=up*f.dot(up)
        source=Matrix.Identity(4) if family=='PitViper2011' else basis(Vector((0,1,0)),Vector((0,0,1)))
        mount=basis(f,up)@source.inverted();mount.translation=root.translation
    else:mount=root@Matrix.Diagonal((.01,.01,.01,1))
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=h['fbx'])
    inv=S@Matrix.Diagonal((.01,.01,.01,1))@mount.inverted()@Matrix.Diagonal((100,100,100,1))@S
    verts=[];faces=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        groups={g.index for g in ob.vertex_groups if g.name.startswith('WPN_')}
        ids={v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>.5}
        transform=inv@ob.matrix_world
        local={i:transform@ob.data.vertices[i].co for i in ids}
        emitter=Vector(e['emitter_blender_m'])
        polygons=[p for p in ob.data.polygons if all(i in ids for i in p.vertices) and any((local[i]-emitter).length<.22 for i in p.vertices)]
        used=sorted({i for p in polygons for i in p.vertices});remap={i:len(verts)+j for j,i in enumerate(used)}
        verts.extend([list(local[i]) for i in used]);faces.extend([[remap[i] for i in p.vertices] for p in polygons])
    (R/'Hosts'/(family+'-geometry.json')).write_text(json.dumps(dict(vertices=verts,faces=faces),separators=(',',':')))
    f=Vector(e['forward_blender']);up=Vector(e['up_blender']);right=up.cross(f);frame=Matrix((f,right,up));origin=Vector(e['emitter_blender_m'])
    points=[frame@(Vector(v)-origin) for v in verts];tree=BVHTree.FromPolygons(points,faces)
    hits=[]
    for x in (-.055,-.045,-.035,-.025):
        for y in (-.006,0.,.006):
            hit,normal,_,dist=tree.ray_cast(Vector((x*e['scale'],y*e['scale'],.014*e['scale'])),Vector((0,0,1)),.16)
            hits.append(dict(x=x,y=y,z=round(hit.z*1000,3) if hit else None,normal=list(normal) if hit else None))
    report[family]=hits
    print('HOST_CONTACT',family,[v['z'] for v in hits],flush=True)
(R/'host_contacts.json').write_text(json.dumps(report,indent=2))
