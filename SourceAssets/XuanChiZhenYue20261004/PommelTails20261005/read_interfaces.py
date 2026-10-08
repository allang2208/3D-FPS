"""Read native mounting and end-cap surfaces as fabrication input."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
SRC=P.parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)

def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0]
    if obj is None:raise RuntimeError('Missing source '+name)
    bpy.context.scene.collection.objects.link(obj)
    return obj

def describe(obj):
    m=obj.data
    tree=BVHTree.FromPolygons([v.co for v in m.vertices],[list(p.vertices) for p in m.polygons])
    rings=[]
    for radius in [0,.003,.006,.009,.012,.015,.019,.023]:
        points=[]
        for i in range(8):
            a=i*math.tau/8
            hit,n,face,dist=tree.ray_cast(Vector((radius*math.cos(a),radius*math.sin(a),-.5)),Vector((0,0,1)),.55)
            points.append(None if hit is None else {'p':list(hit),'mat':m.materials[m.polygons[face].material_index].name})
        rings.append({'radius_m':radius,'hits':points})
    return {'name':obj.name,'location':list(obj.location),'scale':list(obj.scale),
        'materials':[x.name for x in m.materials],'uvs':[uv.name for uv in m.uv_layers],
        'local_bounds_m':[[min(v.co[i] for v in m.vertices) for i in range(3)],
                          [max(v.co[i] for v in m.vertices) for i in range(3)]],
        'terminal_rays':rings}

rows={}
native=P.parent/'SurfaceV2/XuanChi_SurfaceV2_Editable.blend'
for name in ['SM_XuanChi_Pommel_V2','SM_XuanChi_Tassel']:
    ob=append(native,name);rows[name]=describe(ob)
    if 'Pommel' in name:
        points=set()
        for f in ob.data.polygons:
            coords=[ob.data.vertices[i].co for i in f.vertices]
            if not any(v.z<-.000001 for v in coords):continue
            for v in coords:
                if abs(v.z)<.000001:points.add(tuple(round(x,8) for x in v))
        rows[name]['mount_perimeter']=sorted(points,key=lambda p:math.atan2(p[1],p[0]))
for key,name in [('ballast_hardened','Meteor'),('ballast_rune','JadeStar'),('ballast_magic_orb','Swiftstar')]:
    obj=append(SRC/'RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend','SM_RunePommel_'+name)
    rows[key]=describe(obj)
for key,old in [('pommel_hardened','ballast_hardened'),('pommel_runic','ballast_rune'),('pommel_mana_orb','ballast_magic_orb')]:
    obj=append(SRC/'FrostSwordPommelsRepair20260915'/old/'FrostPommel_Editable.blend','SM_FrostPommel_'+old)
    rows[key]=describe(obj)
    if key=='pommel_mana_orb':
        metal=[obj.data.vertices[i].co.copy() for f in obj.data.polygons
            if 'Bronze' in obj.data.materials[f.material_index].name for i in f.vertices]
        anchors=[]
        for k in range(4):
            angle=math.pi/4+k*math.pi/2
            sector=[v for v in metal if abs(math.atan2(math.sin(math.atan2(v.y,v.x)-angle),math.cos(math.atan2(v.y,v.x)-angle)))<.23 and math.hypot(v.x,v.y)>.014]
            anchors.append(list(min(sector,key=lambda v:v.z)))
        rows[key]['metal_cradle_anchors']=anchors
        print('MANA_CRADLE_ANCHORS',anchors)
(P/'interface_inputs.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
for key,row in rows.items():
    print(key,json.dumps({k:v for k,v in row.items() if k not in ['terminal_rays','mount_perimeter']}))
    if key=='SM_XuanChi_Pommel_V2':print('MOUNT_POINTS',len(row['mount_perimeter']),row['mount_perimeter'][::max(1,len(row['mount_perimeter'])//8)])
    elif key!='SM_XuanChi_Tassel':
        print('END_CAP',[(r['radius_m'],[(round(h['p'][2],5),h['mat']) if h else None for h in r['hits'][:4]]) for r in row['terminal_rays']])
