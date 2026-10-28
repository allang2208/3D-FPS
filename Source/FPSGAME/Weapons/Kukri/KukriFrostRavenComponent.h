#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "KukriFrostRavenComponent.generated.h"

class UColdSteelStatusModel;
class UAzureDragonEnergyComponent;
class UKukriBerserkerVFXComponent;
struct FColdSteelItem;
struct FColdSteelSkillShot;

USTRUCT()
struct FKukriFrostRavenState
{
    GENERATED_BODY()
    UPROPERTY() TArray<FString> Instances;
    UPROPERTY() FString EquipmentKey;
    UPROPERTY() uint32 EquipmentRevision=0;
    UPROPERTY() int32 Charge=0;
    UPROPERTY() double EndsAt=0.;
};

/** Shared charge for equipped raven knives; each successful swing chills each victim once. */
UCLASS()
class FPSGAME_API UKukriFrostRavenComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UKukriFrostRavenComponent();
    void Configure(const UColdSteelStatusModel* Model);
    void ConfirmHit(const FColdSteelSkillShot& Shot,AActor* Victim,float AppliedDamage);
    static bool Installed(const FColdSteelItem& Item);
    static float ToughnessMultiplier(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model);
    float Remaining() const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class UKukriNetworkAuditCommandlet;
    struct FAttackContact
    {
        uint32 Serial=0;
        bool bAwakened=false;
        TSet<TWeakObjectPtr<AActor>> Victims;
    };
    double Clock() const;
    bool MatchesEquipment() const;
    bool Eligible(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model) const;
    void Present();
    UFUNCTION() void OnRep_State();
    UPROPERTY(ReplicatedUsing=OnRep_State) FKukriFrostRavenState State;
    UPROPERTY(Transient) TObjectPtr<UAzureDragonEnergyComponent> Hud;
    UPROPERTY(Transient) TObjectPtr<UKukriBerserkerVFXComponent> ActiveVFX;
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    TArray<FString> EquippedInstances;
    FString EquippedKey;
    uint32 RequiredEquipmentRevision=0;
    bool bEquipmentConfigured=false;
    TArray<FAttackContact> RecentAttacks;
    int32 ShownCharge=-1;
    double ShownActivation=0.;
};
