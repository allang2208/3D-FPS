#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "KukriWeaponComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class UKukriArmsMeshComponent;
class UStaticMeshComponent;
class USceneComponent;
class UAnimSequence;
class USoundBase;
class UColdSteelStatusModel;

/**
 * 尼泊尔弯刀：单手近战（主手，副手可空或持枪／魔法书）。
 * 库存拥有装备实例；本组件只负责第一人称视模、拔刀／待机／走／跑与两段横挥（右→左、左→右），
 * 以及挥砍命中（出手冻结伤害与攻速，命中窗内逐子步扫掠，每挥目标去重）、挥刀镜头曲线与命中顿帧。
 */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UKukriWeaponComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UKukriWeaponComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;

    static bool IsKukri(const struct FColdSteelItem& Item);
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    UFUNCTION(BlueprintPure, Category="Kukri") bool IsEquipped() const { return !InstanceId.IsEmpty(); }
    UFUNCTION(BlueprintPure, Category="Kukri") bool IsBusy() const { return bAttacking||bEquipping; }
    bool IsEquipping() const { return bEquipping; }
    bool IsAttacking() const { return bAttacking; }
    void BeginPrimaryAttack();
    void CancelAction();
    UKukriArmsMeshComponent* ArmsMesh() const { return Viewmodel; }
    /** 挥刀镜头曲线 + 命中抖动（相对相机）；FovDelta 为垂直视场增量（度）。供角色相机更新读取。 */
    void GetCameraMotion(FVector& Location,FRotator& Rotation,float& FovDelta) const;
private:
    /** 视模呈现父节点的命中冲击（不改相机）。 */
    FRotator ViewmodelKick() const;
    AFPSGAMECharacter* Pawn() const;
    bool CanPresent() const;
    bool CanUse() const;
    void InitializePresentation();
    void SetClip(FName Name,bool bLoop,float Blend);
    void SamplePose(float Time);
    void StartAttack(int32 NewStage);
    void AdvanceAttack(float Delta);
    void TraceBlade(const FTransform& From,const FTransform& To);
    void ConfirmImpact(const FHitResult& Hit,bool bWorld);
    FName LocomotionClip() const;
    FTransform BladeFrame() const;

    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> JumpRoot;
    UPROPERTY(Transient) TObjectPtr<UKukriArmsMeshComponent> Viewmodel;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Animations;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentAnimation;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> PommelHitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> WallSound;

    FString InstanceId;
    FName CurrentClip;
    float Elapsed=0.f;          // author seconds on the current clip
    bool bAttacking=false, bEquipping=false, bQueued=false;
    bool bSwingPlayed=false, bImpactConfirmed=false, bWallHit=false;
    float PlayRate=1.f;         // frozen per swing
    int32 Stage=0;              // 0 = right->left sweep, 1 = left->right backhand
    FRotator CameraCarry=FRotator::ZeroRotator;   // previous stage's camera offset blended out on a chain
    float CameraCarryFov=0.f, CameraCarryAge=-1.f;
    float SwingDamage=0.f, Reach=150.f;
    float HitStop=0.f, ImpactAge=-1.f, ImpactKick=0.f;
    FColdSteelSkillShot Shot;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    FTransform PreviousBlade;
    bool bHavePreviousBlade=false;
};
