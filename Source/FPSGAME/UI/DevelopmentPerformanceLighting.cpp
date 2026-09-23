#include "DevelopmentPanelWidget.h"
#include "PerformanceTextUpdate.h"
#include "Components/TextBlock.h"

void UDevelopmentPanelWidget::RefreshPerformanceLighting()
{
    if (!PerformanceLights) return;
    const auto& Snapshot = PerformanceCache;
    const auto& C = Snapshot.Coverage;
    FString Text = FString::Printf(TEXT("总数 %d · 启用且有有效亮度 %d · 其中开启阴影 %d\n点光 %d · 聚光 %d · 矩形 %d · 方向光 %d（类型为总量）"),
        C.Lights, C.EnabledLights, C.EnabledShadowLights, C.PointLights, C.SpotLights, C.RectLights, C.DirectionalLights);
    Text += FString::Printf(TEXT("\n另计天空光 %d · 有效开启 %d · 开启实时捕获标志 %d（非实际捕获次数）"),C.SkyLights,C.EnabledSkyLights,C.RealTimeSkyCaptures);
    if (Snapshot.bHasView && Snapshot.bHasProjection)
        Text += FString::Printf(TEXT("\n当前视野候选 %d · 其中阴影候选 %d · 摄像机所在球形范围重叠 %d（均为估算）"),
            C.LightViewCandidates, C.ShadowViewCandidates, C.CameraLightBounds);
    else Text += TEXT("\n视野候选：—（缺少完整视图/投影）");
    Text += TEXT("\n实际渲染灯数、局部照明/阴影/Lumen/体积雾 GPU 分段：未采集。");
    auto Setting = [&](const TCHAR* Name)
    {
        const FString* Value = Snapshot.LightingCVars.Find(Name);
        return Value ? *Value : FString(TEXT("未知"));
    };
    Text += FString::Printf(TEXT("\n设置快照：VSM=%s · 光追阴影=%s · MegaLights=%s · Lumen HWRT=%s\n地牢灯光策略=%s（下次生成应用）· 房间调度=%s"),
        *Setting(TEXT("r.Shadow.Virtual.Enable")), *Setting(TEXT("r.RayTracing.Shadows")),
        *Setting(TEXT("r.MegaLights.Enable")), *Setting(TEXT("r.Lumen.HardwareRayTracing")),
        *Setting(TEXT("fps.Dungeon.Lighting.Optimize")), *Setting(TEXT("fps.Dungeon.Lighting.RoomCulling")));
    Text += TEXT("\n设置值不能证明某个 GPU pass 实际执行；完整明细与设置写入 JSON。");
    if (Snapshot.Lights.IsEmpty()) Text += TEXT("\n当前 World 未发现局部/方向灯光组件。");
    else Text += TEXT("\n\n前 12 盏：视野候选、已开启优先，同组按距离排列。");
    for (int32 Index = 0; Index < FMath::Min(12, Snapshot.Lights.Num()); ++Index)
    {
        const auto& L = Snapshot.Lights[Index];
        const TCHAR* Type = L.Type == TEXT("Spot") ? TEXT("聚光") : L.Type == TEXT("Point") ? TEXT("点光")
            : L.Type == TEXT("Rect") ? TEXT("矩形") : L.Type == TEXT("Directional") ? TEXT("方向光") : TEXT("其它");
        const FString Distance = Snapshot.bHasView && L.bLocal ? FString::Printf(TEXT("%.1f m"), L.DistanceCm / 100.f) : TEXT("—");
        const FString Draw = L.bLocal && L.MaxDrawDistanceCm > 0
            ? FString::Printf(TEXT("%.1f m（缩放后 %.1f）"), L.MaxDrawDistanceCm / 100.f, L.EffectiveMaxDrawDistanceCm / 100.f) : TEXT("不限距离");
        const FString Room = L.Module.IsEmpty() ? TEXT("非生成模块") : L.Module;
        Text += FString::Printf(TEXT("\n%d. %s · %s · %s · %s\n%s · %s · %s\n强度 %.1f %s · 半径 %.1f m · 距离 %s · 显示 %s · 淡出 %.1f m"),
            Index + 1, *L.Label, Type, L.bEnabled ? TEXT("开启") : TEXT("关闭/零强度"),
            L.bCastShadows ? TEXT("投影开") : TEXT("投影关"), *Room, *L.Role, *L.Mobility,
            L.Intensity, *L.IntensityUnits, L.RadiusCm / 100.f, *Distance, *Draw, L.FadeRangeCm / 100.f);
    }
    SetPerformanceText(PerformanceLights, FText::FromString(Text));
}
