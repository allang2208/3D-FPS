"""扇区双半径带验证：嫌疑扇区外壳是否完整（决定方位角掩码会不会开天窗）+簇真实范围。只读。"""
import math
import unreal as u

TAG = 'SECTORPROBE'


def log(m):
    u.log('%s %s' % (TAG, m))
    print('%s %s' % (TAG, m))


def load_positions(kind):
    asset = u.EditorAssetLibrary.load_asset('/Game/Items/HarvestTimber/SM_CutUpper_' + kind)
    if not asset:
        return None
    read = u.GeometryScriptMeshReadLOD()
    read.lod_type = u.GeometryScriptLODType.SOURCE_MODEL
    dynamic, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), read)
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
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


def sector(p):
    return int(((math.degrees(math.atan2(p[1], p[0])) % 360) // 15))


for kind in 'ABCD':
    positions = load_positions(kind)
    if not positions:
        log('KIND %s MISSING' % kind)
        continue
    strip = [p for p in positions if 15.0 <= (p[0] ** 2 + p[1] ** 2) ** 0.5 < 30.0 and 42.0 <= p[2] <= 600.0]
    shell = [p for p in positions if 30.0 <= (p[0] ** 2 + p[1] ** 2) ** 0.5 <= 46.0 and 42.0 <= p[2] <= 210.0]
    hs = [0] * 24
    for p in strip:
        hs[sector(p)] += 1
    ss = [0] * 24
    for p in shell:
        ss[sector(p)] += 1
    log('KIND %s STRIP(15-30,42-600)=%d hist=%s' % (kind, len(strip), hs))
    log('KIND %s SHELL(30-46,42-210)=%d hist=%s' % (kind, len(shell), ss))
    # 簇的真实 z 范围（只统计 STRIP 直方图 >=30 的扇区内的顶点）
    hot = {i for i, c in enumerate(hs) if c >= 30}
    if hot:
        zs = sorted(p[2] for p in strip if sector(p) in hot)
        if zs:
            log('KIND %s HOTSECTORS=%s z=[%.0f..%.0f]' % (kind, sorted(hot), zs[0], zs[-1]))
log('DONE')
