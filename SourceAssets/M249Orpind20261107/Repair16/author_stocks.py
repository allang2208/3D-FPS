"""Move the existing stock bodies to the factory upper port and author a short neck."""
import bpy,bmesh,json,pickle,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion
r=Path(__file__).resolve().parent;old=r.parent/'Repair13'
plan=json.loads((r/'stock_plan.json').read_text());recipe=json.loads((old/'parts_recipe.json').read_text())
d=pickle.load(open(old/'native.pkl','rb'));v=d['bind'][d['names'].index('WPN_root')]
root=np.eye(4);root[:3,:3]=np.array(Quaternion((v[6],v[3],v[4],v[5])).to_matrix())*v[7:];root[:3,3]=v[:3]
component_to_blender=np.diag([.01,-.01,.01,1.])@np.diag([100,100,100,1.])@np.linalg.inv(root)
shift=component_to_blender[:3,:3]@np.array(plan['body_translation_cm'])
front=np.array(plan['upper_port_ring_cm']);center=np.array(plan['factory_upper_port_cm'])
target=np.array(plan['new_stock_anchor_cm']);count=len(front)
(r/'Exports').mkdir(exist_ok=True);out={}
for key in ('skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock'):
    bpy.ops.wm.open_mainfile(filepath=str(old/'Exports'/('SM_M249_'+key+'.blend')))
    bpy.context.preferences.filepaths.save_version=0
    for o in list(bpy.context.scene.objects):
        if o.type=='MESH' and o.name.startswith('M249_StockCollar'):bpy.data.objects.remove(o,do_unlink=True)
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in obs:o.data.transform(Matrix.Translation(shift.tolist()))
    mat=bpy.data.materials.get('M24913_Interface') or bpy.data.materials.new('M24913_Interface')
    rings=[]
    # The inlet copies the original angled 24-sided tube face and overlaps the
    # receiver by 1.5 mm. The far end forms a rounded neck seated in the stock.
    rings.append(front+np.array([0,-.15,0]))
    rings.append(front+np.array([0,.18,0]))
    for advance,width,height in ((1.4,2.30,2.40),(2.08,2.10,2.24),(2.42,2.10,2.24)):
        row=[]
        for point in front:
            theta=math.atan2(point[2]-center[2],point[0]-center[0])
            c,s=math.cos(theta),math.sin(theta)
            row.append(center+[math.copysign(abs(c)**.5,c)*width*.5,advance,math.copysign(abs(s)**.5,s)*height*.5])
        rings.append(np.array(row))
    coords=np.concatenate(rings);coords=(component_to_blender@np.c_[coords,np.ones(len(coords))].T).T[:,:3]
    faces=[]
    for j in range(len(rings)-1):
        for i in range(count):faces.append((j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i))
    faces.extend([tuple(reversed(range(count))),tuple((len(rings)-1)*count+i for i in range(count))])
    mesh=bpy.data.meshes.new('M249_UpperStockNeck');mesh.from_pydata(coords.tolist(),[],faces);mesh.materials.append(mat);mesh.update()
    neck=bpy.data.objects.new('M249_UpperStockNeck',mesh);bpy.context.collection.objects.link(neck)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    bpy.ops.object.select_all(action='DESELECT');neck.select_set(True);bpy.context.view_layer.objects.active=neck
    bevel=neck.modifiers.new('Machined edges 0.35mm','BEVEL');bevel.width=.00035;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for face in mesh.polygons:face.use_smooth=len(face.vertices)==4
    uv=mesh.uv_layers.new(name='UV0')
    for face in mesh.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(face.normal[a]))]
        for li in face.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/.02,co[axes[1]]/.02)
    obs.append(neck);bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=neck
    name='SM_M249_'+key
    bpy.ops.export_scene.fbx(filepath=str(r/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(r/'Exports'/(name+'.blend')))
    out[key]=dict(fbx=str(r/'Exports'/(name+'.fbx')),extension_cm=plan['extension_cm'],body_translation_cm=plan['body_translation_cm'],materials=recipe['parts'][key]['materials'])
    print('M249_UPPER_STOCK_AUTHORED',key,flush=True)
(r/'stock_exports.json').write_text(json.dumps(out,indent=2))
