// 一支离弦的箭：分步推进 + 球形扫掠，命中按与弹道组件同一入口结算一次伤害。
// 箭身与箭头是引擎基础图占位（与 `dev.warehousecrate` 占位件同一口径），
// 正式箭模到位后由 bows.json 的 arrow_mesh 换路径，本类不改。
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "BowArrow.generated.h"

class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

UCLASS()
class FPSGAME_API ABowArrow : public AActor
{
    GENERATED_BODY()

public:
    ABowArrow();
    /**
     * 由弓组件在生成后立刻配置。伤害与速度已经按拉距算好，箭自身不再二次换算；
     * `InShot` 是射击瞬间的修炼／符文快照，与枪械弹道共用同一结算口径。
     */
    void Configure(float InDamage, float InSpeed, float InGravityCM, float InRangeCM,
                   const FColdSteelSkillShot& InShot, UStaticMesh* InShaftMesh, UStaticMesh* InHeadMesh,
                   float InRadiusCM, float InLengthCM, const FString& InAmmoId);
    virtual void Tick(float Delta) override;

private:
    /** 命中结算：一次扫掠一个目标，命中后不再重复扣血。 */
    void ApplyHit(const FHitResult& Hit);
    /** 命中后插住：关掉碰撞、跟着被击组件（骨骼）走，到时间再消失。 */
    void FinishStuck(const FHitResult& Hit);

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shaft;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Head;

    FVector Velocity = FVector::ZeroVector;
    FColdSteelSkillShot Shot;
    FString AmmoId;
    float Speed = 0.f;
    float Damage = 0.f, GravityCM = 0.f, TravelledCM = 0.f, MaxDistanceCM = 0.f;
    float Age = 0.f, StickRemaining = 0.f;
    bool bResolved = false, bStuck = false;

    /** 单步不超过这个长度：9800 cm/s 在 30 fps 下也不会穿过薄墙。 */
    static constexpr float StepCM = 60.f;
    /** 插地／插身后停留多久再消失（秒）。 */
    static constexpr float StickSeconds = 8.f;
};
