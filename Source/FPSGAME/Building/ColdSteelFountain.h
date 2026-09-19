#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelFountain.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UNiagaraComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class USoundBase;
class UAudioComponent;

/**
 * 罗马喷泉（蛋糕塔）的**逻辑构件**：面板构件与关卡实例共用这一个类，两处水效一致。
 *
 * 组件：
 *   FountainMesh — 主体石材与碰撞；slot1 的旧平面水已隐藏。
 *   WaterFxMesh  — 保留现有泡沫 / 湿膜 / 焦散，组件槽 2 隐藏旧的固定水帘。
 *   CascadeMesh  — V7 单层几何 + V8 随流传播的随机水束/缺口，30–40 m 渐退细噪声。
 *   LandingSpray — V8 单个 GPU 系统，出生时随机小簇/速度/大小，随后解析轨迹，无场景碰撞。
 *   WaterMesh    — `SM_RomanFountain_WaterWaves`（3 个密集网格水面盘，会真实起伏/不规则波动）；
 *                  **永远可见**（远处也只关水膜/水柱，不关水面）。主网格 slot1 是隐藏材质（旧平面水已剔除）。
 *   Jet          — 引擎模板 `FountainLightweight`（塔尖水柱），位置由包围盒算出来（pivot 不在中心也对）。
 *
 * 占格不变（48×48×36），存档字段不变（Id/Cell/Yaw/Footprint）；只在"逻辑构件"分支被生成。
 *
 * 质量 0 = 仅盆水；1/2 = 默认/较密飞沫。20/40/62 m 分级，盆水始终保留。
 * 每个世界最多 4 座近处可见喷泉运行附加飞沫，统一每 0.25 s 排序。
 */
UCLASS()
class FPSGAME_API AColdSteelFountain : public AActor
{
    GENERATED_BODY()
public:
    AColdSteelFountain();
    virtual void Tick(float DeltaSeconds) override;

    /** 放置时由建造系统写入材质：只覆盖主网格 slot0（大理石），水／泡沫槽保持自己的材质实例。 */
    void Configure(UMaterialInterface* Surface);
    /** 按主网格包围盒把网格贴地、并把水柱放到塔尖（与门的 AlignGeometry 同一口径）。 */
    void AlignGeometry();
    /** 读 `fps.Fountain.Quality` 并应用（切换后 0.25 s 内生效）。 */
    UFUNCTION(BlueprintCallable, Category="Fountain") void ApplyFxQuality();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> FountainMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> WaterFxMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> WaterMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> CascadeMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Jet;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> LandingSpray;
    UPROPERTY() TObjectPtr<UMaterialInterface> CascadeNearMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> CascadeFarMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> HiddenCascadeMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CascadeNearInstance;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CascadeFarInstance;

    UPROPERTY(EditAnywhere, Category="Fountain|Perf") float NearDetailDistanceCm=2000.f;
    UPROPERTY(EditAnywhere, Category="Fountain|Perf") float SprayEndDistanceCm=4000.f;
    /** 距离分级阈值（cm）：超过该距离只留水面材质（关水效网格与水柱）。 */
    UPROPERTY(EditAnywhere, Category="Fountain|Perf") float MidJetDistanceCm=6200.f;

    /** V9 两层持续循环水声；旧间隔 / SplashCues 字段只保留序列化兼容。 */
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") bool bEnableAudio=true;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioRadiusCm=3200.f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioMinInterval=1.4f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioMaxInterval=3.2f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioVolume=0.5f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioHeightCm=120.f;
    UPROPERTY(VisibleAnywhere, Category="Fountain|Audio") TArray<TObjectPtr<USoundBase>> SplashCues;

private:
    float AudioCountdown=0.f;
    int32 CachedQuality=INDEX_NONE;
    int32 CachedTier=INDEX_NONE;
    bool bSprayBudgetGranted=false;
    float CachedSprayRate=-1.f;
    /** 0=近景；1=飞沫递减；2=简化水帘；3=仅盆水。 */
    int32 ComputeTier() const;
    void ApplyTier(int32 Tier);
    void SetSprayBudget(bool bGranted, float DistanceCm);
    static void RefreshSprayBudgets(UWorld* World);

    // Append new reflected state: existing actor fields retain their layout.
    UPROPERTY(VisibleAnywhere, Category="Fountain|Audio") TObjectPtr<UAudioComponent> WaterLoop;
    UPROPERTY(VisibleAnywhere, Category="Fountain|Audio") TObjectPtr<UAudioComponent> CloseWaterLoop;
    UPROPERTY() TObjectPtr<UMaterialInterface> PolishedStoneMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> OriginalStoneMaterial;
    bool bBedLoopWanted=false;
    bool bDetailLoopWanted=false;
    double NextBedLoopAttempt=0.;
    double NextDetailLoopAttempt=0.;
    void InitializeLoopAudio();
    void UpdateLoopAudio();
    UPROPERTY() TObjectPtr<UStaticMesh> PolishedFountainMesh;
};
