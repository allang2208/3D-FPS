"""Author RealisticV2 ice modules and original PBR maps. Background only, no render."""
import bpy, bmesh, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'SourceAssets/IceWall20260930/RealisticV2'
DEST.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
manifest = []
for index in range(1, 5):
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.object
    ob.name = f'SM_IceBlock_{index:02d}'
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=6, use_grid_fill=True)
    for v in bm.verts:
        x, y, z = v.co
        if abs(x) > .49:
            # Shallow melt relief, with broad continuous faces instead of flat low-poly facets.
            wave = math.sin(y*7.2+index)*math.cos(z*6.1-index*.8)
            melt = .004 + .0045*(wave+1)*.5
            chip = .003*math.exp(-((y-.23*math.sin(index))**2+(z-.38)**2)/.014)
            v.co.x = math.copysign(.5-melt-chip, x)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(ob.data); bm.free()
    bevel = ob.modifiers.new('MeltedIceEdges', 'BEVEL')
    bevel.width = .008 + index*.0013; bevel.segments = 3
    bevel.limit_method = 'ANGLE'; bevel.angle_limit = .6
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for face in ob.data.polygons: face.use_smooth = True
    weighted = ob.modifiers.new('BroadSurfaceNormals', 'WEIGHTED_NORMAL')
    weighted.keep_sharp = True; weighted.weight = 45
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.1, island_margin=.018)
    bpy.ops.object.mode_set(mode='OBJECT')
    colors = ob.data.color_attributes.new(name='Frost', type='BYTE_COLOR', domain='CORNER')
    for loop in ob.data.loops:
        co = ob.data.vertices[loop.vertex_index].co
        edge = max(0, min(1, (max(abs(co.y),abs(co.z))-.43)/.07))
        colors.data[loop.index].color = (edge, 0, 0, 1)
    bpy.ops.export_scene.fbx(filepath=str(DEST/(ob.name+'.fbx')),use_selection=True,
        object_types={'MESH'},add_leaf_bones=False,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
    manifest.append({'mesh':ob.name,'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),
        'unit':'meters','interfaces':'flat Y/Z; smooth front/back melt relief'})
    ob.hide_set(True); ob.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(DEST/'IceWallRealisticV2.blend'))
(DEST/'geometry.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
