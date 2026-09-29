"""Produce both articulated gauntlets, baked steel, matching icon and pickup.

Background Blender production. No gameplay launch or acceptance renders.
"""
import copy
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_metal_gauntlet_sample as s
import build_tailored_fingerless_candidate as leather
from original_leather_gloves import PROJECT as P, read, write
from glove_icon_display import posed_surface
import steel_gauntlet_finish as finish
import steel_gauntlet_coverage as coverage
import steel_gauntlet_mail as mail
import steel_gauntlet_motion_fit as motion_fit
import steel_gauntlet_smooth_transition as transition
import steel_gauntlet_metal_liner as metal_liner

R = P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
T = R/'Textures'
DIGITS = ('index', 'middle', 'ring', 'pinky', 'thumb')
GRIP_CLOUDS = None


def unit(v): return s.unit(v)


def matrix(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m


def deform_liner(d,bones):
    ps=np.asarray(d['positions']);out=np.zeros_like(ps)
    for name in {b for ws in d['weights'] for b in ws}:
        ids=np.asarray([i for i,w in enumerate(d['weights']) if name in w])
        ws=np.asarray([d['weights'][i][name] for i in ids])
        tr=matrix(bones[name])@np.linalg.inv(matrix(d['bones'][name]))
        out[ids]+=(ps[ids]@tr[:3,:3].T+tr[:3,3])*ws[:,None]
    return out


def select_side(d, side):
    own = {i for i,w in enumerate(d['weights']) if sum(v for n,v in w.items() if n.endswith('_'+side)) > .5}
    return [f for f in d['triangles'] if all(v in own for v in f)]


def smooth_grid(grid, cycles=2):
    """Fair interior steel surfaces, retaining designed perimeter and seams."""
    g = np.asarray(grid)
    for _ in range(cycles):
        h = g.copy()
        h[1:-1,1:-1] = g[1:-1,1:-1]*.60 + .10*(g[:-2,1:-1]+g[2:,1:-1]+g[1:-1,:-2]+g[1:-1,2:])
        g = h
    return g


def plate(name, grid, dorsal, bone, rig, mat):
    grid = smooth_grid(grid)
    obj = s.surface_object(name, grid, dorsal, bone, rig, mat)
    return grid, obj


def grip_trees(d,bone,faces):
    """Native liner in the owner's frame: rest plus the reported pistol grip."""
    global GRIP_CLOUDS
    if GRIP_CLOUDS is None:
        source=read(R/'Sources/DW715.json')
        poses=read(R/'GripFix/DW715_poses.json')
        GRIP_CLOUDS=[(deform_liner(source,p['bones']),p['bones']) for p in poses.values()]
    clouds=[np.asarray(d['positions'])]
    for positions,bones in GRIP_CLOUDS:
        transform=matrix(d['bones'][bone])@np.linalg.inv(matrix(bones[bone]))
        clouds.append(positions@transform[:3,:3].T+transform[:3,3])
    return [BVHTree.FromPolygons(p.tolist(),faces,all_triangles=True) for p in clouds]


def smooth_roof(grid,origin,across,forward,dorsal,extra=.10):
    """A smooth forged surface enclosing the sampled leather, not its folds."""
    g=np.asarray(grid);q=g.reshape((-1,3))-origin
    x=q@across;y=q@forward;z=q@dorsal
    def terms(x,y):return np.array([np.ones_like(x),x,y,x*x,x*y,y*y]).T
    basis=terms(x,y);fit=np.linalg.lstsq(basis,z,rcond=None)[0]
    height=basis@fit;lift=float(np.max(z-height))+extra
    print('STEEL_ROOF_LIFT_CM',round(lift,3),flush=True)
    return (q+dorsal[None,:]*(height+lift-z)[:,None]+origin).reshape(g.shape)


def roof_hit(trees,center,dorsal,reach=12.):
    hits=[]
    for tree in trees:
        hit,_,_,_=tree.ray_cast(Vector(center+dorsal*reach),Vector(-dorsal),reach*2)
        if hit is not None:hits.append(np.asarray(hit))
    if not hits:raise RuntimeError('No liner under steel roof '+str(center))
    return max(hits,key=lambda p:float((p-center)@dorsal))


def handback_grid(d,tree,faces,wrist,x,f,z,roots,side):
    """Fit the main plate to the actual dorsal palm, including both side edges.

    Knuckle centres describe the front edge, not the width of the palm. The old
    average-width trapezoid exposed over a third of the dorsal palm samples.
    """
    core=np.asarray([sum(v for b,v in ws.items() if b.startswith('hand_') or 'metacarpal_' in b) for ws in d['weights']])
    core_faces=[face for face in faces if core[face].mean()>.45]
    envelopes=grip_trees(d,'hand_'+side,core_faces)
    ys=[];bounds=[]
    for py in np.arange(-.45,10.16,.10):
        row=[]
        for px in np.arange(-6.25,6.26,.08):
            origin=wrist+x*px+f*py+z*12
            hit,normal,fi,_=tree.ray_cast(Vector(origin),Vector(-z),24.)
            if hit is not None and core[faces[fi]].mean()>=.55 and abs(np.asarray(normal)@z)>=.20:
                row.append(float(px))
        if row:
            ys.append(float(py));bounds.append([min(row),max(row)])
    ys=np.asarray(ys);bounds=np.asarray(bounds)
    # Fair the sampled outline while retaining a small protective rim beyond
    # the core-palm weight transition. The thumb web is outside this region.
    for _ in range(2):
        bounds[1:-1]=bounds[1:-1]*.5+(bounds[:-2]+bounds[2:])*.25
    bounds[:,0]-=.06;bounds[:,1]+=.06
    order=np.argsort(roots@x);rx=(roots@x)[order];ry=(roots@f)[order]
    def dorsal_surface(px,py):
        center=wrist+x*px+f*py
        # The protective rim extends slightly past the liner silhouette. Carry
        # the adjacent dorsal height across that rim instead of shrinking it.
        offsets=[(0.,0.)]
        for step in (.08,.16,.24,.32,.40):
            offsets.extend(((-step,0.),(step,0.),(0.,-step)))
        for dx,dy in offsets:
            hits=[]
            for surface in envelopes:
                hit,_,_,_=surface.ray_cast(Vector(center+x*dx+f*dy+z*12),Vector(-z),24.)
                if hit is not None:hits.append(float((np.asarray(hit)-center)@z))
            if hits:return center+z*max(hits)
        raise RuntimeError(f'Hand-back outline outside dorsal surface: {px}, {py}')
    grid=[]
    for v in np.linspace(0,1,17):
        row=[]
        for u in np.linspace(0,1,21):
            px=float(bounds[len(bounds)//2,0]*(1-u)+bounds[len(bounds)//2,1]*u)
            for _ in range(4):
                front=float(np.interp(px,rx,ry))-.20
                py=.10+(front-.10)*v
                lo=float(np.interp(py,ys,bounds[:,0]));hi=float(np.interp(py,ys,bounds[:,1]))
                px=lo*(1-u)+hi*u
            top=dorsal_surface(px,py)
            # Keep the rear edge of the unified shell clear of the wrist liner.
            clearance=.25+.15*math.exp(-(v/.16)**2)
            keel=.075*math.exp(-((u-.5)/.14)**2)*math.sin(math.pi*v)
            row.append(top+z*(clearance+keel))
        grid.append(row)
    return smooth_roof(grid,wrist,x,f,z,.12)


def hand(d, anatomy, side, rig, mat):
    a = anatomy[side]; bones = d['bones']
    z = unit(a['dorsal']); wrist = np.asarray(bones['hand_'+side]['position'])
    f = np.asarray(bones['middle_01_'+side]['position'])-wrist
    f = unit(f-z*np.dot(f,z)); x = unit(np.cross(f,z))
    if np.dot(x,np.asarray(bones['thumb_01_'+side]['position'])-wrist)<0: x=-x
    hand_faces=select_side(d,side)
    tree = BVHTree.FromPolygons([Vector(p) for p in d['positions']],hand_faces,all_triangles=True)
    roots = np.asarray([bones[k+'_01_'+side]['position'] for k in DIGITS[:-1]])-wrist
    grid=handback_grid(d,tree,hand_faces,wrist,x,f,z,roots,side)
    transition.build(d,a,side,rig,mat,grid,tree,wrist,x,f,z)
    for digit in DIGITS[:-1]:
        own={i for i,w in enumerate(d['weights']) if sum(v for n,v in w.items() if n.startswith(digit+'_') and n.endswith('_'+side))>.25}
        # Include the transition triangles at the finger root: their other
        # corners can carry metacarpal/neighbor weights across the web seam.
        faces=[f for f in d['triangles'] if any(i in own for i in f)]
        # Existing index/middle/ring/pinky fit remains isolated per phalanx.
        # The thumb is now part of the continuous dorsal shell above.
        for segment in (1,2,3):
            section=next(q for q in a['digits'] if q['bone']==f'{digit}_{segment:02d}_{side}')
            bone=section['bone']; head=np.asarray(bones[bone]['position'])
            axis,dorsal,cross=(unit(section[k]) for k in ('axis','dorsal','across'))
            envelopes=motion_fit.section_trees(d,bone)
            neighbor=np.asarray(bones[('ring' if digit=='pinky' else 'pinky')+'_01_'+side]['position'])-head
            outer=-neighbor if digit=='pinky' else neighbor if digit=='ring' else x
            grid,fit=coverage.finger_shell(section,head,envelopes,terminal=segment==3,
                                           thumb_base=digit=='thumb' and segment==1,outward=outer)
            name=f'Plate_{digit.title()}_{segment:02d}_{side}'
            grid=finish.plate(name,grid,dorsal,bone,rig,mat,'shell')
            if segment==1:
                for i,u in enumerate((.22,.78)):
                    finish.rivet(name.replace('Plate','Rivet')+f'_{i}',grid,u,.20,dorsal,bone,rig,mat,radius=.10)
    mail.build(d,anatomy,side,rig,mat)


def authored_steel():
    return finish.material()


def bake_steel(mat,color,orm,bs,out):
    objects=[p['object'] for p in s.PARTS]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.2,island_margin=.002,area_weight=.2)
    bpy.ops.uv.pack_islands(rotate=True,margin=.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=False
    scene.render.bake.margin=8;scene.render.bake.use_selected_to_active=False
    maps={};nt=mat.node_tree
    for label,kind,source,space in [('BaseColor','EMIT',color,'sRGB'),('ORM','EMIT',orm,'Non-Color'),('Normal','NORMAL',None,'Non-Color')]:
        image=bpy.data.images.new('T_SteelGauntlet_'+label,width=2048,height=2048,alpha=False)
        image.colorspace_settings.name=space
        node=nt.nodes.new('ShaderNodeTexImage');node.image=image;nt.nodes.active=node
        if source is not None:
            emit=nt.nodes.new('ShaderNodeEmission');nt.links.new(source,emit.inputs[0]);nt.links.new(emit.outputs[0],out.inputs[0])
        else: nt.links.new(bs.outputs[0],out.inputs[0])
        print('STEEL_GAUNTLET_BAKE_BEGIN',label,flush=True)
        bpy.ops.object.bake(type=kind,normal_space='TANGENT',uv_layer='SteelSampleUV')
        image.filepath_raw=str(T/(image.name+'.png'));image.file_format='PNG';image.save();maps[label]=image
    nt.links.new(bs.outputs[0],out.inputs[0])
    baked=bpy.data.materials.new('SteelGauntlet_Baked');baked.use_nodes=True
    n=baked.node_tree.nodes;l=baked.node_tree.links;bs=n.get('Principled BSDF')
    for label,image in maps.items():
        tex=n.new('ShaderNodeTexImage');tex.image=image
        if label=='BaseColor':l.new(tex.outputs[0],bs.inputs['Base Color'])
        elif label=='Normal':
            nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
        else:
            sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs[0],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    for obj in objects:obj.data.materials[0]=baked
    return baked


def payload(liner,output_root=None):
    d=copy.deepcopy(liner);manifest=[]
    for part in s.PARTS:
        mesh=part['object'].data;mesh.calc_loop_triangles();base=len(d['positions']);first=len(d['triangles'])
        d['positions'].extend(s.to_ue(v.co) for v in mesh.vertices)
        d['weights'].extend(part.get('weights',[{part['bone']:1.} for _ in mesh.vertices]))
        uv=mesh.uv_layers.active;normals=mesh.corner_normals
        for face in mesh.loop_triangles:
            d['triangles'].append([base+i for i in face.vertices])
            d['normals'].append([[normals[i].vector.x,-normals[i].vector.y,normals[i].vector.z] for i in face.loops])
            d['uv'].append([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in face.loops])
            d['triangle_materials'].append(1)
        manifest.append(dict(name=part['name'],bone=part['bone'],kind=part['kind'],binding='native_soft' if 'weights' in part else 'rigid',first_vertex=base,vertices=len(mesh.vertices),first_triangle=first,triangles=len(mesh.loop_triangles)))
        if 'author_grid' in part:manifest[-1]['author_grid']=part['author_grid']
    d['contract']='Steel gauntlets; native glove liner; continuous deformable hand-back/wrist/thumb shell; independent index/middle/ring/pinky plates; flexible mail; shared existing animations'
    dest=Path(output_root) if output_root else R
    write(dest/'Master/M4.json',d);write(dest/'parts.json',manifest)
    return d


def mesh_from_payload(name,d,positions,indices,mats):
    faces=np.asarray(d['triangles'])[indices];used=np.unique(faces);remap={int(v):i for i,v in enumerate(used)}
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(positions[used].tolist(),[],[[remap[int(v)] for v in f] for f in faces]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    for mat in mats:mesh.materials.append(mat)
    uv=mesh.uv_layers.new(name='BakedTailoringUV')
    for poly,fi in zip(mesh.polygons,indices):
        poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for li,(u,v) in zip(poly.loop_indices,d['uv'][fi]):uv.data[li].uv=(u,1-v)
    return obj


def artwork(d,anatomy,liner_mat,steel_mat):
    # Same production geometry/materials, one relaxed empty right gauntlet.
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    posed,selected=posed_surface(d,d['bones'],anatomy,'r')
    rotation=np.asarray(Euler(np.radians((18,20,-8)),'XYZ').to_matrix())
    positions=((posed-np.array([0,7.5,0]))*.01)@rotation.T
    obj=mesh_from_payload('SM_SteelGauntlet_Pickup',d,positions,selected,[liner_mat,steel_mat])
    # Inward lining is added to leather only; steel already has real walls.
    lining=obj.vertex_groups.new(name='LeatherLining')
    leather_ids={v for f in obj.data.polygons if f.material_index==0 for v in f.vertices}
    lining.add(sorted(leather_ids),1.,'REPLACE')
    shell=obj.modifiers.new('LeatherInterior','SOLIDIFY');shell.vertex_group=lining.name;shell.thickness=.0006;shell.offset=-1.;shell.thickness_vertex_group=0.
    # Do not solidify the joined steel: separate the leather shell for its open cuff.
    obj.modifiers.remove(shell)
    s.activate(obj)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
    for poly in obj.data.polygons:poly.select=poly.material_index==0
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
    leather_obj=next(o for o in bpy.context.selected_objects if o is not obj)
    s.activate(leather_obj);shell=leather_obj.modifiers.new('EmptyLeatherInterior','SOLIDIFY');shell.thickness=.0006;shell.offset=-1.
    bpy.ops.object.modifier_apply(modifier=shell.name)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    # Origin at ground contact for a reusable inventory drop.
    coords=np.asarray([v.co[:] for v in obj.data.vertices]);centre=(coords.min(0)+coords.max(0))*.5;centre[2]=coords[:,2].min()
    for v in obj.data.vertices:v.co-=Vector(centre)
    bpy.ops.export_scene.fbx(filepath=str(R/'SM_SteelGauntlet_Pickup.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
    # Keep the editable empty-glove source separate from icon lighting/framing.
    # Icon-only revisions run render_steel_gauntlet_icon.py, never this exporter.
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'SteelGauntlet_Icon.blend'))
    from render_steel_gauntlet_icon import render_current_scene
    render_current_scene(obj)
    write(R/'artwork.json',dict(icon=str(R/'ue_steel_gauntlets.png'),pickup=str(R/'SM_SteelGauntlet_Pickup.fbx'),texture_size=2048,production_materials_shared=True,runtime_tested=False))


def main():
    R.mkdir(parents=True,exist_ok=True);T.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    d=read(R/'Sources/M4.json')
    anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    liner,rig=s.make_liner(d);s.PARTS.clear()
    metal_liner.apply_to_liner(liner)
    mat,color,orm,bs,out=authored_steel();mat.use_fake_user=True
    for side in ('r','l'):hand(d,anatomy,side,rig,mat)
    print('STEEL_GAUNTLET_GEOMETRY_AUTHORED',len(s.PARTS),flush=True)
    if '--geometry-only' in sys.argv:
        payload(d,R/'ArticulationSolve20260928/Candidate')
        return
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'SteelGauntlet_Authored.blend'))
    steel=bake_steel(mat,color,orm,bs,out)
    complete=payload(d)
    bpy.ops.file.pack_all();s.activate(liner)
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'SteelGauntlet_M4.blend'))
    artwork(complete,anatomy,liner.data.materials[0],steel)
    print('STEEL_GAUNTLET_ARTWORK_SAVED',flush=True)


def finish_saved_master():
    """Resume delivery artwork from a saved production master after a failure."""
    bpy.ops.wm.open_mainfile(filepath=str(R/'SteelGauntlet_M4.blend'))
    bpy.context.preferences.filepaths.save_version=0
    steel=bpy.data.materials['SteelGauntlet_Baked']
    for node in steel.node_tree.nodes:
        if node.type=='NORMAL_MAP':
            for link in list(node.inputs['Strength'].links):steel.node_tree.links.remove(link)
            normal=next(n for n in steel.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.name.endswith('Normal'))
            steel.node_tree.links.new(normal.outputs[0],node.inputs['Color'])
            node.inputs['Strength'].default_value=1.
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'SteelGauntlet_M4.blend'))
    d=read(R/'Master/M4.json')
    anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    liner=metal_liner.blender_material()
    artwork(d,anatomy,liner,steel)


if __name__=='__main__':
    if '--finish' in sys.argv:finish_saved_master()
    else:main()
