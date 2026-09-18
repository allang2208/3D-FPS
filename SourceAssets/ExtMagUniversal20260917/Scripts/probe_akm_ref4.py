import unreal as u, json
m = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')
sk = m.skeleton
ref = sk.get_reference_pose()
api = [x for x in dir(ref) if not x.startswith('_')]
u.log('REF_API ' + json.dumps(api[:40]))
