"""判断 SceneCapture 导出是否真的在更新：从 1 号火把的**另一侧**拍一张（不保存任何东西）。"""

import os
import time

import unreal

OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
torch = [a for a in sub.get_all_level_actors() if a.get_actor_label() == "ColonnadeTorch_01"][0]
flame = torch.get_component_by_class(unreal.NiagaraComponent)
if flame:
    print("[cl] asset=%s active=%s" % (flame.get_editor_property("asset").get_name(), flame.is_active()))
    flame.activate(True)          # 只激活，不重设资产：上一版 set_asset() 后立刻 activate() 不出粒子
    time.sleep(2.0)
    print("[cl] after activate: active=%s" % flame.is_active())
light = torch.get_component_by_class(unreal.PointLightComponent)
if light:                          # 编辑器里没有 BeginPlay/Tick，手动点灯；拍完还原（不保存）
    light.set_intensity(600.0)
    light.set_visibility(True)
    time.sleep(1.0)

rt = unreal.RenderingLibrary.create_render_target2d(
    world, 768, 768, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB, unreal.LinearColor(0, 0, 0, 1), False)
# 正视火把（从 -Y 一侧看 +Y）。
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
unreal.RenderingLibrary.export_render_target(world, rt, OUT, "capture_backside.png")
p = os.path.join(OUT, "capture_backside.png")
print("[cl] shot=%s (%d B)" % (os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0))
cap.destroy_actor()
unreal.RenderingLibrary.release_render_target2d(rt)
if light:
    light.set_intensity(0.0)
    light.set_visibility(False)
if flame:
    flame.deactivate()
print("[cl] DONE")
