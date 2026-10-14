"""Campfire-owned visibility revision. No vendor saves, lights, world or savegame."""
from pathlib import Path
import unreal as u
import json,sys
OUT=Path(__file__).resolve().parent
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,ref,LIB
H=getattr(u,'CampfireAssetTools',getattr(u,'RainAssetEditor',None));assert H
base='/Game/Building/Campfire20261013/TorchFire'
s=u.load_asset(base+'/NS_CampfireTorchFire');m=u.load_asset(base+'/M_CampfireTorchFire');assert s and m
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
assert not ({base+'/NS_CampfireTorchFire',base+'/M_CampfireTorchFire'}&dirty),'Preserve unsaved assets'
nodes=LIB.get_material_expressions(m)
original=next(n for n in nodes if n.get_name()=='MaterialExpressionMultiply_0')
assert isinstance(original,u.MaterialExpressionMultiply)
original.set_editor_property('const_b',.12)
def tagged(cls,tag):
    found=[n for n in LIB.get_material_expressions(m) if n.get_editor_property('desc')==tag]
    assert len(found)<=1
    n=found[0] if found else LIB.create_material_expression(m,cls)
    n.set_editor_property('desc',tag);return n
eye=tagged(u.MaterialExpressionEyeAdaptationInverse,'CampfireDaylightExposure20261013')
strength=tagged(u.MaterialExpressionConstant,'CampfireDaylightExposureStrength20261013')
strength.set_editor_property('r',1.)
names=[str(x) for x in LIB.get_material_expression_input_names(eye)]
assert LIB.connect_material_expressions(original,'',eye,names[0])
assert LIB.connect_material_expressions(strength,'',eye,next(n for n in names if 'alpha' in n.lower()))
assert LIB.connect_material_property(eye,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
LIB.recompile_material(m)
changes=[]
def put(stage,module,key,value,typ='/Script/Niagara.NiagaraFloat'):
    assert H.set_input(s,'Fire',stage,module,key,typ,value),(module,key)
    changes.append({'stage':stage,'module':module,'input':key,'readback':H.read_input(s,'Fire',stage,module,key)})
expr='/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
put('EmitterUpdateScript','SpawnRate','SpawnRate','(Value=16)')
put('ParticleUpdateScript','ScaleColor','Scale Alpha','(HlslExpression=".95*smoothstep(0.0,.08,Particles.NormalizedAge)*(1.0-smoothstep(.65,1.0,Particles.NormalizedAge))")',expr)
put('ParticleUpdateScript','DynamicMaterialParameters','Index 0 Param 1','(HlslExpression="1.15+.25*frac(float(Particles.UniqueID)*.41421356237)")',expr)
put('ParticleUpdateScript','DynamicMaterialParameters','Index 0 Param 2','(HlslExpression=".9+.4*smoothstep(.65,1.0,Particles.NormalizedAge)")',expr)
assert H.compile_rain(s)
assert u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost(),s.get_outermost()],False)
report={'system':s.get_path_name(),'material':m.get_path_name(),'changes':changes,'emissive_gain':.12,'exposure_compensation':1.,'depth_fade_cm':4.,'sprite_size_cm':[62,76],'birth_radius_cm':14,'fire_lifetime_s':[1.1,1.55],'emitter_count':3,'particle_light_renderers':0,'estimated_upper_live_particles':38,'new_lights':0,'runtime_tested':False,'visual_preview_performed':False}
(OUT/'visibility-authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CAMPFIRE_VISIBILITY_SAVED',s.get_path_name())
