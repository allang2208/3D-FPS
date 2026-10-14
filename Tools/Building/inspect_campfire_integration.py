"""User-requested static integration readback. No actor spawning, world simulation or rendering."""
from pathlib import Path
import json
import sys
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
sys.path.insert(0,str(root/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters

system_path='/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire'
system=u.find_object(None,system_path+'.NS_CampfireTorchFire')
cls=u.load_class(None,'/Script/FPSGAME.ColdSteelCampfire')
assert system and cls,'Native class startup did not load the saved flame system'
cdo=u.get_default_object(cls)
source=(root/'Source/FPSGAME/Building/ColdSteelCampfire.cpp').read_text(encoding='utf-8-sig')
header=(root/'Source/FPSGAME/Building/ColdSteelCampfire.h').read_text(encoding='utf-8-sig')
assert system.get_path_name() in source,'Native constructor path does not match the saved flame'
assert 'bool bFuelBurning=false' in header and 'bool bExtinguished=false' in header
sphere=u.find_object(cdo,'WarmthQuery')
assert sphere,'Native warmth query subobject is missing'
radius=sphere.get_editor_property('sphere_radius')
assert abs(radius-500)<.01

palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entries=[e for e in palette.get_editor_property('components') if str(e.id)=='campfire']
assert len(entries)==1,'Expected exactly one registered campfire'
entry=entries[0]
actor=entry.get_editor_property('actor_class')
actor_path=actor.get_path_name() if hasattr(actor,'get_path_name') else str(actor)
assert 'ColdSteelCampfire' in actor_path
assert str(entry.get_editor_property('material')) in ('None',''),'Campfire must remain in the Other menu'
assert str(entry.get_editor_property('display_name'))=='篝火'

names=emitters(system)
expected_materials={
    'Fire':'/Game/Building/Campfire20261013/TorchFire/M_CampfireTorchFire.M_CampfireTorchFire',
    'Smoke':'/Game/Building/Campfire20261013/TorchFire/M_CampfireTorchSmoke.M_CampfireTorchSmoke',
    'Sparks':'/Game/TorchFire/Material/M_Spark.M_Spark',
}
assert set(names)==set(expected_materials),names
materials=[]
for name in names:
    data=json.loads(API.call_method('GetRendererData',(ref(system,name,renderer=0),)).get_editor_property('property_values'))
    path=data['Material'];path=path['refPath'] if isinstance(path,dict) else path
    assert path==expected_materials[name],path
    mat=u.load_asset(path)
    assert mat,path
    if name!='Sparks':
        assert mat.get_base_material().get_editor_property('refraction_method')==u.RefractionMode.RM_NONE
    materials.append(path)
recipes=json.loads((root/'Content/ColdSteelData/campfire-recipes.json').read_text(encoding='utf-8'))['recipes']
report={
    'static_readback_passed':True,'native_class':cls.get_path_name(),'startup_loaded_flame':system.get_path_name(),
    'radius_cm':radius,'default_fuel_burning_source':False,'palette_campfire_entries':len(entries),
    'palette_name':str(entry.get_editor_property('display_name')),'palette_class':actor_path,
    'menu_material':str(entry.get_editor_property('material')),'emitters':names,'materials':materials,
    'fire_and_smoke_refraction_disabled':True,'cooking_recipes':len(recipes),
    'cooking_recipe_outputs':[r['output']['item'] for r in recipes if r.get('enabled',True)],
    'game_or_pie_started':False,'actor_spawned':False,'assets_modified':False,
}
(root/'SourceAssets/Campfire20261013/Relay/static-integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CAMPFIRE_STATIC_INTEGRATION_OK',json.dumps(report,ensure_ascii=True))
