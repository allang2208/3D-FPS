"""Prepare original M07 gill side-fold contact coverage, production only.

The V17 mother file, all display positions/UVs/normals/materials and the whole
83-bone reference remain authoritative. Hidden low-density sheets are taken
from the original leaf surfaces, including the lateral folds excluded by V09.
Only genuinely mobile, body-owned display fold skin rows can be reassigned to
the existing leaf chain. No simulation, rendering, UE or acceptance is run.
"""
from pathlib import Path
import copy
import json
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'BodyMotionV18/Proxy'
MASTER = ROOT/'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
TEMPLATE = ROOT/'BodyMotionV18/Cloth/cloth_ue_manifest_v18.json'
sys.path.insert(0, str(Path(__file__).parent))
import author_original_surfaces_v08 as surface


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def smooth(t):
    t = np.clip(t, 0., 1.)
    return t*t*(3.-2.*t)


def arrays(obj):
    points = np.empty((len(obj.data.vertices), 3), np.float32)
    obj.data.vertices.foreach_get('co', points.ravel())
    faces = np.asarray([list(f.vertices) for f in obj.data.polygons], np.int32)
    return points, faces


def weights(obj, names):
    lookup = {name:i for i,name in enumerate(names)}
    mapping = {g.index:lookup[g.name] for g in obj.vertex_groups if g.name in lookup}
    field = np.zeros((len(obj.data.vertices), len(names)), np.float32)
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.group in mapping:
                field[vertex.index, mapping[group.group]] = group.weight
    return field


def pack(field):
    ids = np.argpartition(field, -8, axis=1)[:, -8:]
    values = np.take_along_axis(field, ids, axis=1)
    order = np.argsort(-values, axis=1, kind='stable')
    ids = np.take_along_axis(ids, order, axis=1)
    values = np.take_along_axis(values, order, axis=1)
    values /= np.maximum(values.sum(axis=1, keepdims=True), 1.e-12)
    return ids, values


class OriginalSurface:
    def __init__(self, high, label, source_skin):
        self.points, self.faces = arrays(high)
        self.ids = np.asarray([v.value for v in high.data.attributes['source_vertex_id'].data], np.int32)
        self.tree = BVHTree.FromPolygons(self.points.tolist(), self.faces.tolist(), all_triangles=True)
        self.fold = source_skin['fold_source_distance_cm'][self.ids, label]

    def sample(self, points):
        samples, corners, bary = [], [], []
        for point in points:
            hit, normal, face, distance = self.tree.find_nearest(Vector(point))
            if face is None:
                raise RuntimeError('The original membrane surface has no matching source triangle.')
            tri = self.faces[face]
            a,b,c = self.points[tri]
            ab,ac,q = b-a,c-a,np.asarray(hit)-a
            aa,bb,cc = float(ab@ab),float(ab@ac),float(ac@ac)
            den = aa*cc-bb*bb
            if abs(den) < 1.e-12:
                value = np.asarray([1.,0.,0.])
            else:
                v = (cc*float(q@ab)-bb*float(q@ac))/den
                z = (aa*float(q@ac)-bb*float(q@ab))/den
                value = np.maximum([1.-v-z,v,z],0.)
                value /= max(float(value.sum()),1.e-12)
            corners.append(tri)
            bary.append(value)
            samples.append(float(distance))
        corners = np.asarray(corners, np.int32)
        bary = np.asarray(bary, np.float32)
        # The source fold field is a surface route to actual common attachment,
        # rather than the old global-Z mobility band.
        distance = (self.fold[corners]*bary).sum(axis=1)
        return distance, corners, bary, np.asarray(samples)


def repair_mobile_fold_skin(leaf, rig, label, original, names):
    points, _ = arrays(leaf)
    distance, _, _, _ = original.sample(points)
    field = weights(leaf, names)
    old = field.copy()
    own = [names.index(f'gill_{label:02d}_{i:02d}') for i in range(3)]
    body = [i for i,name in enumerate(names) if not name.startswith('gill_')]
    mass = field[:,body].sum(axis=1)
    # Preserve the real common fold, all existing gill_XX_00 mass and any fused
    # neighboring leaf mass. Only the clearly lateral mobile tissue is eligible.
    strength = smooth((distance-20.)/20.)*smooth((np.abs(points[:,0])-26.)/14.)
    strength *= (mass > .015)
    changed = np.flatnonzero((strength*mass) > 1.e-5)
    start = np.asarray(rig.data.bones[f'gill_{label:02d}_01'].head_local)
    end = np.asarray(rig.data.bones[f'gill_{label:02d}_02'].tail_local)
    axis = end-start
    progress = np.clip((points-start)@axis/max(float(axis@axis),1.e-12),0.,1.)
    distal = smooth((progress-.18)/.62)
    removed = mass*strength
    field[:,body] *= 1.-strength[:,None]
    field[:,own[1]] += removed*(1.-distal)
    field[:,own[2]] += removed*distal
    ids, values = pack(field[changed]) if len(changed) else ([],[])
    # Change local rows only. Global reassignment would quantize the untouched
    # roots and destroy the precise V16 hand / V17 leg preservation contract.
    groups = {g.name:g for g in leaf.vertex_groups}
    for row, row_ids, row_values in zip(changed,ids,values):
        row = int(row)
        for group in leaf.vertex_groups:
            group.remove([row])
        for index,value in zip(row_ids,row_values):
            if value > 1.e-7:
                groups[names[int(index)]].add([row],float(value),'REPLACE')
    leaf['gill_contact_revision'] = 'V18 local mobile fold body spill to existing gill_01/02; roots and original visible surface retained'
    return {'changed_display_fold_vertices':int(len(changed)),
        'maximum_transferred_body_mass':float(removed.max(initial=0.)),
        'protected_common_root_distance_cm':20.,
        'protected_inner_body_tissue_abs_x_cm':26.,
        'gill_00_weight_retained':True,'neighbor_leaf_mass_retained':True,
        'source_weight_policy':'Only lateral mobile body-owned fold rows; all original positions, triangles, UV and normals retained'}, weights(leaf,names)


def clean_proxy(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.025)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.003)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    duplicate = set()
    seen = set()
    bm.verts.index_update()
    for face in bm.faces:
        key = tuple(sorted(v.index for v in face.verts))
        if key in seen or face.calc_area() < 1.e-7:
            duplicate.add(face)
        seen.add(key)
    for edge in bm.edges:
        linked = [f for f in edge.link_faces if f not in duplicate]
        if len(linked) > 2:
            duplicate.update(sorted(linked,key=lambda f:f.calc_area())[:-2])
    if duplicate:
        bmesh.ops.delete(bm,geom=list(duplicate),context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def make_proxy(high, leaf, rig, label, original, names, source_skin, collection, simulation_material, old_panel):
    points, faces = original.points, original.faces
    # Select a single actual outward shell using original smooth normals and a
    # lateral/back view. Unlike the V09 abs(normal.y) rule, side folds remain.
    normals = np.asarray([v.normal[:] for v in high.data.vertices],np.float32)
    outward = np.asarray([.48 if label <= 3 else -.48,1.,0.],np.float32)
    outward /= np.linalg.norm(outward)
    normal = normals[faces].mean(axis=1)
    keep = (normal@outward) > .015
    used, index = np.unique(faces[keep].ravel(),return_inverse=True)
    proxy = surface.make_mesh(f'M07_OriginalGill_{label:02d}_SimulationV18',points[used],index.reshape(-1,3),
        simulation_material,collection)
    clean_proxy(proxy)
    before = {'vertices':len(proxy.data.vertices),'triangles':len(proxy.data.polygons)}
    # Hidden proxy only: retain original sheet folding/silhouette; do not add
    # global density, a Solidify layer, flat patches, or visible anatomy.
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.select_all(action='DESELECT')
    proxy.select_set(True)
    for triangle_budget in (290,240,210,180):
        if len(proxy.data.vertices) <= 295 and len(proxy.data.polygons) <= 300:
            break
        modifier = proxy.modifiers.new('V18OriginalLateralSheetCollapse','DECIMATE')
        modifier.ratio = min(1.,triangle_budget/max(len(proxy.data.polygons),1))
        modifier.use_collapse_triangulate = True
        modifier.delimit = set()
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        clean_proxy(proxy)
    p, f = arrays(proxy)
    distance, corners, bary, surface_error = original.sample(p)
    # Restore each collapsed vertex to the actual original surface. This is a
    # production fit, not a new cloth layer or replacement visible shape.
    for vertex in proxy.data.vertices:
        hit, _, _, _ = original.tree.find_nearest(vertex.co)
        vertex.co = hit
    p,f = arrays(proxy)
    distance, corners, bary, surface_error = original.sample(p)
    # Proxy skin follows the revised same-leaf display field by closest triangle.
    lp,lf = arrays(leaf)
    lt = BVHTree.FromPolygons(lp.tolist(),lf.tolist(),all_triangles=True)
    lf_weights = weights(leaf,names)
    proxy_field = np.zeros((len(p),len(names)),np.float32)
    for vertex in proxy.data.vertices:
        hit, _, face, _ = lt.find_nearest(vertex.co)
        tri = lf[face]
        a,b,c = lp[tri]
        ab,ac,q = b-a,c-a,np.asarray(hit)-a
        aa,bb,cc = float(ab@ab),float(ab@ac),float(ac@ac)
        den = aa*cc-bb*bb
        if abs(den)<1.e-12:
            value = np.asarray([1.,0.,0.])
        else:
            v = (cc*float(q@ab)-bb*float(q@ac))/den
            z = (aa*float(q@ac)-bb*float(q@ab))/den
            value = np.maximum([1.-v-z,v,z],0.)
            value /= max(float(value.sum()),1.e-12)
        proxy_field[vertex.index] = (lf_weights[tri]*value[:,None]).sum(axis=0)
    ids, values = pack(proxy_field)
    surface.assign(proxy,names,ids,values)
    surface.bind(proxy,rig)
    mobility = smooth((distance-2.)/35.)
    maximum = mobility*(28.,22.,16.)[(label-1)%3]
    pin = 1.-mobility
    group = proxy.vertex_groups.new(name='M07_Pin')
    for i,value in enumerate(pin):
        if value>0:
            group.add([i],float(value),'REPLACE')
    proxy['panel_id'] = label
    proxy['display_export_excluded'] = True
    proxy['topology_source'] = 'Actual original single outward shell including lateral fold faces; no planar rebuild or Solidify'
    proxy.hide_render = True
    panel = copy.deepcopy(old_panel)
    panel.update({'id':f'{label:02d}',
        'vertices_cm':np.c_[p[:,0],-p[:,1],p[:,2]].tolist(),
        'max_distance_cm':maximum.tolist(),'pin_weights':pin.tolist(),
        'vertex_count':len(p),'triangle_count':len(f),
        'root_world_m':(p[np.argmin(distance)]/100.).tolist(),
        'tip_world_m':(p[np.argmax(distance)]/100.).tolist(),
        'proxy_revision':'BodyMotionV18 original lateral folded shell; attachment-surface-distance mobility',
        'proxy_orientation':'Original outward shell with side-fold coverage; no abs(normal.y) side-face removal',
        'folded_proxy_faces_removed':0,
        'attachment_surface_distance_cm':distance.tolist(),
        'true_root_fixed_distance_cm':2.})
    details = {'panel':label,'full_single_original_sheet':before,
        'simulation_vertices':len(p),'simulation_triangles':len(f),
        'true_fixed_root_vertices':int((maximum<=1.e-6).sum()),
        'max_distance_cm':float(maximum.max(initial=0.)),
        'lateral_fold_triangle_count':int((np.abs(np.asarray([poly.normal.y for poly in proxy.data.polygons]))<.15).sum()),
        'geometry_source':'Original Meshy leaf outward surface, preserving actual folds; edge-collapse only on hidden simulation sheet'}
    return proxy,panel,details


def author():
    OUT.mkdir(parents=True,exist_ok=True)
    template = json.loads(TEMPLATE.read_text(encoding='utf-8'))
    source_skin = np.load(ROOT/'RecoveryOriginalV09/gill_skin_weights_v09.npz')
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    names = [b.name for b in rig.data.bones]
    collection = bpy.data.collections.new('M07_OriginalHiddenClothV18')
    bpy.context.scene.collection.children.link(collection)
    simulation_material = bpy.data.materials.get('M07_GillSimulation') or bpy.data.materials.new('M07_GillSimulation')
    display = [bpy.data.objects['M07_OriginalBody_Display']]
    panels, proxies, details = [], [], []
    for label in range(1,7):
        high = bpy.data.objects[f'M07_OriginalGill_{label:02d}_High']
        leaf = bpy.data.objects[f'M07_OriginalGill_{label:02d}_Display']
        original = OriginalSurface(high,label,source_skin)
        repair,_ = repair_mobile_fold_skin(leaf,rig,label,original,names)
        proxy,panel,detail = make_proxy(high,leaf,rig,label,original,names,source_skin,collection,simulation_material,template['panels'][label-1])
        detail.update(repair)
        details.append(detail)
        panels.append(panel)
        proxies.append(proxy)
        display.append(leaf)
        print('M07_V18_ORIGINAL_FOLD_CONTACT_PREPARED '+json.dumps(detail),flush=True)
    cloth = copy.deepcopy(template)
    cloth.update({'panels':panels,'proxy_topology_modified':True,
        'geometry_modified':False,
        'method':'Actual original six-leaf lateral single shells; true root surface-distance mobility; fourteen kinematic colliders and existing leaf-bone local clearance',
        'proxy_source':'BodyMotionV18/Proxy/SK_M07_ClothBuildSource_BodyMotionV18.fbx',
        'tested':False,'runtime_tested':False,'rendered':False})
    cloth_file = OUT/'cloth_ue_manifest_v18.json'
    display_file = OUT/'SK_M07_Display_BodyMotionV18.fbx'
    simulation_file = OUT/'SK_M07_ClothBuildSource_BodyMotionV18.fbx'
    blend_file = OUT/'M07_Original_GillContacts_V18.blend'
    surface.export(display_file,rig,display)
    # Source export is exclusively the six hidden simulation leaves. Its single
    # slot and the display-only FBX make accidental proxy rendering impossible.
    surface.export(simulation_file,rig,proxies)
    write(cloth_file,cloth)
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj not in display:
            obj.hide_set(True)
            obj.hide_render=True
    rig.data.pose_position='POSE'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file),compress=True)
    write(OUT/'proxy_manifest_v18.json',{'revision':'BodyMotionV18',
        'source':str(blend_file),'original_master':str(MASTER),
        'display_fbx':str(display_file),'simulation_fbx':str(simulation_file),
        'cloth_manifest':str(cloth_file),
        'reference_skeleton':'/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'reference_revision':'OriginalV11','bone_count':len(rig.data.bones),
        'reference_pose_modified':False,'visible_geometry_modified':False,'uv_modified':False,
        'body_arm_hand_leg_weights_modified':False,
        'display_fold_weights_modified':any(d['changed_display_fold_vertices']>0 for d in details),
        'source_saved':True,'fbx_exported':True,'ue_imported':False,'ue_saved':False,
        'simulation_vertices':sum(len(p.data.vertices) for p in proxies),
        'simulation_triangles':sum(len(p.data.polygons) for p in proxies),
        'changed_display_fold_vertices':sum(d['changed_display_fold_vertices'] for d in details),
        'display_triangles':sum(len(p.data.polygons) for p in display),
        'display_vertices':sum(len(p.data.vertices) for p in display),
        'collision_capsules':len(cloth['collision_capsules']),'panels':details,
        'preserved':['All original visible positions, triangles, UV, normal and materials',
            'All V17 body/hip/knee/ankle weights and V16 shoulder/arm/hand/finger weights',
            'Original V11 83 bone reference hierarchy, lengths and transforms',
            'Real common fold attachments and existing gill_XX_00 mass',
            'All existing compatible actions'],
        'scope':'Hidden proxy lateral coverage and attachment-surface-distance mobility; mobile display fold rows reassigned only when a true body-weight spill is present',
        'display_weight_finding':'The existing V09 common-fold field already confines body/arm mass to true shared roots; no eligible mobile lateral fold requires reassignment in this V17 source',
        'runtime_tested':False,'rendered':False,'tested':False,'user_review_pending':True})
    print('M07_V18_ORIGINAL_GILL_CONTACT_SOURCE_AND_FBX_SAVED '+str(OUT/'proxy_manifest_v18.json'),flush=True)


if __name__=='__main__':
    author()
