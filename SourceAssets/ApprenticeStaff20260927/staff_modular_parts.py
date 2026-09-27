"""Precision finishing for the Meshy staff. All coordinates are centimetres.

The master surface supplies every mating profile. This module authors geometry;
it does not render, run audits, launch the game, or alter the source master.
"""
import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TAU=math.tau

def build_modifications(master, factory_grip, grip_z=32.0):
    tree=BVHTree.FromPolygons([v.co.copy() for v in master.data.vertices],
                             [list(p.vertices) for p in master.data.polygons])
    materials={}
    colors={'ice':(.12,.6,.9,1),'fire':(.8,.14,.025,1),
            'light':(.16,.62,.3,1),'electric':(.38,.18,.9,1),
            'metal':(.21,.23,.25,1),'PineV2':(.40,.24,.09,1),
            'SandalV2':(.23,.075,.035,1),'RuneV2':(.68,.34,.08,1)}
    for key,color in colors.items():
        mat=bpy.data.materials.new('M_Staff_'+key);mat.diffuse_color=color;mat.use_nodes=True
        bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        bs.inputs['Base Color'].default_value=color
        bs.inputs['Roughness'].default_value=.4 if key in ('metal','ice','electric','RuneV2') else .58
        bs.inputs['Metallic'].default_value=.7 if key in ('metal','RuneV2') else 0
        if key in ('ice','fire','light','electric','RuneV2'):
            bs.inputs['Emission Color'].default_value=color
            bs.inputs['Emission Strength'].default_value=.15 if key=='RuneV2' else .35
        if key in ('PineV2','SandalV2'):
            # Keep the Meshy UV layout and grain; only wood species tint changes.
            original=master.data.materials[0]
            nodes=original.node_tree.nodes
            original_bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
            if original_bs.inputs['Base Color'].is_linked:
                source_node=original_bs.inputs['Base Color'].links[0].from_node
                if source_node.type=='TEX_IMAGE':
                    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=source_node.image
                    mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
                    mix.inputs[2].default_value=(.83,.62,.38,1) if key=='PineV2' else (.44,.17,.10,1)
                    mat.node_tree.links.new(tex.outputs['Color'],mix.inputs[1]);mat.node_tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
        materials[key]=mat

    output=[];parts=[]
    def surface(angle,z,offset=0):
        direction=Vector((math.cos(angle),math.sin(angle),0))
        point,normal,index,distance=tree.ray_cast(direction*25+Vector((0,0,z)),-direction,30)
        if point is None:raise RuntimeError('Cannot author interface outside Meshy surface at z='+str(z))
        return point+direction*offset

    def mesh(name,vertices,faces,mat,smooth=True):
        data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        data.materials.append(materials[mat])
        for p in data.polygons:p.use_smooth=smooth
        # Every authored face gets a usable UV channel. Wood grip keeps original UVs.
        uv=data.uv_layers.new(name='UVMap')
        for poly in data.polygons:
            angles=[math.atan2(data.vertices[data.loops[i].vertex_index].co.y,data.vertices[data.loops[i].vertex_index].co.x)/TAU for i in poly.loop_indices]
            wrap=max(angles)-min(angles)>.5
            for i,a in zip(poly.loop_indices,angles):
                co=data.vertices[data.loops[i].vertex_index].co
                uv.data[i].uv=((a+1 if wrap and a<0 else a),co.z/20)
        obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);parts.append(obj);return obj

    def loft(name,rings,mat,cap=True,smooth=True):
        count=len(rings[0]);vertices=[p for row in rings for p in row];faces=[]
        for j in range(len(rings)-1):
            for i in range(count):faces.append((j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i))
        if cap:faces.extend([tuple(reversed(range(count))),tuple((len(rings)-1)*count+i for i in range(count))])
        return mesh(name,vertices,faces,mat,smooth)

    def profile(name,zr,mat,n=32,xy=(0,0),phase=0,smooth=True):
        return loft(name,[[Vector((xy[0]+r*math.cos(i*TAU/n+phase),xy[1]+r*math.sin(i*TAU/n+phase),z)) for i in range(n)] for z,r in zr],mat,smooth=smooth)

    def surface_band(name,z0,z1,mat,thickness=.16,n=64):
        # Closed shaped band with a small intentional embed at the real host surface.
        levels=[(z0,-.025),(z0,.025),(z0+.10,thickness),(z1-.10,thickness),(z1,.025),(z1,-.025)]
        rings=[[surface(i*TAU/n,z,offset) for i in range(n)] for z,offset in levels]
        rings.append(rings[0]);return loft(name,rings,mat,cap=False)

    def densify(points,step):
        result=[]
        for a,b in zip(points,points[1:]):
            a,b=Vector(a),Vector(b);count=max(1,math.ceil((b-a).length/step))
            result.extend(a.lerp(b,i/count) for i in range(count))
        result.append(Vector(points[-1]));return result

    def tube(name,points,radius,mat,sides=8,taper=None):
        points=[Vector(p) for p in points];rings=[]
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
            normal=tangent.cross(Vector((0,1,0)))
            if normal.length<.01:normal=tangent.cross(Vector((1,0,0)))
            normal.normalize();other=tangent.cross(normal).normalized()
            r=radius*(taper[i] if taper else 1)
            rings.append([p+r*(math.cos(k*TAU/sides)*normal+math.sin(k*TAU/sides)*other) for k in range(sides)])
        return loft(name,rings,mat)

    def ribbon(name,path,angle,mat='RuneV2',width=.16,raise_cm=.10):
        # The actual triangle intersection is sampled for both edges at each path
        # station: neither a tangent plane nor a nominal cylinder can sink the mark.
        points=densify(path,.22);vertices=[]
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
            side=Vector((-tangent.y,tangent.x))*width*.5
            for height in (-.022,raise_cm):
                for q in (p-side,p+side):
                    radius=surface(angle,q.y).xy.length
                    vertices.append(surface(angle+q.x/radius,q.y,height))
        faces=[]
        for i in range(len(points)-1):
            a,b=4*i,4*(i+1)
            faces.extend([(a+2,b+2,b+3,a+3),(a,b,b+2,a+2),(a+1,a+3,b+3,b+1),(a,a+1,b+1,b)])
        faces.extend([(0,2,3,1),(len(vertices)-4,len(vertices)-3,len(vertices)-1,len(vertices)-2)])
        return mesh(name,vertices,faces,mat)

    def finish(slot,key):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in parts:obj.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        if len(parts)>1:bpy.ops.object.join()
        obj=bpy.context.object;bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        obj.name='SM_Staff_'+slot+'_'+key;output.append(obj);parts.clear();return obj

    # Every head copies the SAME real lower neck. Its cap is above the crown mount.
    # New collars start slightly inside the preserved body, eliminating an open seam.
    for key,element in [('frozen_crystal','ice'),('magma_core','fire'),('jade_spirit_crystal','light'),('storm_core','electric')]:
        neck=master.copy();neck.data=master.data.copy();bpy.context.collection.objects.link(neck)
        bm=bmesh.new();bm.from_mesh(neck.data)
        for z,normal in [(61.92,(0,0,1)),(64.65,(0,0,-1))]:
            cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,z),plane_no=normal,clear_inner=True,clear_outer=False)
            edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
            if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
        bm.to_mesh(neck.data);bm.free();neck.data.materials.clear();neck.data.materials.append(materials['metal'])
        for p in neck.data.polygons:p.material_index=0
        parts.append(neck)
        profile('gem_seat',[(64.42,3.55),(64.62,3.70),(65.12,3.70),(65.30,3.45)],'metal',48)
        if element=='ice':
            profile('single_hex_crystal',[(64.95,2.7),(66.2,4.1),(67.3,4.45),(74.8,3.5),(79.0,.02)],element,6,phase=math.pi/6,smooth=False)
        elif element=='light':
            profile('jade_cut',[(64.95,2.6),(66.6,3.8),(70.8,4.55),(75.8,3.5),(78.7,.5)],element,10,phase=math.pi/10,smooth=False)
        else:
            radius=5.5 if element=='fire' else 5.65
            zr=[(71+radius*math.cos(math.pi-i*math.pi/10),max(.02,radius*math.sin(i*math.pi/10))) for i in range(11)]
            zr[0]=(64.95,2.6)
            profile('faceted_core',zr,element,16,phase=math.pi/16,smooth=False)
        finish('head_crystal',key)

    # A shared clear envelope lets all four crowns surround all five heads while
    # the lower band seats directly on the common neck instead of floating.
    envelopes=[tree]+[BVHTree.FromPolygons([v.co.copy() for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons]) for o in output]
    def crown_point(a,z):
        n=Vector((math.cos(a),math.sin(a),0));r=0
        for envelope in envelopes:
            p,normal,index,distance=envelope.ray_cast(n*25+Vector((0,0,z)),-n,30)
            if p is not None:r=max(r,p.xy.length)
        return n*(r+.32)+Vector((0,0,z))
    for key,element in [('spike_crown','ice'),('current_crown','electric'),('wreath_crown','light'),('heat_crown','fire')]:
        surface_band('crown_seated_band',62.55,64.25,'metal',.19)
        surface_band('crown_element_inlay',63.05,63.70,element,.215)
        for i in range(8):
            a=i*TAU/8;start=surface(a,64.04,.12)
            points=[start]+[crown_point(a,z) for z in [64.5,65,65.5,66,66.5,67]]
            tube('crown_support',points,.14,'metal',8)
            if element=='light':
                p=points[-2]
                # Leaf base grows out of the stem; there are no disconnected beads.
                tip=crown_point(a,68.0);mid=p.lerp(tip,.52)
                tangent=Vector((-math.sin(a),math.cos(a),0));normal=Vector((math.cos(a),math.sin(a),0))
                v=[p,mid-tangent*.66,tip,mid+tangent*.66,mid+normal*.32,mid-normal*.12]
                faces=[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)]
                mesh('rooted_leaf',v,faces,element,False)
            elif element=='electric':
                path=[points[-3],crown_point(a-.065,67.15),crown_point(a+.065,67.45),crown_point(a,68.15)]
                tube('lightning_prong',path,.20,element,6,taper=[1,1,1,.08])
            elif element=='fire':
                path=[points[-3],crown_point(a-.07,67.2),crown_point(a+.06,68.0),crown_point(a,68.8)]
                tube('flame_prong',path,.33,element,8,taper=[.75,1,.65,.04])
            else:
                tube('ice_spike',[points[-3],points[-1],crown_point(a,68.2+(i%2)*.6)],.30,element,6,taper=[1,.85,.035])
        finish('crown',key)

    for key in ('eagle_eye_rune','crit_rune','storm_rune'):
        for face in range(4):
            a=face*TAU/4
            for z in [46,52.5,59]:
                if key=='eagle_eye_rune':
                    paths=[[(-1.2,z),(0,z+1),(1.2,z),(0,z-1),(-1.2,z)],[(0,z-.52),(0,z+.52)],
                           [(-.65,z+1.6),(0,z+2.05),(.65,z+1.6)]]
                elif key=='crit_rune':
                    paths=[[(-1.05,z-1.5),(1.05,z+1.5)],[(-1.05,z+1.5),(1.05,z-1.5)],
                           [(-.6,z+1.6),(0,z+2.25),(.6,z+1.6)], [(-.6,z-1.6),(0,z-2.25),(.6,z-1.6)]]
                else:
                    paths=[[(.60,z+2.25),(-.8,z+.25),(.65,z+.25),(-.6,z-2.25)],
                           [(-1.15,z+1.8),(-1.15,z+1.0)],[(1.15,z-1.8),(1.15,z-1.0)]]
                for path in paths:ribbon('surface_rune',path,a,width=.16,raise_cm=.105)
        finish('shaft_rune',key)

    for key,mat in [('alloy_grip','metal'),('pine_grip','PineV2'),('sandalwood_grip','SandalV2')]:
        grip=factory_grip.copy();grip.data=factory_grip.data.copy();bpy.context.collection.objects.link(grip)
        grip.data.materials.clear();grip.data.materials.append(materials[mat])
        for p in grip.data.polygons:p.material_index=0
        parts.append(grip)
        # Exact original cut rings, normals, UVs and grip thickness remain intact.
        if key=='alloy_grip':
            for offset in (-7,-3.5,0,3.5,7):surface_band('flush_grip_ring',grip_z+offset-.15,grip_z+offset+.15,'metal',.045)
        finish('grip_lining',key)

    for key,element in [('ice_soul_pendant','ice'),('thunder_bell','electric'),('purification_vine','light'),('flame_pendant','fire')]:
        surface_band('tail_clamp',-64.45,-63.55,'metal',.14)
        start=surface(0,-64,.065)
        # A continuous metal link joins the clamp to the cap of every pendant.
        points=[start,Vector((3.35,0,-64.6)),Vector((4.1,0,-65.8)),Vector((5.2,0,-69.0)),Vector((5.2,0,-72.8))]
        tube('tail_suspension',points,.135,'metal',10)
        profile('pendant_cap',[(-73.1,.52),(-72.75,.60),(-72.5,.35)],'metal',20,(5.2,0))
        if key=='thunder_bell':
            # A real hollow bell, with a visible rim and connected clapper stem.
            zr=[(-72.95,.48),(-73.4,.75),(-75.5,1.6),(-75.75,1.65),(-75.85,1.46),(-75.55,1.39),(-73.45,.54),(-73.18,.30)]
            rings=[[Vector((5.2+r*math.cos(i*TAU/32),r*math.sin(i*TAU/32),z)) for i in range(32)] for z,r in zr]
            rings.append(rings[0]);loft('hollow_thunder_bell',rings,element,cap=False)
            tube('bell_clapper_stem',[(5.2,0,-73),(5.2,0,-76)],.12,'metal')
            profile('bell_clapper',[(-76.4,.05),(-76.2,.32),(-75.8,.32),(-75.6,.05)],'metal',12,(5.2,0))
        elif element=='ice':
            profile('ice_pendant',[(-72.95,.48),(-73.8,1.03),(-76.3,.85),(-77.4,.035)],element,6,(5.2,0),smooth=False)
        elif element=='light':
            p=Vector((5.2,0,-72.95));m=Vector((5.2,0,-75));end=Vector((5.2,0,-77.1))
            mesh('vine_leaf',[p,m+Vector((1.15,0,0)),end,m+Vector((-1.15,0,0)),m+Vector((0,.4,0)),m-Vector((0,.4,0))],
                 [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],element,False)
            tube('leaf_vein',[(5.2,-.02,-72.9),(5.2,-.43,-75),(5.2,-.015,-77)],.065,'metal',6)
        else:
            profile('flame_drop',[(-72.95,.48),(-73.6,.65),(-74.8,1.05),(-75.8,.85),(-77,.025)],element,10,(5.2,0),smooth=False)
        finish('tail_charm',key)

    # Reserve diagonal lanes between the four rune faces so the two slots do not
    # obscure each other. Continuous ribbons replace many overlapping cylinders.
    for key in ('chain_mana','direct_mana'):
        for angle in (math.pi/4,5*math.pi/4):
            if key=='chain_mana':
                for side in (-1,1):
                    path=[(side*.38*math.sin((z-14)*math.pi/2),z) for z in [14+i*.5 for i in range(89)]]
                    ribbon('connected_chain_trace',path,angle,width=.13,raise_cm=.10)
            else:
                for s in (-.17,.17):ribbon('straight_trace',[(s,14),(s,58)],angle,width=.115,raise_cm=.09)
                for z in (14,58):ribbon('trace_termination',[(-.22,z),(.22,z)],angle,width=.16,raise_cm=.095)
        finish('mana_line',key)
    return output
