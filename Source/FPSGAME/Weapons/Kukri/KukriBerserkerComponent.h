#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "KukriBerserkerComponent.generated.h"

class UColdSteelStatusModel;
class UAzureDragonEnergyComponent;
class UKukriBerserkerVFXComponent;
struct FColdSteelItem;
struct FColdSteelSkillShot;

USTRUCT()
struct FKukriBerserkerState
{
    GENERATED_BODY()
    UPROPERTY() TArray<FString> Instances;
    UPROPERTY() FString EquipmentKey;
    UPROPERTY() uint32 EquipmentRevision=0;
    UPROPERTY() int32 Charge=0;
    UPROPERTY() double EndsAt=0.;
};

/** Both equipped berserker knives share one authority-owned charge and duration. */
UCLASS()
class FPSGAME_API UKukriBerserkerComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UKukriBerserkerComponent();
    void Configure(const UColdSteelStatusModel* Model);
    void ConfirmHit(const FColdSteelSkillShot& Shot,float AppliedDamage);
    static bool Installed(const FColdSteelItem& Item);
    static bool Active(const FColdSteelItem* Item,const UColdSteelStatusModel* Model);
    static float CostMultiplier(const FColdSteelItem* Item,const UColdSteelStatusModel* Model);
    static float DamageMultiplier(const FColdSteelItem* Item,const UColdSteelStatusModel* Model);
    static float MovementMultiplier(const AActor* Actor);
    float Remaining() const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class UKukriNetworkAuditCommandlet;
    double Clock() const;
    bool MatchesEquipment() const;
    void Present();
    UFUNCTION() void OnRep_State();
    UPROPERTY(ReplicatedUsing=OnRep_State) FKukriBerserkerState State;
    UPROPERTY(Transient) TObjectPtr<UAzureDragonEnergyComponent> Hud;
    UPROPERTY(Transient) TObjectPtr<UKukriBerserkerVFXComponent> ActiveVFX;
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    TArray<FString> EquippedInstances;
    FString EquippedKey;
    uint32 RequiredEquipmentRevision=0;
    bool bEquipmentConfigured=false;
    TArray<uint32> RecentAttacks;
    int32 ShownCharge=-1;
    double ShownActivation=0.;
};
