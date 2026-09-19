#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BronzeTorch.generated.h"

class AFPSWeatherManager;
class UMaterialInterface;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * 柱上青铜火把：青铜网格 + 火焰 Niagara + 暖色点光，**按世界时钟自动点火**。
 *
 * 组件（都挂在同一个根下，位置由下面的偏移量给出）：
 *   TorchBody  — `SM_BronzeTorch`（局部原点 = 柱轴心、托臂朝 +X，见 SourceAssets/RomanColumn20260915）。
 *   TorchFlame — 火焰系统，默认关闭；**点火时激活**，并按点火量从 0.55 长到 1.0 倍。
 *   TorchLight — 暖色点光，亮度 = 基准 × 点火量 × 闪烁（每支火把相位不同，不会整排同步闪）。
 *
 * 时钟口径与 `ATemperateHillsWorld::TickDayNightSky()`、`AFPSWeatherManager` 完全一致：
 * 一小时 = `Frac(NormalizedDayTime) * 24`，黄昏 16.5 起、夜晚 19.5 起。默认 **17:00 点火、05:30 熄灭**，
 * 用 `IgnitionBlendSeconds` 做淡入淡出，不额外维护第二套计时器，跳时/传送/午夜都不需要特殊分支。
 *
 * 关卡里没有天气管理器时（例如单独打开某张静态图），自动模式回落到 `bStartLit`，不会因为找不到时钟就永远不亮。
 * 手动接口：`SetLit()` 关闭自动模式；`SetAutomaticIgnition(true)` 交回时钟。
 */
UCLASS(Blueprintable)
class FPSGAME_API ABronzeTorch : public AActor
{
    GENERATED_BODY()

public:
    ABronzeTorch();
    virtual void Tick(float DeltaSeconds) override;

    /** 手动点火/熄灭；会同时关闭自动模式，避免下一帧被时钟改回去。 */
    UFUNCTION(BlueprintCallable, Category="Torch")
    void SetLit(bool bLit);

    /** 打开/关闭按世界时钟自动点火。打开时立刻按当前时刻求一次目标状态。 */
    UFUNCTION(BlueprintCallable, Category="Torch")
    void SetAutomaticIgnition(bool bEnabled);

    UFUNCTION(BlueprintPure, Category="Torch")
    float GetIgnitionAmount() const { return IgnitionAmount; }

    UFUNCTION(BlueprintPure, Category="Torch")
    bool IsLit() const { return IgnitionAmount > 0.5f; }

    UFUNCTION(BlueprintPure, Category="Torch")
    bool IsAutomaticIgnition() const { return bAutomaticIgnition; }

    /** 当前是否落在点火窗口内（黄昏/夜晚）。时钟不可用时返回 bStartLit。 */
    UFUNCTION(BlueprintPure, Category="Torch")
    bool ShouldBeLitNow() const;

protected:
    virtual void BeginPlay() override;
    virtual void OnConstruction(const FTransform& Transform) override;

    UPROPERTY(VisibleAnywhere, Category="Torch")
    TObjectPtr<USceneComponent> SceneRoot;

    UPROPERTY(VisibleAnywhere, Category="Torch")
    TObjectPtr<UStaticMeshComponent> TorchBody;

    UPROPERTY(VisibleAnywhere, Category="Torch")
    TObjectPtr<UNiagaraComponent> TorchFlame;

    UPROPERTY(VisibleAnywhere, Category="Torch")
    TObjectPtr<UPointLightComponent> TorchLight;

    /** 默认 `SM_BronzeTorch`；换网格时保持局部原点在柱轴心、托臂朝 +X。 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Torch|Body")
    TObjectPtr<UStaticMesh> BodyMesh;

    /** 默认 `M_Bronze`（光滑青铜）。留空则用网格自带材质。 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Torch|Body")
    TObjectPtr<UMaterialInterface> BodyMaterial;

    /** 火焰系统；留空则只有点光（可在编辑器里换成别的火）。 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Torch|Flame")
    TObjectPtr<UNiagaraSystem> FlameSystem;

    UPROPERTY(EditAnywhere, Category="Torch|Flame")
    bool bEnableFlame = true;

    UPROPERTY(EditAnywhere, Category="Torch|Flame")
    bool bEnableLight = true;

    /**
     * 火焰相对火把网格原点的位置（本地坐标）。杯口在 z≈42.6、杯腔深约 27 cm：
     * 原点必须靠近**杯口**，否则火苗会整个埋进杯腔里看不见（只剩灯）。
     */
    UPROPERTY(EditAnywhere, Category="Torch|Flame")
    FVector FlameOffset = FVector(50.0f, 0.0f, 36.0f);

    /** 火焰整体缩放，按点火量从 `FlameIgnitionScaleFloor` 长到 1.0 倍。 */
    UPROPERTY(EditAnywhere, Category="Torch|Flame")
    float FlameScale = 0.5f;

    UPROPERTY(EditAnywhere, Category="Torch|Flame", meta=(ClampMin="0.0", ClampMax="1.0"))
    float FlameIgnitionScaleFloor = 0.55f;

    UPROPERTY(EditAnywhere, Category="Torch|Light")
    FVector LightOffset = FVector(50.0f, 0.0f, 52.0f);

    UPROPERTY(EditAnywhere, Category="Torch|Light")
    float LightLumens = 350.0f;

    UPROPERTY(EditAnywhere, Category="Torch|Light")
    float LightRadiusCm = 500.0f;

    UPROPERTY(EditAnywhere, Category="Torch|Light")
    FLinearColor LightColor = FLinearColor(1.0f, 0.60f, 0.26f);

    /** 默认关：6 支阴影点光会各占一张立方体阴影图。需要夜里的投影时逐支打开。 */
    UPROPERTY(EditAnywhere, Category="Torch|Light")
    bool bLightCastsShadows = false;

    UPROPERTY(EditAnywhere, Category="Torch|Light", meta=(ClampMin="0.0", ClampMax="1.0"))
    float FlickerAmplitude = 0.04f;

    UPROPERTY(EditAnywhere, Category="Torch|Light", meta=(ClampMin="0.1"))
    float FlickerFrequency = 1.5f;

    // ---------------------------------------------------------------- 自动点火
    /** 与天空自己的相位边界对齐：夕阳段 16.5 起、日出段 6.0 结束（见 TemperateHillsDayNightSky.cpp）。 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Torch|Clock", meta=(ClampMin="0.0", ClampMax="24.0"))
    float IgniteHour = 16.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Torch|Clock", meta=(ClampMin="0.0", ClampMax="24.0"))
    float ExtinguishHour = 6.0f;

    /** 淡入/淡出秒数。0 表示硬切换。 */
    UPROPERTY(EditAnywhere, Category="Torch|Clock", meta=(ClampMin="0.0"))
    float IgnitionBlendSeconds = 6.0f;

    /** 关卡里没有天气管理器时的兜底状态。 */
    UPROPERTY(EditAnywhere, Category="Torch|Clock")
    bool bStartLit = false;

    /** 点火状态翻转时打一行 `TORCH_STATE`，方便对着日志核对黄昏/夜晚是否生效。 */
    UPROPERTY(EditAnywhere, Category="Torch|Clock")
    bool bLogStateChanges = true;

private:
    UPROPERTY(VisibleAnywhere, Category="Torch|Clock")
    bool bAutomaticIgnition = true;

    UPROPERTY(VisibleAnywhere, Category="Torch|Clock")
    bool bLitOverride = false;

    UPROPERTY(VisibleAnywhere, Category="Torch|Clock")
    float IgnitionAmount = 0.0f;

    TWeakObjectPtr<AFPSWeatherManager> WeatherManager;
    float FlickerPhase = 0.0f;
    float ClockRefreshCountdown = 0.0f;
    float CachedHour = 12.0f;
    bool bCachedClockValid = false;
    bool bLastReportedLit = false;
    bool bHasReported = false;

    AFPSWeatherManager* ResolveWeatherManager();
    void RefreshClock(float DeltaSeconds);
    void ApplyVisuals(float DeltaSeconds);
    void ApplyComponentOffsets();
};
