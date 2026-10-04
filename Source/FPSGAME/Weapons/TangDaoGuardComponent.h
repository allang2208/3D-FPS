#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GunsmithSystem.h"
#include "TangDaoGuardComponent.generated.h"

class UColdSteelStatusModel;
struct FColdSteelSkillShot;

/** Equipped Tang Dao guard effects. Configuration changes are pushed by the profile;
 * proc state is owned by the server and replicated only to the owning player. */
UCLASS()
class FPSGAME_API UTangDaoGuardComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTangDaoGuardComponent();
    void Configure(const UColdSteelStatusModel* Profile);
    void GrantDragon();
    void GrantPhoenix();
    void ClearTransient();
    static void StampBladeAttack(AActor* Owner,FColdSteelSkillShot& Shot);
    float ConsumeDragon(const FColdSteelSkillShot& Shot,float& BonusToughness);
    void ConfirmBladeHit(const FColdSteelSkillShot& Shot);
    float DamageTakenMultiplier() const;
    float DodgeStaminaMultiplier() const;
    float SprintStaminaMultiplier() const;
    float AttackStaminaMultiplier() const;
    float AttackSpeedMultiplier() const;
    float DragonRemaining() const;
    float PhoenixRemaining() const;
    float DragonDuration() const {return Modifiers.DragonSeconds;}
    float PhoenixDuration() const {return Modifiers.PhoenixSeconds;}
    int32 PhoenixHitsRemaining() const {return PhoenixRemaining()>0.f?PhoenixHits:0;}
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    bool IsActive() const;
    bool IsBladeHit(const FColdSteelSkillShot& Shot) const;
    double Clock() const;
    UFUNCTION() void OnRep_Proc();
    void Publish();
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    FString EquippedInstance,GuardId;
    FMeleeModifiers Modifiers;
    uint32 AttackSerial=0;
    TArray<uint32> HealedAttacks;
    double DragonReadyAt=0.,PhoenixReadyAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_Proc) FString ProcInstance;
    UPROPERTY(ReplicatedUsing=OnRep_Proc) double DragonEndsAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_Proc) double PhoenixEndsAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_Proc) int32 PhoenixHits=0;
};
