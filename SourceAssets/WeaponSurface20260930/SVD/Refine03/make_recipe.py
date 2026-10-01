"""Author scoped SVD finish settings from the captured current material bindings."""
import json
from pathlib import Path
O=Path(__file__).parent
targets=json.loads((O/'targets.json').read_text())
bakes=json.loads((O/'Bake/bake_receipt.json').read_text())['textures']
normals={(v['mesh'],v['slot']):k for k,v in bakes.items()}
for t in targets:
 key,name=t['mesh'],t['slot']
 category='satin steel';rough=.38;color=[.032,.033,.035]
 if any(s in name for s in ('Interface','AdapterSteel','Mount')):
  category='anodized mount';rough=.44;color=[.022,.023,.024]
 if key in ('suppressor','tactical_suppressor','brake'):
  category='muzzle coating';rough=.45;color=[.025,.026,.027]
 if key in ('core_stock','tactical_telescopic','skeleton','qr_performance') and 'Adapter' not in name:
  category='stock hardware';rough=.42;color=[.028,.029,.030]
 if key=='tactical_vertical' and name=='SVD_tactical_vertical_0':rough=.43
 if key=='SVD' and name=='SVD_FactoryMuzzle':rough=.42;color=[.026,.027,.028]
 if key=='SVD' and name=='SM_SVD_ScopeBody_001':category='optic housing';rough=.43;color=[.024,.025,.026]
 if 'BoltCarrier' in name:category='moving steel';rough=.31;color=[.068,.069,.070]
 if 'ChargingHandle' in name:category='moving steel';rough=.34;color=[.043,.044,.045]
 if 'Trigger' in name or 'SafetyLever' in name:rough=.35;color=[.035,.036,.037]
 if 'Fastener' in name:category='fastener';rough=.36;color=[.038,.039,.040]
 if 'Recess' in name:category='recess';rough=.51;color=[.018,.019,.020]
 magazine=(key=='ext_mag' or (key=='SVD' and name in ('SM_SVD_Magazine_001','SVD_InterfaceSteel')))
 if magazine:category='magazine satin';rough=.37 if 'Interface' in name else .34;color=[.034,.035,.037]
 s={'WS_Roughness':rough,'WS_GrainRoughness':.012,'WS_MottleRoughness':.005,
    'WS_MottleColor':0.,'WS_Stipple':0.,'WS_ScratchAmount':0.,'WS_EdgeWear':.025,
    'WS_EdgeHighlight':.060,'WS_CavityDarken':.025,'WS_CavityRoughness':.018,
    'WS_EdgeRoughness':max(.28,rough-.065),'SVD_MicroScratchStrength':.12,
    'R03_SourceNormalStrength':.92,'R03_EdgeNormalStrength':.70,'R03_DielectricFinish':0.}
 if 'Recess' in name:s.update(WS_EdgeWear=.01,WS_EdgeHighlight=.025)
 if category=='moving steel':s.update(WS_GrainRoughness=.009,WS_EdgeHighlight=.050)
 if key=='SVD' and name in ('SM_SVD_Body_001','SVD_FactoryStock'):s['R03_DielectricFinish']=1.
 if magazine:
  s.update(WS_GrainRoughness=.009,WS_MottleRoughness=.004,WS_EdgeHighlight=.055,
   MagazineRibHeightMM=.06,MagazineRibRadiusMM=2.,MagazineUVToMM=352.,R03_SourceNormalStrength=1.)
 t.update(category=category,magazine=magazine,scalars=s,
  vectors={'WS_FinishColor':color,'WS_EdgeColor':[v*1.7 for v in color]},normal=normals.get((key,name)))
recipe={'version':'SVD-Refine03-20261001','targets':targets,'textures':bakes,
 'principle':'fine satin hierarchy; preserved markings, polymer, rubber and optical identity; wetness remains last',
 'tested':False}
(O/'recipe.json').write_text(json.dumps(recipe,indent=1))
