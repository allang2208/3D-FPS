"""Restore native HK416 assemblies; rigidly register their existing rail clamps.

No generated bridge or fitted bearing. Emitter and native clamp stay rigidly
together; only slot II's remote cable extends longitudinally around the fore-end.
The existing runtime slot transform is compensated in the second asset export.
"""
import bpy,bmesh,json,math,re
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;P=O.parents[2];X=O/'Exports';X.mkdir(exist_ok=True);B=O/'Editable';B.mkdir(exist_ok=True)
source=json.loads((O/'sources.json').read_text());frames=json.loads((O/'frames.json').read_text())
G=Matrix(frames['asset_to_gun']);opposite=Matrix(frames['runtime_opposite_blender']);S=Matrix.Diagonal((1,-1,1,1))
inv=json.loads((P/'SourceAssets/HK416Reworked20260930/source_inventory.json').read_text());objects={e['name']:e for e in inv['objects']}
old=json.loads((O.parent/'FitReview/Repaired/manifest.json').read_text())['HK416-blessed_laser-1']
spec=json.loads((P/'SourceAssets/BlessedLaser20261006/Model/authoring.json').read_text())['HK416']
bpy.context.preferences.filepaths.save_version=0
def clean(n):return re.sub(r'[._]\d{3}$','',n)
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
def load_native(kind):
    bpy.ops.import_scene.fbx(filepath=source[kind]['fbx']);obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for ob in obs:
        t=G@ob.matrix_world;ob.parent=None;ob.data.transform(t);ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
    for ob in list(bpy.context.scene.objects):
        if ob not in obs:bpy.data.objects.remove(ob,do_unlink=True)
    select(obs)
    if len(obs)>1:bpy.ops.object.join()
    return bpy.context.object
def socket_gun(kind):
    return {n:G@S@Vector([p[0]/100,p[1]/100,p[2]/100]) for n,p in source[kind]['sockets'].items()}
def mapping(kind,ob):
    return {m.name:next(e['path'] for e in source[kind]['materials'] if clean(e['path'].split('/')[-1].split('.')[0])==clean(m.name) or clean(e['slot'])==clean(m.name)) for m in ob.data.materials}
right=objects['Side_R_Rail_low']['bounds'];left=objects['Side_L_Rail_low']['bounds'];bottom=objects['Front_down_Rail_low']['bounds']
rail_z=(right['min'][2]+right['max'][2])*2
rail_x=(right['max'][0]+left['min'][0])*2
center=Vector((rail_x,0,rail_z));roll=Matrix.Rotation(math.pi,4,'Y');roll.translation=center-roll.to_3x3()@center
lamp_origin=Vector(((bottom['min'][0]+bottom['max'][0])*2,0,bottom['min'][2]*4))
manifest={}
for kind in ('laser','flashlight','blessed_laser'):
    for side in (1,2):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if kind!='blessed_laser':
            ob=load_native(kind);bindings=mapping(kind,ob);sockets=socket_gun(kind)
            if kind=='laser':
                move=Matrix.Identity(4) if side==1 else roll
                if side==2:
                    # Keep emitter, its original clamp, covers and cable socket
                    # rigidly together. The remote battery stays behind it;
                    # preserve the cable's wrap around the fore-end and extend
                    # its longitudinal route to the advanced assembly.
                    advance=.032;battery_back=-.016;bm=bmesh.new();bm.from_mesh(ob.data);seen=set();classified={}
                    for v in bm.verts:
                        if v in seen:continue
                        seen.add(v);queue=[v];group=[]
                        while queue:
                            p=queue.pop();group.append(p)
                            for edge in p.link_edges:
                                q=edge.other_vert(p)
                                if q not in seen:seen.add(q);queue.append(q)
                        low=min(p.co.x for p in group);high=max(p.co.x for p in group)
                        if low<-.03 and high>.035:
                            classified['cable']=len(group)
                            for p in group:
                                w=max(0.,min(1.,(p.co.x+.025)/.050));w=w*w*(3-2*w);p.co.y+=battery_back+(advance-battery_back)*w
                        elif high<-.015:
                            classified['battery']=classified.get('battery',0)+len(group)
                            for p in group:p.co.y+=battery_back
                        else:
                            for p in group:p.co.y+=advance
                    if not all(k in classified for k in ('cable','battery')):raise RuntimeError('Native cable/battery identity lost')
                    bm.to_mesh(ob.data);bm.free();sockets={n:p+Vector((0,advance,0)) for n,p in sockets.items()}
            else:
                move=Matrix.Rotation(-math.pi/2 if side==1 else math.pi/2,4,'Y')
                crown=Vector((right['max'][0]*4 if side==1 else left['min'][0]*4,0,rail_z))
                move.translation=crown-move.to_3x3()@lamp_origin
            ob.data.transform(move);sockets={n:move@p for n,p in sockets.items()}
            rigid=not(kind=='laser' and side==2);native_clamp='original emitter and clamp retained as one rigid assembly'
        else:
            # Keep the currently installed approved body, dropping only this
            # task's rejected generic bearing. Its keyed block remains intact.
            bpy.ops.wm.open_mainfile(filepath=str(O.parent/'FitReview/Repaired/HK416-blessed_laser-1.blend'))
            ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
            bindings={m.name:old['materials'][m.name] for m in ob.data.materials}
            bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if ob.data.materials[f.material_index].name.startswith('Tactical_Fitted_Bearing')],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
            undo=Vector((0,0,old['body_outward_mm']/1000));ob.data.transform(Matrix.Translation(undo))
            body_tree=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[list(p.vertices) for p in ob.data.polygons])
            hit=body_tree.ray_cast(Vector((-.045*spec['scale'],0,.10)),Vector((0,0,-1)),.20)[0]
            if hit is None:raise RuntimeError('Existing blessed keyed block not found')
            key_top=hit.z
            canonical=Matrix(old['canonical']);sockets={n:canonical@S@Vector([p[0]/100,p[1]/100,p[2]/100])+undo for n,p in source['blessed_laser-1']['sockets'].items()}
            with bpy.data.libraries.load(str(P/'SourceAssets/HK416Reworked20260930/HK416_Original_Editable.blend'),link=False) as (src,dst):dst.objects=['mount_low']
            clamp=dst.objects[0];bpy.context.collection.objects.link(clamp)
            clamp.parent=None;clamp.data.transform(Matrix.Diagonal((4,4,4,1))@Matrix(objects['mount_low']['matrix_world']));clamp.matrix_world=Matrix.Identity(4);clamp.modifiers.clear()
            for layer in list(clamp.data.uv_layers)[1:]:clamp.data.uv_layers.remove(layer)
            layer=clamp.data.uv_layers[0];layer.name=ob.data.uv_layers[0].name
            tile=math.floor(sum(v.uv.x for v in layer.data)/len(layer.data))
            for v in layer.data:v.uv.x-=tile
            mat=bpy.data.materials.new('HK416_Original_Rail_Clamp');clamp.data.materials.clear();clamp.data.materials.append(mat)
            for face in clamp.data.polygons:face.material_index=0
            bindings[mat.name]=source['laser']['materials'][0]['path']
            lo=Vector([min(v.co[i] for v in clamp.data.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in clamp.data.vertices) for i in range(3)])
            seat=(lo+hi)*.5
            # The existing clamp's outer mounting plate receives the existing
            # blessed keyed block directly. No extra geometry is inserted.
            aim=Matrix(((0,0,-1),(1,0,0),(0,-1,0))).to_4x4()
            aim.translation=Vector((hi.x+key_top-.00008,seat.y+.045*spec['scale'],seat.z))
            ob.data.transform(aim);sockets={n:aim@p for n,p in sockets.items()}
            select([ob,clamp]);bpy.ops.object.join()
            if side==2:
                translate=Matrix.Translation((0,.004,0));ob.data.transform(translate@roll);sockets={n:translate@roll@p for n,p in sockets.items()}
            rigid=False;native_clamp='original Laser_sight/mount_low, unchanged shape and source UV'
        key=f'HK416-{kind}-{side}';ob.name=f'SM_{kind}_{side}';select([ob]);bpy.ops.object.material_slot_remove_unused()
        bpy.ops.wm.save_as_mainfile(filepath=str(B/(key+'.blend')))
        export=G.inverted() if side==1 else opposite.inverted()@G.inverted()
        ob.data.transform(export);out_sockets={}
        for label,pos in sockets.items():
            p=export@pos;out_sockets[label]=[p.x*100,-p.y*100,p.z*100]
            sock=bpy.data.objects.new('SOCKET_'+label,None);bpy.context.collection.objects.link(sock);sock.parent=ob;sock.location=p;sock.select_set(True)
        fbx=X/(key+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
        manifest[key]={'family':'HK416','kind':kind,'side':side,'fbx':str(fbx),'source':source[kind]['path'],'materials':{m.name:bindings[m.name] for m in ob.data.materials},'sockets':out_sockets,'native_clamp':native_clamp,'whole_native_assembly_rigid':rigid,'generated_connector_count':0,'rail_center_gun_m':list(center),'runtime_compensation':list(map(list,export))}
(O/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('HK416_NATIVE_RAIL_EXPORTED',len(manifest))
