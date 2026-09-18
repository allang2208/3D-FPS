import unreal as u, json
m = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')
sk = m.skeleton
api = [x for x in dir(sk) if 'ref' in x.lower() or 'bone' in x.lower()]
u.log('SK_API ' + json.dumps(api[:30]))
