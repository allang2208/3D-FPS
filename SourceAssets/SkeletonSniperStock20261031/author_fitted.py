"""Fit the selected exterior mesh to three existing game-asset interfaces."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;H=json.loads((O/'Inputs/hosts.json').read_text())
bpy.context.preferences.filepaths.save_version=0
report={'source':'Original/Meshy_AI_Adjustable_Tactical_R_1031040412_texture.glb','models':{},'animations_changed':False}

def loop_edges(edges):
    edges=list(edges);result=[]
    while edges:
        a,b=edges.pop();loop=[a,b]
        while loop[-1]!=loop[0]:
            k=next((i for i,e in enumerate(edges) if loop[-1] in e),None)
            if k is None:break
            e=edges.pop(k);loop.append(e[1] if e[0]==loop[-1] else e[0])
        if loop[-1]==loop[0] and len(loop)>3:result.append(loop[:-1])
    return result

def make_mesh(name,verts,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material)
    uv=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        ax=sorted(range(3),key=lambda a:abs(f.normal[a]))[:2]
        for i in f.loop_indices:
            p=me.vertices[me.loops[i].vertex_index].co;uv.data[i].uv=(p[ax[0]]*20,p[ax[1]]*20)
    return ob

for key in ('M24','SVD','SVCH'):
    bpy.ops.wm.open_mainfile(filepath=str(O/'SkeletonSniperStock_Meshy_Master.blend'),load_ui=False,use_scripts=False)
    ob=bpy.data.objects['SkeletonSniperStock_Meshy_Master'];ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
    ob.name='SniperSkeleton_'+key
    ob.data.materials[0].name='SniperStock_MeshySurface'
    pts=np.array([list(v.co) for v in ob.data.vertices]);xmin,xmax=pts[:,0].min(),pts[:,0].max()
    frontband=pts[pts[:,0]<xmin+.025];rearband=pts[pts[:,0]>xmax-.04]
    front_src=Vector((xmin,0,(frontband[:,2].min()+frontband[:,2].max())*.5))
    rear_src=Vector((xmax,0,(rearband[:,2].min()+rearband[:,2].max())*.5))
    stock_data=None;interface=[];parts=[ob]
    if key=='M24':
        native=np.load(O/'Inputs/M24_M24_base.npz',allow_pickle=True);v=native['vertices'];fs=native['faces']
        selected={i for i,f in enumerate(fs) if v[list(map(int,f)),1].min()<-.11801}
        faces_centers=[(v[list(map(int,fs[i]))].mean(0)*[100,-100,100]).tolist() for i in sorted(selected)]
        (O/'Inputs/m24_factory_stock_faces.json').write_text(json.dumps(faces_centers))
        edge_faces={}
        for i,f in enumerate(fs):
            for a,b in zip(f,np.roll(f,-1)):
                e=tuple(sorted((tuple(np.round(v[int(a)],6)),tuple(np.round(v[int(b)],6)))))
                edge_faces.setdefault(e,[]).append(i in selected)
        interface=loop_edges([e for e,side in edge_faces.items() if any(side) and not all(side)])
        rear=v[v[:,1]<v[:,1].min()+.015]
        front=Vector((0,-.125,.039));back=Vector((0,v[:,1].min(),(rear[:,2].min()+rear[:,2].max())*.5))
        to_export=Matrix.Identity(4)
        report['m24_removed_faces']=len(selected)
    elif key=='SVD':
        native=np.load(O/'Inputs/SVD_SM_SVD_FactoryStock.npz',allow_pickle=True);v=native['root_vertices']
        q=v[np.abs(v[:,1]+.35*v[:,2]-.112)<.00001]
        points=list({tuple(np.round(p,7)) for p in q})
        center=np.mean(points,0);points.sort(key=lambda p:math.atan2(p[2]-center[2],p[0]-center[0]))
        interface=[points]
        rear=v[v[:,1]>v[:,1].max()-.015]
        front=Vector((0,.131,.026));back=Vector((0,v[:,1].max(),(rear[:,2].min()+rear[:,2].max())*.5))
        to_export=Matrix.Identity(4)
    else:
        native=np.load(O/'Inputs/SVCH_SVCH_New_stock.npz',allow_pickle=True);v=native['vertices'];fs=native['faces']
        front_y=v[:,1].max()-.006
        rear=v[v[:,1]<v[:,1].min()+.015]
        xc=(rear[:,0].min()+rear[:,0].max())*.5
        front_q=v[v[:,1]>front_y];zc=(front_q[:,2].min()+front_q[:,2].max())*.5
        # A short transition follows the actual original stock's front outline.
        q=front_q[np.abs(front_q[:,1]-front_q[:,1].max())<.0015]
        center=q.mean(0);points=list({tuple(np.round(p,7)) for p in q})
        points.sort(key=lambda p:math.atan2(p[2]-center[2],p[0]-center[0]));interface=[points]
        front=Vector((xc,front_y-.004,zc));back=Vector((xc,v[:,1].min(),(rear[:,2].min()+rear[:,2].max())*.5))
        to_export=Matrix(H[key]['root_world']).inverted()
    source_direction=(rear_src-front_src).normalized();target_direction=(back-front).normalized()
    source_side=Vector((0,1,0));source_up=source_direction.cross(source_side).normalized()
    target_side=Vector((0,0,1)).cross(target_direction).normalized();target_up=target_direction.cross(target_side).normalized()
    src=Matrix((source_direction,source_side,source_up)).transposed();dst=Matrix((target_direction,target_side,target_up)).transposed()
    rot=dst@src.transposed();scale=(back-front).length/(rear_src-front_src).length
    transform=Matrix.Translation(front)@rot.to_4x4()@Matrix.Scale(scale,4)@Matrix.Translation(-front_src)
    ob.data.transform(transform)
    adapter_mat=bpy.data.materials.new('SniperStock_Interface');adapter_mat.use_nodes=True
    bs=next(n for n in adapter_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.026,.029,.031,1);bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.36
    # Preserve the host boundary exactly. The second ring joins the selected
    # Meshy nose behind its closed end, without scaling the host grip surface.
    radius_side=max(abs(frontband[:,1].min()),abs(frontband[:,1].max()))*scale
    radius_up=(frontband[:,2].max()-frontband[:,2].min())*.5*scale
    for i,ring in enumerate(interface):
        if len(ring)<3:continue
        c=sum((Vector(p) for p in ring),Vector())/len(ring)
        end=[]
        for p in ring:
            q=Vector(p)-c;a=math.atan2(q.dot(target_up),q.dot(target_side))
            end.append(front+target_direction*.001+target_side*(math.cos(a)*radius_side)+target_up*(math.sin(a)*radius_up))
        n=len(ring);verts=list(ring)+[tuple(p) for p in end]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        adapter=make_mesh('SniperStock_'+key+'_Interface'+str(i),verts,faces,adapter_mat)
        bm=bmesh.new();bm.from_mesh(adapter.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(adapter.data);bm.free()
        parts.append(adapter)
    if not interface:raise RuntimeError('No host interface for '+key)
    for p in parts:p.data.transform(to_export)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=ob
    bpy.ops.wm.save_as_mainfile(filepath=str(O/('SkeletonSniperStock_'+key+'_Editable.blend')))
    f=O/'Exports'/('SM_SniperSkeleton_'+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='OFF',use_tspace=True)
    report['models'][key]=dict(file=str(f),objects=[p.name for p in parts],source_to_host=list(map(list,transform)),export_conversion=list(map(list,to_export)),front_anchor=list(front),rear_contact=list(back),uniform_scale=scale,interface_loops=len(interface),source_triangles=len(ob.data.polygons),export_frame='M24 native metres' if key=='M24' else 'Blender WPN_root metres')
    print('SNIPER_STOCK_FITTED',key,len(interface),flush=True)
(O/'authoring.json').write_text(json.dumps(report,indent=2))
