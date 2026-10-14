"""Use the accepted fixture-bound downlight treatment at reduced office output."""
REVISION='medical_office_dimmed_downlights_20261010'
FIXTURE='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_LampFixture'
# Same luminous face and downward orientation as DungeonFixtureLighting20261009.
FACE_Z_CM=-6.85
EMITTER_Z_CM=FACE_Z_CM-1.
DIRECT_SCALE=.55

def apply(module):
 if module['id']!='MedicalDoctorOffice':raise ValueError('Office lighting belongs to MedicalDoctorOffice')
 fixtures={p['id']:p for p in module['parts'] if p.get('id','').startswith('MedicalOffice.Ceiling.Lamp')}
 for light in module['lights']:
  index=light['id'].removeprefix('MedicalOffice.Light')
  part=fixtures['MedicalOffice.Ceiling.Lamp'+index]
  if part['mesh']!=FIXTURE:raise ValueError('Office fixture changed: '+part['id'])
  anchor=part['position'];corridor=abs(anchor[0])<.01
  # Idempotent authoring values: .25 converts point lumens to rectangular lumens;
  # .55 is the additional requested brightness reduction, after that conversion.
  original=720. if corridor else 920.
  light.update(type='rect',position=[anchor[0],anchor[1],anchor[2]+EMITTER_Z_CM],
   intensity=round(original*.25*DIRECT_SCALE,3),pitch=-90.,yaw=part.get('yaw',0),roll=90.,
   source_width_cm=116.,source_height_cm=18.,color=[.78,.88,1.],
   radius=600. if corridor else 650.,optimized_radius_cm=600. if corridor else 650.,
   cast_shadows=True,indirect_lighting_intensity=.22,volumetric_scattering_intensity=0.,
   fixture_anchor_cm=list(anchor),fixture_mesh=FIXTURE,fixture_face_center_cm=[anchor[0],anchor[1],anchor[2]+FACE_Z_CM],
   fixture_normal=[0.,0.,-1.],fixture_lighting_revision=REVISION)
  light.pop('source_radius',None);light.pop('source_length',None)
 for spec in module['runtime_actors']:
  if spec.get('type')=='post_process':
   spec.update(exposure_ev=1.2,exposure_bias=-.35,indirect_intensity=.65,bloom=.04)
 module['fixture_lighting_revision']=REVISION
 module.setdefault('authoring',{})['office_lighting']=dict(revision=REVISION,lights=len(module['lights']),
  reference='DungeonFixtureLighting20261009',direct_output_scale_after_type_conversion=DIRECT_SCALE,
  scope='MedicalDoctorOffice only',exposure_ev=1.2,exposure_bias=-.35,tests_run=False)
 return module

def set_light(component,spec):
 import unreal as u
 component.set_editor_property('intensity_units',u.LightUnits.LUMENS)
 component.set_intensity(spec['intensity']);component.set_light_color(u.LinearColor(*spec['color'],1))
 for key,value in dict(attenuation_radius=spec['radius'],cast_shadows=spec['cast_shadows'],
  indirect_lighting_intensity=spec['indirect_lighting_intensity'],volumetric_scattering_intensity=spec['volumetric_scattering_intensity'],
  max_draw_distance=spec['max_draw_distance_cm'],max_distance_fade_range=spec['fade_range_cm'],
  source_width=spec['source_width_cm'],source_height=spec['source_height_cm']).items():component.set_editor_property(key,value)

def set_exposure(component,spec):
 settings=component.get_editor_property('settings')
 for key,value in dict(auto_exposure_min_brightness=spec['exposure_ev'],auto_exposure_max_brightness=spec['exposure_ev'],
  auto_exposure_bias=spec['exposure_bias'],indirect_lighting_intensity=spec['indirect_intensity'],bloom_intensity=spec['bloom']).items():
  settings.set_editor_property('override_'+key,True);settings.set_editor_property(key,value)
 component.set_editor_property('settings',settings)
