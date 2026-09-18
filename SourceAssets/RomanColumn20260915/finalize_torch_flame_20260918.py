"""收尾：保存项目自己的 NS_TorchFlame、把 6 支火把指过去、降灯亮度，并抓一张对照图。

NS_TorchFlame = Vefects NS_Fire_Small 的项目内副本，改动：两个火焰发射器 ScaleSpriteSize 的
Uniform Curve Scale 1 -> 0.3（火苗缩到 30%）；移除自带 NE_Lights（光照交给我方可调、受点火曲线控制的点光）。
"""

import os
import time

import unreal

OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
# 注意：NS_TorchFlame（项目副本，已把两个火焰发射器的 Uniform Curve Scale 降到 0.3、删掉 NE_Lights）
# 目前**不出火**——改过堆栈的系统需要 Niagara 重新编译，这一步还没打通，因此先指回 pack 原系统。
FLAME = "/Game/Vefects/Free_Fire/Shared/Particles/NS_Fire_Small"
LUMENS = 600.0


def log(m):
    print("[fin] " + m)


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

flame_asset = unreal.EditorAssetLibrary.load_asset(FLAME)
if not flame_asset:
    raise RuntimeError("missing %s" % FLAME)
saved = unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(FLAME)], False)
log("system saved=%s" % saved)

torches = sorted([a for a in sub.get_all_level_actors() if a.get_actor_label().startswith("ColonnadeTorch_")],
                 key=lambda a: a.get_actor_label())
for a in torches:
    for name in ("FlameSystem", "flame_system"):
        try:
            a.set_editor_property(name, flame_asset)
            break
        except Exception:  # noqa: BLE001
            continue
    for name in ("LightLumens", "light_lumens"):
        try:
            a.set_editor_property(name, LUMENS)
            break
        except Exception:  # noqa: BLE001
            continue
    comp = a.get_component_by_class(unreal.NiagaraComponent)
    if comp:
        comp.set_asset(flame_asset)
        comp.set_relative_location(unreal.Vector(50.0, 0.0, 36.0), False, False)
log("retargeted %d torches to NS_TorchFlame, light=%.0f lm" % (len(torches), LUMENS))
log("map save=%s" % unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level())

# 单张对照图：编辑器里手点火 + 手点灯（运行时由时钟驱动），拍完还原、不再保存。
torch = torches[0]
flame = torch.get_component_by_class(unreal.NiagaraComponent)
light = torch.get_component_by_class(unreal.PointLightComponent)
if flame:
    flame.activate(True)
if light:
    light.set_intensity(LUMENS)
    light.set_visibility(True)
time.sleep(2.0)

rt = unreal.RenderingLibrary.create_render_target2d(
    world, 768, 768, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB, unreal.LinearColor(0, 0, 0, 1), False)
cap = sub.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(600.0, 380.0, 240.0),
                                 unreal.Rotator(0.0, -4.0, 90.0))
c = cap.get_component_by_class(unreal.SceneCaptureComponent2D)
c.set_editor_property("texture_target", rt)
c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
c.set_editor_property("projection_type", unreal.CameraProjectionMode.PERSPECTIVE)
c.set_editor_property("fov_angle", 48.0)
for _ in range(3):
    c.capture_scene()
    time.sleep(0.6)
unreal.RenderingLibrary.export_render_target(world, rt, OUT, "torch_flame_final.png")
path = os.path.join(OUT, "torch_flame_final.png")
log("shot %s (%d B)" % (os.path.exists(path), os.path.getsize(path) if os.path.exists(path) else 0))
cap.destroy_actor()
unreal.RenderingLibrary.release_render_target2d(rt)

if light:
    light.set_intensity(0.0)
    light.set_visibility(False)
if flame:
    flame.deactivate()
log("restored; DONE")
