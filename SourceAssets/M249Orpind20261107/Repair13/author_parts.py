"""Fit the installed shared parts in native M249 root space, retaining UVs."""
import bpy,bmesh,json,pickle,sys,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
r=Path(__file__).resolve().parent;p=r.parents[2]
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def qr(v):return np.array(Quaternion((v[3],v[0],v[1],v[2])).to_matrix())
def matrix(v):
    a=np.eye(4);a[:3,:3]=qr(v[3:7])*np.array(v[7:]);a[:3,3]=v[:3];return a
def compose(ns,ps,local):
    world={}
    for n in ns:world[n]=world[ps[n]]@local[n] if ps[n] else local[n].copy()
    return world
inputs=json.loads((r/'inputs.json').read_text());d=pickle.load(open(r/'native.pkl','rb'));donor=pickle.load(open(r/'donor.pkl','rb'))
out={'parts':{},'foregrip_transforms':{},'runtime_tested':False};(r/'Exports').mkdir(exist_ok=True)
names=d['names'];parents={n:(names[i] if i>=0 else None) for n,i in zip(names,d['parents'])}
bind={n:matrix(v) for n,v in zip(names,d['bind'])};root=bind['WPN_root'];to_root=np.diag([100,100,100,1])@np.linalg.inv(root)
def hold(data,family=None):
    ns=data['names'];ps={n:(ns[i] if i>=0 else None) for n,i in zip(ns,data['parents'])}
    if family is None:
        clip=next(v for k,v in data['clips'].items() if k.split('.')[0].endswith('_idle'));rows=clip['frames'][0]
    else:rows=data['holds'][family]['local']
    local={n:matrix(v) for n,v in zip(ns,rows)}
    if family:
        for track in data['holds'][family]['tracks']:
            n=track['bone'];v=np.array(track['values']).reshape(-1,10)[0]
            local[n][:3,3]+=v[:3];local[n][:3,:3]=qr(v[3:7])@local[n][:3,:3]
    return compose(ns,ps,local)
th=hold(d);dh=hold(donor,'base')
def in_root(world,n):
    t=np.linalg.inv(world['WPN_root'])@world[n];t[:3,3]*=100;t[:3,:3]=rot(t);return t
rear_transform=in_root(th,'hand_r')@np.linalg.inv(in_root(dh,'hand_r'))
v=np.array(d['vertices']);faces=np.array(d['faces']);sections=np.array(d['sections'])
def points(slot):return v[np.unique(faces[sections==d['slots'].index(slot)])]
stock=points('M249_Factory_Stock');rim=stock[stock[:,1]<stock[:,1].min()+.4];stock_anchor=(rim.min(0)+rim.max(0))*.5
fore=points('M249_Factory_Foregrip');saddle=fore[fore[:,2]>fore[:,2].max()-.7];fore_anchor=(saddle.min(0)+saddle.max(0))*.5;fore_anchor[2]=fore[:,2].max()+.02
muzzle=points('M249_Factory_Muzzle');inlet=muzzle[muzzle[:,1]>muzzle[:,1].max()-.65];muzzle_anchor=(inlet.min(0)+inlet.max(0))*.5;muzzle_anchor[1]=muzzle[:,1].max()-.15
out['interfaces_component_cm']={'stock':stock_anchor.tolist(),'foregrip':fore_anchor.tolist(),'muzzle':muzzle_anchor.tolist()}
forward_basis=np.diag([-1.,-1.,1.]);fore_source=np.array([-.003818143,36.0937039256,3.0852688968])
stock_source=np.array([-.003818143,-6.4062960744,7.1852688968])
def map_frame(basis,target,source):
    a=np.eye(4);a[:3,:3]=basis;a[:3,3]=target-basis@source;return to_root@a
front_xf=map_frame(forward_basis,fore_anchor,fore_source)
stock_xf=map_frame(forward_basis,stock_anchor,stock_source)
out['stock_transform']=stock_xf.tolist();out['rear_transform']=rear_transform.tolist()
flip=np.diag([1.,-1.,1.,1.]);bpy.context.preferences.filepaths.save_version=0
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def block(name,center,scale,material,xf):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material);mod=o.modifiers.new('Interface edge','BEVEL');mod.width=.045;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.transform(Matrix(xf)@o.matrix_world);o.matrix_world=Matrix.Identity(4)
    return o
def bevelled_neck(name,a,b,width,height,mat):
    # A short closed receiver collar. Coordinates are component centimetres.
    direction=np.array(b)-a;length=np.linalg.norm(direction);axis=direction/max(length,1e-9)
    x=np.cross([0,0,1],axis);x/=max(np.linalg.norm(x),1e-9);z=np.cross(axis,x)
    xf=np.eye(4);xf[:3,:3]=np.column_stack((x,axis,z));xf[:3,3]=(np.array(a)+b)*.5
    return block(name,(0,0,0),(width,length,height),mat,to_root@xf)
for key,spec in inputs['parts'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.
    bpy.ops.import_scene.fbx(filepath=spec['fbx'],use_anim=False)
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];bindings={};source_points=[]
    for o in obs:
        # UE exporter -> Blender metres -> UE local centimetres, exactly once.
        o.data.transform(Matrix(np.diag([100.,-100.,100.,1.]))@o.matrix_world);o.matrix_world=Matrix.Identity(4)
        for idx,m in enumerate(o.data.materials):
            matches=[s for s in spec['slots'] if m.name.split('.')[0] in (s['slot'],s['material'].split('.')[-1]) or m.name.startswith(s['material'].split('.')[-1])]
            s=matches[0] if matches else spec['slots'][min(idx,len(spec['slots'])-1)]
            m['source_slot']=s['slot'];m.name='M24913_'+key+'_'+str(idx);bindings[m.name]=s['material']
        # Discard the old host's separately authored mounting blocks only.
        bm=bmesh.new();bm.from_mesh(o.data)
        remove=[f for f in bm.faces if o.data.materials[f.material_index].get('source_slot')=='PKM14_Interface']
        bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(o.data);bm.free()
        source_points.extend([tuple(x.co) for x in o.data.vertices])
    q=np.array(source_points);xf=np.eye(4);sockets={}
    if key in ('vertical','tactical_vertical','canted','prism','angled'):
        xf=front_xf;out['foregrip_transforms'][key]=xf.tolist()
    elif key.endswith('reargrip'):xf=rear_transform
    elif key in ('skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock'):xf=stock_xf
    else:
        basis=np.array([[0,1,0],[-1,0,0],[0,0,1.]]) if key=='multi_caliber_suppressor' else np.eye(3)
        xf=map_frame(basis,muzzle_anchor,np.zeros(3))
        tip=np.array(spec['sockets']['Muzzle']) if 'Muzzle' in spec['sockets'] else np.array([0.,q[:,1].min(),0.])
        axis=np.array([1.,0,0]) if key=='multi_caliber_suppressor' else np.array([0.,-1,0])
        sockets={'Muzzle':(xf@np.r_[tip,1])[:3].tolist(),'AimGuide':(xf@np.r_[tip+axis*5,1])[:3].tolist()}
    for o in obs:o.data.transform(Matrix(xf))
    adapter=bpy.data.materials.new('M24913_Interface');adapter.use_nodes=True;bindings[adapter.name]='M249_INTERFACE'
    if key in ('vertical','tactical_vertical','canted','prism','angled'):
        # The existing top saddle meets the native underside rail. A thin cap
        # closes the interface, without enlarging or changing the grip body.
        a=fore_anchor.copy();a[2]+=.12
        obs.append(block('M249_UndersideSeat',a,(2.14,6.0,.28),adapter,to_root))
    elif key in ('skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock'):
        a=stock_anchor.copy();a[1]-=.3;b=stock_anchor.copy();b[1]+=.65
        obs.append(bevelled_neck('M249_StockCollar',a,b,2.05,2.2,adapter))
    elif key.endswith('reargrip'):
        # Preserve the mapped palm contact, bridging only the top collar to
        # the existing trigger housing. No scale change of the grip body.
        cloud=np.array([tuple(x.co) for o in obs for x in o.data.vertices]);component=(root@np.c_[cloud/100,np.ones(len(cloud))].T).T[:,:3]
        cap=component[component[:,2]>component[:,2].max()-.6];center=(cap.min(0)+cap.max(0))*.5
        center[2]+=.16;obs.append(block('M249_GripCollar',center,(2.7,3.25,.55),adapter,to_root))
    bounds=np.array([tuple(x.co) for o in obs for x in o.data.vertices]);out['parts'][key]=dict(source=spec['source'],transform=xf.tolist(),bounds_root_cm=[bounds.min(0).tolist(),bounds.max(0).tolist()],materials=bindings,sockets=sockets)
    # Native root-centimetres -> FBX metres. Runtime has the established .01
    # compensation against the 100x native bone scale.
    for o in obs:
        o.data.transform(Matrix(np.diag([.01,-.01,.01,1.])))
        if not o.data.uv_layers:o.data.uv_layers.new(name='UV0')
        if o.name.startswith('M249_'):
            uv=o.data.uv_layers[0]
            for face in o.data.polygons:
                axes=[i for i in range(3) if i!=max(range(3),key=lambda a:abs(face.normal[a]))]
                for li in face.loop_indices:
                    co=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/.03,co[axes[1]]/.03)
    select(obs);name='SM_M249_'+key
    bpy.ops.export_scene.fbx(filepath=str(r/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(r/'Exports'/(name+'.blend')))
    print('M249_FITTED_PART',key,flush=True)
(r/'parts_recipe.json').write_text(json.dumps(out,indent=2))
