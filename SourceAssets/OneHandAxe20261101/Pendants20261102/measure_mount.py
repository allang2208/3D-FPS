"""Read actual tail through-hole cross sections for the shared lanyard mount."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
SA=P.parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)

def load(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (source,target):target.objects=[name]
    obj=target.objects[0];bpy.context.scene.collection.objects.link(obj);return obj

def hole(obj):
    mesh=obj.data;points=[v.co for v in mesh.vertices]
    xmin,xmax=min(p.x for p in points),max(p.x for p in points)
    zmin,zmax=min(p.z for p in points),max(p.z for p in points)
    ymin,ymax=min(p.y for p in points),max(p.y for p in points)
    tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in mesh.polygons])
    step=.0002;nx=int((xmax-xmin)/step)+5;nz=int((zmax-zmin)/step)+5
    left=xmin-2*step;bottom=zmin-2*step
    empty=set()
    for i in range(nx):
        for j in range(nz):
            hit=tree.ray_cast(Vector((left+i*step,ymin-.01,bottom+j*step)),Vector((0,1,0)),ymax-ymin+.02)[0]
            if hit is None:empty.add((i,j))
    holes=[]
    while empty:
        seed=empty.pop();todo=[seed];group=[seed];outside=False
        while todo:
            i,j=todo.pop()
            outside|=i==0 or i==nx-1 or j==0 or j==nz-1
            for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if n in empty:empty.remove(n);todo.append(n);group.append(n)
        if not outside and len(group)>10:
            xx=[left+i*step for i,j in group];zz=[bottom+j*step for i,j in group]
            holes.append({'area_cells':len(group),'center_cm':[(min(xx)+max(xx))*50,0,(min(zz)+max(zz))*50],
                'extent_cm':[(max(xx)-min(xx))*100,(max(zz)-min(zz))*100]})
    if not holes:raise RuntimeError('No closed through-hole found on '+obj.name)
    return {'object':obj.name,'sample_step_cm':step*100,'holes':sorted(holes,key=lambda h:h['area_cells'],reverse=True),
        'local_bounds_cm':[[xmin*100,ymin*100,zmin*100],[xmax*100,ymax*100,zmax*100]]}

hatchet=load(P.parent/'ModulesV1/TacticalHatchet_Modules_Editable.blend','SM_TacticalHatchet_Pommel_Factory')
kukri=load(SA/'KukriModules20261026/Kukri_Modules_Editable.blend','SM_Kukri_Pommel_Factory')
result={'hatchet':hole(hatchet),'kukri':hole(kukri),'purpose':'measure mounting interfaces; no gameplay or acceptance rendering'}
catalog=json.loads((P.parents[2]/'Content/ColdSteelData/kukri-modules.json').read_text('utf-8'))
old=catalog['slots']['lanyard']['knife_lanyard_braid']['location_cm']
a=result['hatchet']['holes'][0]['center_cm'];b=result['kukri']['holes'][0]['center_cm']
result['location_cm']=[old[0]+a[0]-b[0],0,old[2]+a[2]-b[2]]
(P/'mount.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('HATCHET_PENDANT_MOUNT '+json.dumps(result),flush=True)
