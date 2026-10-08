"""Temporary runtime-only material/particle comparison. Does not edit a profile or map."""
from pathlib import Path
import unreal as u
import builtins
OUT=Path(__file__).resolve().parent
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not w:raise RuntimeError('PIE required')
def spawn(cls,location,rotation=u.Rotator()):
    transform=u.Transform(location=location,rotation=rotation)
    api=u.get_default_object(u.GameplayStatics)
    a=api.call_method('BeginDeferredActorSpawnFromClass',(w,cls,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    return api.call_method('FinishSpawningActor',(a,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
print('MESH_API '+str([n for n in dir(u.DynamicMeshActor) if 'mesh' in n]))
base=u.Vector(-1100,-400,27)
if hasattr(builtins,'zhenmo_fixture'):
    raise RuntimeError('Fixture already exists; inspect instead of spawning twice')
ground=spawn(u.DynamicMeshActor,base)
builtins.zhenmo_fixture={'world':w,'ground':ground}
comp=ground.get_component_by_class(u.DynamicMeshComponent)
mesh=comp.get_dynamic_mesh()
u.GeometryScript_Primitives.append_rectangle_xy(mesh,u.GeometryScriptPrimitiveOptions(),u.Transform(),3440,3440,8,8)
comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
comp.set_cast_shadow(False)
mat=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/SoftGroundV3/M_ZhenmoSoftGround')
mid=comp.create_dynamic_material_instance(0,mat)
mid.set_scalar_parameter_value('FieldOpacity',1)
mid.set_vector_parameter_value('FieldCenter',u.LinearColor(base.x,base.y,base.z,0))
mid.set_scalar_parameter_value('FieldRadius',1500)
fx=u.NiagaraFunctionLibrary.spawn_system_at_location(w,u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold'),base,auto_destroy=False,auto_activate=False,pre_cull_check=False)
fx.set_variable_float('User.Radius',1500)
fx.set_variable_float('User.FieldOpacity',1)
fx.activate(True)
camloc=base+u.Vector(0,-1800,2800)
camrot=u.MathLibrary.find_look_at_rotation(camloc,base)
cam=spawn(u.SceneCapture2D,camloc,camrot)
capture=cam.get_component_by_class(u.SceneCaptureComponent2D)
rt=u.RenderingLibrary.create_render_target2d(w,1280,900,u.TextureRenderTargetFormat.RTF_RGBA8)
capture.set_editor_property('texture_target',rt)
capture.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
capture.set_editor_property('capture_every_frame',False)
capture.set_editor_property('capture_on_movement',False)
capture.capture_scene()
builtins.zhenmo_fixture={'world':w,'ground':ground,'comp':comp,'mat':mat,'mid':mid,'fx':fx,'cam':cam,'capture':capture,'rt':rt,'base':base}
print('ZHENMO_FIXTURE_CREATED triangles='+str(mesh.get_triangle_count())+' particles_active='+str(fx.is_active()))
