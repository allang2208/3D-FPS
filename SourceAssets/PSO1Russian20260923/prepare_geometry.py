"""Extract current import geometry into measured gun-root authoring frames."""
import bpy, bmesh, json
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
sources=json.loads((O/'sources.json').read_text())
report={'hosts':{},'scope':{}}

def bounds(points):
    return {'min':[min(p[k] for p in points) for k in range(3)],
            'max':[max(p[k] for p in points) for k in range(3)]}

def islands(ob):
    parent=list(range(len(ob.data.vertices)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for e in ob.data.edges:
        a,b=map(root,e.vertices);parent[a]=b
    groups={}
    for v in ob.data.vertices:groups.setdefault(root(v.index),[]).append(v.co)
    return sorted([dict(bounds(p),vertices=len(p)) for p in groups.values()],key=lambda p:-p['vertices'])

bpy.ops.wm.open_mainfile(filepath=str(S/'SVDCompletion20260923/SVD_Complete_Editable.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
kept=[]
for part in ['ScopeBody','ScopeMount','ScopeLens']:
    original=bpy.data.objects['SM_SVD_'+part]
    ob=bpy.data.objects.new('PSO_'+part,original.data.copy());bpy.context.scene.collection.objects.link(ob)
    ob.data.transform(inv@original.matrix_world);kept.append(ob)
    report['scope'][part]=dict(bounds([v.co for v in ob.data.vertices]),islands=islands(ob))
for ob in list(bpy.data.objects):
    if ob not in kept:bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PSO_SourceRoot.blend'))

for host,info in sources['hosts'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=info['source'][0],use_anim=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
    inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
    rows=[];keep=[]
    for ob in list(bpy.data.objects):
        if ob.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(ob.data)
        remove=[f for f in bm.faces if f.material_index<len(ob.data.materials) and 'manny' in ob.data.materials[f.material_index].name.lower()]
        bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(ob.data);bm.free()
        if not ob.data.polygons:continue
        xf=inv@ob.matrix_world
        ob.parent=None;ob.modifiers.clear();ob.data.transform(xf);ob.matrix_world=Matrix.Identity(4)
        rows.append({'name':ob.name,'bounds':bounds([v.co for v in ob.data.vertices]),
                     'materials':[m.name for m in ob.data.materials if m],
                     'bones':[g.name for g in ob.vertex_groups]})
        keep.append(ob)
    for ob in list(bpy.data.objects):
        if ob not in keep:bpy.data.objects.remove(ob,do_unlink=True)
    report['hosts'][host]=rows
    bpy.ops.wm.save_as_mainfile(filepath=str(O/(host+'_ReceiverReference.blend')))
(O/'geometry_frames.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PSO1_GEOMETRY_INPUTS_SAVED',flush=True)
