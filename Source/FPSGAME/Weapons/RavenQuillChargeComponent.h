#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "RavenQuillChargeComponent.generated.h"

class UStaticMeshComponent;
struct FColdSteelItem;
struct FColdSteelSkillShot;

USTRUCT()
struct FRavenQuillCharge
{
    GENERATED_BODY()
    UPROPERTY() float BankedSeconds=0.f;
    UPROPERTY() double RunStartedAt=-1.;
    UPROPERTY() double ReadyUntil=-1.;
};

/** The server owns sprint time and hit consumption. Clients animate between clock transitions. */
UCLASS()
class FPSGAME_API URavenQuillChargeComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    URavenQuillChargeComponent();
    void Equip(const FColdSteelItem* Item);
    bool IsInstalled() const { return !Weapon.IsEmpty(); }
    bool IsMovingSprint() const;
    bool Matches(const FColdSteelSkillShot& Shot) const;
    float ContactBonus(const FColdSteelSkillShot& Shot);
    static void BindGuard(UStaticMeshComponent* Mesh);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Charge) FRavenQuillCharge Charge;
    UFUNCTION() void OnRep_Charge();
    FString Weapon;
    TArray<uint64,TInlineAllocator<8>> EmpoweredAttacks;
    TArray<TWeakObjectPtr<UStaticMeshComponent>> Guards;
    float LastGlow=-1.f;
    double Clock() const;
    bool AdvanceDeadlines(double Now);
    void Present(double Now);
    float Progress(double Now) const;
};

