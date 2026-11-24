#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "EagleTalonGuardComponent.generated.h"

class UColdSteelStatusModel;
class UStaticMeshComponent;
struct FColdSteelItem;
struct FColdSteelNetHitReport;

enum class EEagleStrike : uint8 { Ordinary, Heavy, Quick, Uppercut, Whirlwind };

USTRUCT()
struct FEagleGuardCharge
{
    GENERATED_BODY()
    UPROPERTY() FString Weapon;
    UPROPERTY() uint8 Blocks=0;
};

UCLASS()
class FPSGAME_API UEagleTalonGuardComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UEagleTalonGuardComponent();
    void Equip(const UColdSteelStatusModel* Profile);
    void ClearCharge();
    void Defended(const FString& Weapon,AActor* Attacker,bool Parried);
    static bool Installed(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile);
    static bool Ready(const UColdSteelStatusModel* Profile,const FColdSteelItem* Item);
    static bool Ready(const UColdSteelStatusModel* Profile);
    // Called after the action has passed its existing resource and ability gates.
    static bool Commit(AActor* Owner,const FString& Weapon,EEagleStrike Kind=EEagleStrike::Ordinary,uint32 Serial=0);
    static bool WasEmpowered(const AActor* Owner,const FString& Weapon,EEagleStrike Kind,uint32 Serial);
    static uint64 ReportAttackKey(const FColdSteelNetHitReport& Report);
    static uint64 AttackKey(EEagleStrike Kind,uint32 Serial);
    static bool ReportEmpowered(const AActor* Owner,const FColdSteelNetHitReport& Report);
    static bool IsEagleMesh(const UStaticMeshComponent* Part);
    static void BindGuard(UStaticMeshComponent* Mesh);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(ReplicatedUsing=Present) FEagleGuardCharge Charge;
    UFUNCTION() void Present();
    TArray<TWeakObjectPtr<UStaticMeshComponent>> Guards;
    TArray<uint64> EmpoweredReceipts;
};
