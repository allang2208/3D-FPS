"""Read the active fireball combustion authoring inputs; no playback or tests."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/MeteorFireballImpact20261115'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters

source=u.load_asset('/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic')
record={'source':source.get_path_name(),'emitters':{},'material':{}}
for name in ('ContactIgnition','OutwardCombustion'):
    row={'renderer':json.loads(API.call_method('GetRendererData',(ref(source,name,renderer=0),)).get_editor_property('property_values'))}
    for script in ('ParticleSpawnScript','ParticleUpdateScript'):
        row[script+'_stack']=[value.export_text() for value in API.call_method('GetScriptStackInputValues',(ref(source,name,script),))]
        module=u.EditorAssetLibrary.get_metadata_tag(source,'Fireball.Assignments.'+name+'.'+script)
        attributes=['Particles.Position','Particles.SpriteSize','Particles.Color','Particles.SubImageIndex','Particles.SpriteRotation']
        if script=='ParticleSpawnScript':attributes.append('Particles.Lifetime')
        row[script]={key:u.RainAssetEditor.read_input(source,name,script,module,key) for key in attributes}
    row['burst']={key:u.RainAssetEditor.read_input(source,name,'EmitterUpdateScript','SpawnBurst_Instantaneous',key)
                  for key in ('Spawn Count','Spawn Time')}
    record['emitters'][name]=row
material=u.load_asset('/Game/Skills/Fireball/ImpactRealistic20260914/MI_ImpactCombustion')
record['material']['path']=material.get_path_name()
record['material']['parent']=material.get_editor_property('parent').get_path_name()
record['material']['scalars']={str(key):LIB.get_material_instance_scalar_parameter_value(material,key)
                               for key in LIB.get_scalar_parameter_names(material)}
record['material']['textures']={str(key):str(LIB.get_material_instance_texture_parameter_value(material,key))
                                for key in LIB.get_texture_parameter_names(material)}
target=u.load_asset('/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7/NS_MeteorPressureV7')
record['target_emitters']=emitters(target)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'fireball-donor.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print('METEOR_FIREBALL_DONOR_READ '+str(OUT/'fireball-donor.json'))
