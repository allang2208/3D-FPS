// 一支离弦的箭：分步推进 + 球形扫掠，命中按与弹道组件同一入口结算一次伤害。
// 箭模复用弦上箭部件。命中后的实弹箭靠近自动回收到弹药袋，也保留 E 拾取。
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TimerManager.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "BowArrow.generated.h"

class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UCapsuleComponent;
class USphereComponent;
class UPrimitiveComponent;

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
                   float InRadiusCM, float InLengthCM, const FString& InAmmoId,
                   bool bInRecoverable, float InRecoverySeconds);
    virtual void Tick(float Delta) override;
    void ResolveLaunchObstruction(const FVector& CameraOrigin);
    bool CanRecover() const { return bStuck && bRecoverable && !IsActorBeingDestroyed(); }
    FString RecoveryPrompt() const;
    bool TryRecover(APawn* Pawn);
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    /** 命中结算：一次扫掠一个目标，命中后不再重复扣血。 */
    void ApplyHit(const FHitResult& Hit);
    /** 命中后插住：只留实弹箭的拾取查询，随被击组件移动，超时消失。 */
    void FinishStuck(const FHitResult& Hit);

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shaft;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Head;

    FVector Velocity = FVector::ZeroVector;
    FColdSteelSkillShot Shot;
    FString AmmoId;
    float Speed = 0.f;
    float Damage = 0.f, GravityCM = 0.f, TravelledCM = 0.f, MaxDistanceCM = 0.f;
    float Age = 0.f;
    bool bResolved = false, bStuck = false;

    /** 单步不超过这个长度：9800 cm/s 在 30 fps 下也不会穿过薄墙。 */
    static constexpr float StepCM = 60.f;
    /** 无限备弹箭短暂保留，靠近可收走，但不返还真实库存。 */
    static constexpr float StickSeconds = 8.f;
    float CollisionRadiusCM = .35f;
    // Overlaps only: the E trace sees this shape, weapon blocking traces do not.
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> RecoveryShape;
    bool bRecoverable = false;
    float RecoverySeconds = 120.f;
    FString RecoveryCaption;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> AutoRecovery;
    FTimerHandle RecoveryTimer;
    UFUNCTION() void OnRecoveryOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
        UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex,bool bFromSweep,const FHitResult& SweepResult);
    UFUNCTION() void OnRecoveryEndOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
        UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex);
    void RecoverNearby();
    bool RecoverIntoPouch(APawn* Pawn);
};
