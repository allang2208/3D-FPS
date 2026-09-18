import unreal as u, json
def probe(path, label):
    m = u.load_asset(path)
    if not m:
        u.log(label + ' MISSING'); return
    sk = m.skeleton
    ref = sk.get_reference_pose()
    names = [str(n) for n in ref.get_bone_names()]
    out = {}
    for i, n in enumerate(names):
        if n in ('WPN_root', 'WPN_SOCKET_Magazine'):
            t = ref.get_bone_pose(n)
            tr = t.translation; sc = t.scale3d; q = t.rotation
            out[n] = {'t': [round(tr.x,4), round(tr.y,4), round(tr.z,4)],
                      's': [round(sc.x,4), round(sc.y,4), round(sc.z,4)],
                      'q': [round(q.x,4), round(q.y,4), round(q.z,4), round(q.w,4)]}
    u.log(label + '_BONES ' + json.dumps(out))
probe('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative', 'AKM')
probe('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny', 'QBZ')
probe('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416', 'M4')
