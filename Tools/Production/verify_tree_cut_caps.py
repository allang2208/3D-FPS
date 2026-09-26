"""只读核对 SM_CutCap_<A..D>：存在性、槽位材质、三角形数、材质号分布、包围盒。"""
import unreal as u

TAG = 'CAPCHECK'


def log(message):
    u.log('%s %s' % (TAG, message))
    print('%s %s' % (TAG, message))


for kind in 'ABCD':
    path = '/Game/Items/HarvestTimber/SM_CutCap_' + kind
    asset = u.EditorAssetLibrary.load_asset(path)
    if not asset:
        log('%s MISSING %s' % (kind, path))
        continue
    slots = []
    try:
        for entry in asset.get_editor_property('static_materials'):
            material = entry.get_editor_property('material_interface')
            slots.append((str(entry.get_editor_property('material_slot_name')),
                          material.get_name() if material else None))
    except Exception as error:
        log('WARN %s 读槽异常 %s' % (kind, error))
    read = u.GeometryScriptMeshReadLOD()
    read.lod_type = u.GeometryScriptLODType.SOURCE_MODEL
    dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read)
    histogram = {}
    if outcome == u.GeometryScriptOutcomePins.SUCCESS:
        for triangle in range(dynamic.get_triangle_count()):
            material_id, valid = u.GeometryScript_Materials.get_triangle_material_id(dynamic, triangle)
            if valid:
                histogram[material_id] = histogram.get(material_id, 0) + 1
    bounds = asset.get_bounds()
    log('%s slots=%s tris=%s material_ids=%s origin_z=%.1f extent=%s' % (
        kind, slots, dynamic.get_triangle_count() if outcome == u.GeometryScriptOutcomePins.SUCCESS else outcome,
        histogram, bounds.origin.z, [round(bounds.box_extent.x, 1), round(bounds.box_extent.z, 1)]))

log('CAPCHECK_DONE')