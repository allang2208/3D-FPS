"""Offline closeout checks for native preservation and authored closed adapters."""
import bpy,bmesh,json,gzip,collections,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
R={'native':{},'parts':{},'errors':[]}
with gzip.open(O/'Inputs/native_geometry.json.gz','rt') as f:before=json.load(f)
with gzip.open(O/'current_geometry_check.json.gz','rt') as f:after=json.load(f)
for field in ('positions','triangles'):
    R['native'][field+'_exactly_unchanged']=before[field]==after[field]
    if before[field]!=after[field]:R['errors'].append('Native geometry changed: '+field)
selected=set(json.loads((O/'factory_triangles.json').read_text()))
R['native']['factory_triangles']=len(selected)
if len(selected)!=4038:R['errors'].append('Unexpected factory stock island size')
expected=[]
for i,mat in enumerate(before['materials']):
    name=before['slot_names'][mat]
    expected.append(after['slot_names'].index('S90_FactoryStock_'+name) if i in selected else after['slot_names'].index(name))
R['native']['only_selected_stock_materials_changed']=expected==after['materials']
if expected!=after['materials']:R['errors'].append('Unexpected native material group changes')
def signature(path):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    q=lambda x:tuple(round(float(v),5) for v in x)
    points=[q(ob.matrix_world@v.co) for v in ob.data.vertices]
    groups={g.index:g.name for g in ob.vertex_groups}
    weights=set((points[v.index],tuple(sorted((groups[g.group],round(g.weight,5)) for g in v.groups))) for v in ob.data.vertices)
    corners=collections.Counter();normal_rows=collections.defaultdict(list)
    for f in ob.data.polygons:
        row=[]
        for li in f.loop_indices:
            row.append((points[ob.data.loops[li].vertex_index],tuple(q(layer.data[li].uv) for layer in ob.data.uv_layers),q(ob.data.corner_normals[li].vector)))
        row.sort(key=lambda x:x[:2]);key=tuple(x[:2] for x in row)
        corners[key]+=1;normal_rows[key].append(tuple(x[2] for x in row))
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    bones={b.name:(b.parent.name if b.parent else '',tuple(q(row) for row in b.matrix_local)) for b in rigs[0].data.bones}
    return weights,corners,bones,normal_rows
a=signature(O/'Inputs/super90.fbx');b=signature(O/'current_native_check.fbx')
for label,x,y in zip(('weights','face_corner_uv','bone_rest_frames'),a,b):
    R['native'][label+'_unchanged']=x==y
    if x!=y:
        R['errors'].append('Native preservation mismatch: '+label)
        if label!='bone_rest_frames':
            print('MISMATCH',label,'counts',len(x),len(y),'before',str(list(x-y)[:2])[:1400],'after',str(list(y-x)[:2])[:1400],flush=True)
if a[1]==b[1]:
    # Separate export float rounding from a real shading change. Compare every
    # corner on its matching triangle; material-section vertex duplication is legal.
    maximum=0.
    for key,rows in a[3].items():
        for row in rows:
            error=min(max(math.dist(x,y) for x,y in zip(row,candidate)) for candidate in b[3][key])
            maximum=max(maximum,error)
    R['native']['normal_max_vector_delta']=maximum
    R['native']['normal_max_angle_degrees']=math.degrees(2*math.asin(min(1.,maximum*.5)))
    # Rebuilding imported skeletal data can quantize stored normals. Record the
    # measured difference rather than claiming bit-for-bit equality; 0.001
    # vector distance bounds this to less than 0.058 degrees.
    R['native']['normals_within_0058_degrees']=maximum<.001
    if maximum>=.001:R['errors'].append('Native normal delta exceeds 0.058 degrees')
for key in json.loads((O/'models.json').read_text())['parts']:
    bpy.ops.wm.open_mainfile(filepath=str(O/(key+'_Editable.blend')))
    row={};R['parts'][key]=row
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or ob.name not in ('StockSocketTransition','S90_ConnectionRod','S90_RodLockRing','Super90_NativeStockNeck'):continue
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        boundary=[e for e in bm.edges if e.is_boundary]
        zero=sum(f.calc_area()<1e-12 for f in bm.faces)
        row[ob.name]={'boundary_edges':len(boundary),'zero_area_faces':zero,'faces':len(bm.faces)}
        # The neck's forward opening is the retained host interface. No new
        # rear cut edge may be left open; solid rod/socket components are closed.
        if ob.name=='Super90_NativeStockNeck':
            rear=[e for e in boundary if all(v.co.y<-.2249 for v in e.verts)]
            row[ob.name]['open_rear_edges']=len(rear)
            if rear:R['errors'].append(key+': open neck rear')
        elif boundary:R['errors'].append(key+': open '+ob.name)
        if zero:R['errors'].append(key+': degenerate '+ob.name)
        bm.free()
R['ok']=not R['errors'];(O/'model_check.json').write_text(json.dumps(R,indent=2))
print('SUPER90_STOCK_MODEL_CHECK',R['ok'],R['errors'],R['native'])
