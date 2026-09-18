#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ColdSteelFountain.generated.h"

class UStaticMeshComponent;
class UNiagaraComponent;
class UMaterialInterface;
class USoundBase;

/**
 * 罗马喷泉（蛋糕塔）的**逻辑构件**：面板构件与关卡实例共用这一个类，两处水效一致。
 *
 * 组件：
 *   FountainMesh — `SM_RomanFountain_20`（大理石 + 半透明水两槽）；它的 slot0 由建造系统按材质行覆盖，
 *                  slot1 水永远是 `MIC_FountainWater`。
 *   WaterFxMesh  — `SM_RomanFountain_WaterFX`（4 槽：泡沫 / 湿膜 / 溢流 / 焦散），挂在门口网格之下、
 *                  无碰撞、不投影。三个网格部件共用同一物体空间，所以对齐只需动 FountainMesh。
 *   Jet          — 引擎模板 `FountainLightweight`（塔尖水柱），位置由包围盒算出来（pivot 不在中心也对）。
 *
 * 占格不变（48×48×36），存档字段不变（Id/Cell/Yaw/Footprint）；只在"逻辑构件"分支被生成。
 *
 * 质量开关 `fps.Fountain.Quality`：0 = 只留主网格水面（关水膜/溢流/水柱/水声），1 = 默认，2 = 预留。
 * 距离分级（性能）：近处 = 水效网格 + 水柱 + 水花；中距 = 水效网格 + 水柱；远处 = 只留水面材质。
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

    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> FountainMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> WaterFxMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Jet;

    /** 距离分级阈值（cm）：超过该距离只留水面材质（关水效网格与水柱）。 */
    UPROPERTY(EditAnywhere, Category="Fountain|Perf") float MidJetDistanceCm=6200.f;

    /** 占位水声：工程里没有水流循环声，用户已同意先用脚步水花在近距离随机播放（见 Docs）。 */
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") bool bEnableAudio=true;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioRadiusCm=1800.f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioMinInterval=1.4f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioMaxInterval=3.2f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioVolume=0.5f;
    UPROPERTY(EditAnywhere, Category="Fountain|Audio") float AudioHeightCm=120.f;
    UPROPERTY(VisibleAnywhere, Category="Fountain|Audio") TArray<TObjectPtr<USoundBase>> SplashCues;

private:
    float AudioCountdown=0.f;
    int32 CachedQuality=INDEX_NONE;
    int32 CachedTier=INDEX_NONE;
    /** 近/中/远三档：0 = 全开，1 = 关水花，2 = 只留水面材质 */
    int32 ComputeTier() const;
    void ApplyTier(int32 Tier);
};
