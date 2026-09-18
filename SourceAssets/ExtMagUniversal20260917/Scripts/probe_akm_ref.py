import unreal as u, json
m = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')
if not m: raise RuntimeError('akm mesh missing')
rs = m.reference_skeleton
out = {}
try:
    bones = rs.get_bone_names()
    for i, b in enumerate(bones):
        if 'WPN_root' in str(b) or 'WPN_SOCKET_Magazine' in str(b):
            t = rs.get_ref_bone_transform(i)
            tr = t.translation; sc = t.scale3d
            out[str(b)] = {'translation': [round(tr.x,3), round(tr.y,3), round(tr.z,3)], 'scale3d': [round(sc.x,4), round(sc.y,4), round(sc.z,4)]}
except Exception as e:
    out['api_error'] = str(e)[:200]
    # fallback: raw API surface
    out['api'] = [x for x in dir(rs) if not x.startswith('_')][:40]
u.log('AKM_REF_PROBE ' + json.dumps(out))
