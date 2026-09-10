"""Isolated WRAD hand skinning repair. Uses linear skinning, never changes actions.

Blender --background --python repair_arms_skinning.py -- --variant weights --render
All outputs stay in SourceAssets/ArmsRepair20260909; delivered sources are read only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ArmsRepair20260909'
SOURCE = ROOT / 'SourceAssets/AKMReplacement/SK_AKM_Replacement_Source.blend'
WRAD = ROOT / 'SourceAssets/ArmsReplacement/WRAD_Original/arms.blend'
SAMPLES = [('idle', 1), ('reload', 52), ('reload_empty', 52), ('reload_empty', 75)]


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x-a)/(b-a)))
    return t*t*(3.0-2.0*t)


def weights_of(mesh):
    return [{mesh.vertex_groups[g.group].name: float(g.weight) for g in v.groups if g.weight > 1e-8}
            for v in mesh.data.vertices]


def set_weights(mesh, weights):
    mesh.vertex_groups.clear()
    names = sorted({n for w in weights for n, value in w.items() if value > 1e-8})
    groups = {n: mesh.vertex_groups.new(name=n) for n in names}
    for i, row in enumerate(weights):
        total = sum(row.values())
        if total <= 0.0:
            raise RuntimeError(f'Unweighted vertex {i}')
        for n, w in row.items():
            if w > 1e-8:
                groups[n].add([i], w/total, 'REPLACE')


def head(rig, name):
    return rig.data.bones[name].head_local.copy()


def anatomical_frame(rig, side, source=False):
    h = head(rig, f'wrist.{side}' if source else f'hand_{side}')
    idx = head(rig, f'finger_index1.{side}' if source else f'index_01_{side}')
    mid = head(rig, f'finger_middle1.{side}' if source else f'middle_01_{side}')
    pnk = head(rig, f'finger_pinky1.{side}' if source else f'pinky_01_{side}')
    y = (mid-h).normalized()
    x = (idx-pnk); x = (x-y*x.dot(y)).normalized()
    z = x.cross(y).normalized()
    return h, Matrix((x,y,z)).transposed(), (mid-h).length, (idx-pnk).length


def load_source_mesh():
    with bpy.data.libraries.load(str(WRAD), link=False) as (src, dst):
        dst.objects = ['arms', 'arms_mesh']
    for ob in dst.objects:
        bpy.context.collection.objects.link(ob)
    source_rig = next(ob for ob in dst.objects if ob.type == 'ARMATURE')
    source_mesh = next(ob for ob in dst.objects if ob.type == 'MESH')
    source_mesh.modifiers.clear()
    bpy.context.view_layer.objects.active = source_mesh
    modifier = source_mesh.modifiers.new('CorrespondenceSubdivision', 'SUBSURF')
    modifier.levels = modifier.render_levels = 2
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    source_mesh.hide_render = True
    source_rig.hide_render = True
    return source_rig, source_mesh


def repair_weights(mesh, source_mesh, source_rig, target_rig, anatomical=False):
    original = weights_of(mesh)
    source_weights = weights_of(source_mesh)
    if len(source_weights) != len(original):
        raise RuntimeError('Source subdivision correspondence does not match delivered topology')
    regions = {side: [] for side in ('l','r')}
    new_weights = []
    for i, vertex in enumerate(source_mesh.data.vertices):
        row = original[i].copy()
        sw = source_weights[i]
        for side in ('l', 'r'):
            palm_name = f'hand_{side}'
            palm = sw.get(f'wrist.{side}', 0.0)
            h, basis, length, width = anatomical_frame(source_rig, side, True)
            local = basis.transposed() @ (vertex.co-h)
            in_palm = 0.04 < local.y/length < 1.08 and palm > 0.12
            if in_palm:
                regions[side].append(i)
            # Distal phalanges may not influence the proximal palm/web. Classify
            # in the original WRAD anatomical coordinates, not the warped fit.
            for finger in ('thumb','index','middle','ring','pinky'):
                names = [f'{finger}_0{j}_{side}' for j in (1,2,3)]
                total = sum(row.get(n,0.0) for n in names)
                if total < 1e-8:
                    continue
                p0 = head(source_rig, f'finger_{finger}1.{side}')
                p1 = head(source_rig, f'finger_{finger}2.{side}')
                axis = p1-p0
                along = (vertex.co-p0).dot(axis)/axis.length_squared
                proximal = 1.0-smooth(0.72, 1.06, along)
                radial_gate=1.0
                if anatomical and finger=='thumb':
                    chain=[head(source_rig,f'finger_thumb{j}.{side}') for j in (1,2,3)]
                    chain.append(source_rig.data.bones[f'finger_thumb3.{side}'].tail_local.copy())
                    distance=min((vertex.co-(a+(b-a)*max(0,min(1,(vertex.co-a).dot(b-a)/(b-a).length_squared)))).length for a,b in zip(chain,chain[1:]))
                    radial_gate=1-smooth(.115,.225,distance)
                    proximal=max(proximal,smooth(.015,.16,palm))
                # At the thumb web, reduce the old broad influence without a
                # hard boundary. Whole-finger vertices retain their articulation.
                if finger == 'thumb' and palm > 1e-7:
                    pair = palm+total
                    fraction = total/pair
                    retained = total*radial_gate if anatomical else pair * fraction**1.8
                    strength = 1.0 if anatomical else proximal
                    new_total = total+(retained-total)*strength
                    removed = total-new_total
                    for n in names:
                        row[n] = row.get(n,0.0) * new_total/total
                    row[palm_name] = row.get(palm_name,0.0)+removed
                for n in names[1:]:
                    moved = row.get(n,0.0)*proximal
                    row[n] = row.get(n,0.0)-moved
                    row[names[0]] = row.get(names[0],0.0)+moved
            # Preserve the animated twist helper. Allocate a continuous sleeve
            # influence along the actual elbow/wrist axis instead of source labels.
            lower = f'lowerarm_{side}'
            twist = f'lowerarm_twist_01_{side}'
            forearm = row.get(lower,0.0)+row.get(twist,0.0)
            if forearm > 1e-8:
                elbow = head(source_rig, f'forearm.{side}')
                wrist = head(source_rig, f'wrist.{side}')
                axis = wrist-elbow
                t = (vertex.co-elbow).dot(axis)/axis.length_squared
                influence = 0.78*smooth(0.08,0.92,t)
                row[twist] = forearm*influence
                row[lower] = forearm*(1.0-influence)
        new_weights.append(row)
    set_weights(mesh,new_weights)
    return original, new_weights, regions


def rebuild_hand_fit(mesh, source_mesh, source_rig, rig, weights, continuous=False):
    """One thickness-preserving palm frame; independently oriented thumb chain.

    Palm/web vertices use that coherent frame. Distal fingers may follow their
    anatomical segment frames; they cannot pull the palm through distal weights.
    """
    palm={};fingers={};landmarks={}
    for side in ('l','r'):
        sh,sb,sl,sw=anatomical_frame(source_rig,side,True)
        th,tb,tl,tw=anatomical_frame(rig,side,False)
        palm[side]=(sh,th,tb@Matrix.Diagonal(Vector((tw/sw,tl/sl,tw/sw)))@sb.transposed())
        if continuous:
            # A smooth palm warp makes all finger-root landmarks agree with the
            # finger fits. Front/back share displacement, preserving thickness.
            source_marks=[sh, sh-sb.col[1]*sl*.5]
            target_marks=[th, th-tb.col[1]*tl*.5]
            for finger in ('thumb','index','middle','ring','pinky'):
                source_marks.append(head(source_rig,f'finger_{finger}1.{side}'))
                target_marks.append(head(rig,f'{finger}_01_{side}'))
            xy=np.array([tuple((sb.transposed()@(p-sh))/sl)[:2] for p in source_marks])
            delta=np.array([tuple(t-(th+palm[side][2]@(s-sh))) for s,t in zip(source_marks,target_marks)])
            kernel=np.exp(-np.sum((xy[:,None,:]-xy[None,:,:])**2,axis=2)/(2*.55**2))
            coeff=np.linalg.solve(kernel+np.eye(len(xy))*1e-7,delta)
            landmarks[side]=(sb,sl,xy,coeff)
        for finger in ('thumb','index','middle','ring','pinky'):
            source_chain=[head(source_rig,f'finger_{finger}{j}.{side}') for j in (1,2,3)]
            source_chain.append(source_rig.data.bones[f'finger_{finger}3.{side}'].tail_local.copy())
            target_chain=[head(rig,f'{finger}_0{j}_{side}') for j in (1,2,3)]
            target_chain.append(target_chain[-1]+(target_chain[-1]-target_chain[-2])*.72)
            if finger=='thumb':
                sn=(source_chain[1]-source_chain[0]).cross(source_chain[0]-sh).normalized()
                tn=(target_chain[1]-target_chain[0]).cross(target_chain[0]-th).normalized()
                # Cross products can face opposite palm hemispheres in the two
                # rigs. Keep a consistent anatomical roll before blending fits.
                if sn.dot(sb.col[2]) < 0: sn = -sn
                if tn.dot(tb.col[2]) < 0: tn = -tn
            else:
                sn=sb.col[2].copy();tn=tb.col[2].copy()
            transverse=(target_chain[1]-target_chain[0]).length/(source_chain[1]-source_chain[0]).length
            for j in range(3):
                sa,se=source_chain[j:j+2];ta,te=target_chain[j:j+2]
                sy=(se-sa).normalized();sx=sy.cross(sn).normalized();sz=sx.cross(sy).normalized()
                ty=(te-ta).normalized();tx=ty.cross(tn).normalized();tz=tx.cross(ty).normalized()
                sm=Matrix((sx,sy,sz)).transposed();tm=Matrix((tx,ty,tz)).transposed()
                axial=(te-ta).length/(se-sa).length
                fingers[f'{finger}_0{j+1}_{side}']=(sa,ta,tm@Matrix.Diagonal(Vector((transverse,axial,transverse)))@sm.transposed())
    for i,vertex in enumerate(mesh.data.vertices):
        source_point=source_mesh.data.vertices[i].co
        row=weights[i]
        influenced=sum(w for n,w in row.items() if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')))
        if influenced<=1e-8:continue
        result=vertex.co*(1-influenced)
        for n,w in row.items():
            if n.startswith('hand_'):
                side=n[-1]
                sh,th,m=palm[side]
                mapped=th+m@(source_point-sh)
                if continuous:
                    basis,length,centers,coeff=landmarks[side]
                    xy=np.array(tuple((basis.transposed()@(source_point-sh))/length)[:2])
                    factors=np.exp(-np.sum((centers-xy)**2,axis=1)/(2*.55**2))
                    mapped+=Vector(factors@coeff)
                result+=mapped*w
            elif n in fingers:
                sh,th,m=fingers[n];result+=(th+m@(source_point-sh))*w
        vertex.co=result


def set_pose(rig, clip, frame):
    rig.data.pose_position = 'POSE'
    action = bpy.data.actions['AKM_'+clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def points(mesh):
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    array = np.array([tuple(v.co) for v in data.vertices])
    evaluated.to_mesh_clear()
    return array


def measure(mesh, rig, regions):
    rest = np.array([tuple(v.co) for v in mesh.data.vertices])
    edges = np.array([tuple(e.vertices) for e in mesh.data.edges])
    mesh.data.calc_loop_triangles()
    tris = np.array([tuple(t.vertices) for t in mesh.data.loop_triangles])
    edge_lengths = np.linalg.norm(rest[edges[:,1]]-rest[edges[:,0]],axis=1)
    rest_cross = np.cross(rest[tris[:,1]]-rest[tris[:,0]],rest[tris[:,2]]-rest[tris[:,0]])
    rest_area = np.linalg.norm(rest_cross,axis=1)
    samples = []
    for clip, frame in SAMPLES:
        set_pose(rig,clip,frame)
        posed = points(mesh)
        lengths = np.linalg.norm(posed[edges[:,1]]-posed[edges[:,0]],axis=1)
        cross = np.cross(posed[tris[:,1]]-posed[tris[:,0]],posed[tris[:,2]]-posed[tris[:,0]])
        area = np.linalg.norm(cross,axis=1)
        row = {'action':clip,'frame':frame,'regions':{}}
        for side, vertex_ids in regions.items():
            mask = np.zeros(len(rest),dtype=bool);mask[vertex_ids] = True
            edge_mask = mask[edges].all(axis=1)&(edge_lengths>1e-5)
            tri_mask = mask[tris].all(axis=1)&(rest_area>1e-8)
            ratio = lengths[edge_mask]/edge_lengths[edge_mask]
            ar = area[tri_mask]/rest_area[tri_mask]
            bone = rig.pose.bones[f'hand_{side}']
            transform = np.array(bone.matrix @ bone.bone.matrix_local.inverted())[:3,:3]
            expected = rest_cross @ transform.T
            flips = (np.sum(expected*cross,axis=1)<0)&tri_mask
            row['regions'][side] = {'vertices':len(vertex_ids),'edges':int(edge_mask.sum()),'triangles':int(tri_mask.sum()),
                'edge_ratio_p01_p50_p99_max':np.quantile(ratio,[.01,.5,.99,1]).tolist(),
                'area_ratio_p01_p50_p99_max':np.quantile(ar,[.01,.5,.99,1]).tolist(),
                'normal_opposed_to_rigid_palm_count':int(flips.sum())}
        samples.append(row)
    return samples


def setup_render(rig):
    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        if ob.type in ('LIGHT','CAMERA'):
            bpy.data.objects.remove(ob,do_unlink=True)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 960;scene.render.resolution_y = 720;scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG';scene.render.film_transparent = False
    scene.world.color = (.12,.14,.17);scene.view_settings.look = 'AgX - Medium High Contrast'
    data = bpy.data.cameras.new('ArmsRepairCamera')
    camera = bpy.data.objects.new(data.name,data);bpy.context.collection.objects.link(camera);scene.camera = camera
    data.lens = 60;data.clip_start = .001
    for name,pos,power,color in [('Key',(1,-.4,1),150,(1,.87,.72)),('Fill',(-.8,0,.5),90,(.62,.77,1)),('Rim',(.2,1,.7),150,(.8,.9,1))]:
        ld = bpy.data.lights.new('Repair_'+name,'AREA');ld.energy=power;ld.size=2;ld.color=color
        ob = bpy.data.objects.new(ld.name,ld);bpy.context.collection.objects.link(ob);ob.location=pos
        ob.rotation_euler=(Vector((0,.3,-.1))-ob.location).to_track_quat('-Z','Y').to_euler()
    return camera


def render_pairs(before, after, rig, variant):
    camera = setup_render(rig)
    scene = bpy.context.scene
    for clip, frame in SAMPLES:
        set_pose(rig,clip,frame)
        for view in ('natural','palm_r','palm_l'):
            if view == 'natural':
                center=Vector((0,.24,-.13));camera.location=center+Vector((.85,-1.15,.55));camera.data.lens=60
            else:
                side=view[-1]
                bone=rig.pose.bones[f'hand_{side}']
                mid=rig.pose.bones[f'middle_01_{side}']
                idx=rig.pose.bones[f'index_01_{side}']
                pnk=rig.pose.bones[f'pinky_01_{side}']
                wrist=rig.matrix_world@bone.matrix.translation
                base=rig.matrix_world@mid.matrix.translation
                center=(wrist+base)*.5
                width=rig.matrix_world@idx.matrix.translation-rig.matrix_world@pnk.matrix.translation
                normal=width.cross(base-wrist).normalized()
                # Anatomical inside-palm viewpoint; exact same camera for A/B.
                camera.location=center+normal*(.26 if side=='r' else -.26)+(wrist-base).normalized()*.06
                camera.data.lens=62
            camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            for stage,visible,hidden in [('before',before,after),('after',after,before)]:
                visible.hide_render=False;hidden.hide_render=True
                scene.render.filepath=str(OUT/f'{variant}_{clip}_{frame:03d}_{view}_{stage}.png')
                bpy.ops.render.render(write_still=True)
    before.hide_render=True;after.hide_render=False


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--variant',default='weights')
    parser.add_argument('--render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not args.variant.replace('_','').isalnum():raise ValueError('Invalid variant name')
    OUT.mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig=bpy.data.objects['SK_AKM_Viewmodel'];before=bpy.data.objects['SK_ArmsReplacement_WRAD']
    source_rig,source_mesh=load_source_mesh()
    candidate=before.copy();candidate.data=before.data.copy();candidate.name='SK_ArmsRepair_WRAD'
    bpy.context.collection.objects.link(candidate)
    for ob in (before,candidate):
        for modifier in ob.modifiers:
            if modifier.type=='ARMATURE':modifier.use_deform_preserve_volume=False
    anatomical=args.variant!='weights'
    original,new,regions=repair_weights(candidate,source_mesh,source_rig,rig,anatomical)
    if anatomical:rebuild_hand_fit(candidate,source_mesh,source_rig,rig,new,continuous=args.variant=='anatomy_v3')
    before_metrics=measure(before,rig,regions)
    after_metrics=measure(candidate,rig,regions)
    report={'variant':args.variant,'source':str(SOURCE),'license':'WRAD ARMS by wriks, CC0 1.0; license retained in ArmsReplacement/WRAD_Original/LICENSE',
        'linear_skinning':True,'preserve_volume':False,'rest_geometry_changed':anatomical,'actions_changed':False,
        'changed_weight_vertices':sum(any(abs(w.get(k,0)-v.get(k,0))>1e-6 for k in w.keys()|v.keys()) for w,v in zip(original,new)),
        'region_definition':'Original WRAD wrist weight > 0.12 and palm-forward coordinate 0.04..1.08 of wrist-to-middle-base length; includes thumb web.',
        'normal_metric':'Triangle orientation relative to rigid hand-bone transformed rest normal; reports local folding, not a generic outward-normal ground truth.',
        'before':before_metrics,'after':after_metrics,
        'diagnostic_vertices':[{'index':i,'source_position':list(source_mesh.data.vertices[i].co),'rest_position':list(before.data.vertices[i].co),'before_weights':original[i],'after_weights':new[i],
            'thumb_proximal_coordinate':float((source_mesh.data.vertices[i].co-head(source_rig,'finger_thumb1.r')).dot(head(source_rig,'finger_thumb2.r')-head(source_rig,'finger_thumb1.r'))/(head(source_rig,'finger_thumb2.r')-head(source_rig,'finger_thumb1.r')).length_squared)} for i in (1773,6004,1772,6005,198,1004)]}
    (OUT/f'repair_{args.variant}_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('ARMS_REPAIR_METRICS '+json.dumps(report),flush=True)
    bpy.data.objects.remove(source_mesh,do_unlink=True);bpy.data.objects.remove(source_rig,do_unlink=True)
    before.hide_render=True;before.hide_set(True);candidate.hide_render=False;candidate.hide_set(False)
    if args.render:render_pairs(before,candidate,rig,args.variant)
    set_pose(rig,'idle',1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'SK_ArmsRepair_{args.variant}.blend'))
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);candidate.hide_set(False)
    rig.select_set(True);candidate.select_set(True);bpy.context.view_layer.objects.active=rig
    rig.animation_data_clear();rig.data.pose_position='REST'
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'SK_ArmsRepair_{args.variant}.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=False,axis_forward='-Z',axis_up='Y',apply_scale_options='FBX_SCALE_NONE',use_armature_deform_only=False)
    print('ARMS_REPAIR_CANDIDATE_READY '+args.variant,flush=True)


if __name__=='__main__':main()
