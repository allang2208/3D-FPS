
import unreal as u, json
m = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')
api = [x for x in dir(m) if 'ref' in x.lower() or 'skeleton' in x.lower() or 'bone' in x.lower()]
u.log('AKM_API ' + json.dumps(api))
