"""找倒木切口端的突出物：SM_CutUpper_* 断面附近几何簇只读探针（2026-09-29，commandlet 安全）。

用户图：细杆从切口端断面附近斜向上伸出，光滑发黑。树干是空心壳（半径 33-45），
轴心 30cm 内本应无任何顶点——出现即嫌疑（芯钉/退化刺/残根）。按半径分桶+方位角统计。
只读，不改不存。结果 STUB 行打印（配 -abslog 收集）。
"""
import math

import unreal as u

TAG = 'STUBPROBE'


def log(m):
    u.log('%s %s' % (TAG, m))
    print('%s %s' % (TAG, m))


def load_positions(kind):
    asset = u.EditorAssetLibrary.load_asset('/Game/Items/HarvestTimber/SM_CutUpper_' + kind)
    if not asset:
        log('KIND %s MISSING' % kind)
        return None
    read = u.GeometryScriptMeshReadLOD()
    read.lod_type = u.GeometryScriptLODType.SOURCE_MODEL
    dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        log('KIND %s COPY_FAIL' % kind)
        return None
    raw = u.GeometryScript_MeshQueries.get_all_vertex_positions(dynamic, False)
    positions = []
    for part in raw:
        if part.__class__.__name__ == 'GeometryScriptVectorList':
            for index in range(part.get_vector_list_length()):
                item = part.get_vector_list_item(index)
                p = item[0] if isinstance(item, tuple) else item
                positions.append((p.x, p.y, p.z))
            break
    return positions


def analyze(kind, positions):
    if not positions:
        return
    # 1) 轴心细簇：半径 < 15（壳体 33+，正常内空）。任何出现都是嫌疑。
    core = [p for p in positions if (p[0] ** 2 + p[1] ** 2) ** 0.5 < 15.0 and 40.0 <= p[2] <= 400.0]
    log('KIND %s verts=%d core(<15cm,40..400)=%d' % (kind, len(positions), len(core)))
    if core:
        zs = sorted(p[2] for p in core)
        zmin, zmax = zs[0], zs[-1]
        rs = [(p[0] ** 2 + p[1] ** 2) ** 0.5 for p in core]
        log('CORE %s z=[%.1f..%.1f] r=[%.1f..%.1f] mean_r=%.1f' % (
            kind, zmin, zmax, min(rs), max(rs), sum(rs) / len(rs)))
        # 顶点方位角直方图（24 桶），看簇是否集中
        hist = [0] * 24
        for p in core:
            hist[int(((math.degrees(math.atan2(p[1], p[0])) % 360) // 15))] += 1
        log('CORE %s yaw_hist15deg=%s' % (kind, hist))
    # 2) 断面层细节：z∈[42,52] 半径分桶（壳 33-38；芯钉会在小桶）
    face = [p for p in positions if 42.0 <= p[2] <= 52.0]
    buckets = {}
    for p in face:
        r = (p[0] ** 2 + p[1] ** 2) ** 0.5
        key = int(r // 5)
        buckets[key] = buckets.get(key, 0) + 1
    log('FACE %s z42..52 buckets5cm=%s' % (kind, sorted(buckets.items())))
    # 3) 贴干内层簇（15..30cm，42..200cm 高）：正常壳体不应有；残根会有
    inner = [p for p in positions if 15.0 <= (p[0] ** 2 + p[1] ** 2) ** 0.5 < 30.0 and 42.0 <= p[2] <= 200.0]
    if inner:
        hist = [0] * 24
        for p in inner:
            hist[int(((math.degrees(math.atan2(p[1], p[0])) % 360) // 15))] += 1
        log('INNER %s count=%d yaw_hist15deg=%s' % (kind, len(inner), hist))
    else:
        log('INNER %s count=0' % kind)


for kind in 'ABCD':
    try:
        analyze(kind, load_positions(kind))
    except Exception as error:
        log('KIND %s FAIL %s' % (kind, error))
log('DONE')
