#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Combat/ProgressiveInfectionComponent.h"
#include "FPSStatusReplicationComponent.generated.h"

USTRUCT()
struct FFPSStatusDisplayNet
{
    GENERATED_BODY()
    UPROPERTY() FName Type;
    UPROPERTY() double End=0.;
    UPROPERTY() float Duration=0.f;
    UPROPERTY() int32 Stacks=-1;
    UPROPERTY() int32 Battles=-1;
    UPROPERTY() bool Persistent=false;
    UPROPERTY() FString DurationText;
    UPROPERTY() FString Name;
    UPROPERTY() FString Icon;
    UPROPERTY() FLinearColor Color=FLinearColor::Transparent;
};
// Deadlines are server time, so countdowns do not produce a new packet each tick.
USTRUCT()
struct FFPSStatusNetState
{
    GENERATED_BODY()
    UPROPERTY() bool bHasCombat=false;
    UPROPERTY() bool bImmune=false;
    UPROPERTY() float ZhenmoMovement=1.f;
    UPROPERTY() FInfectionState Infection;
    UPROPERTY() double InfectedAt=0.;
    UPROPERTY() int32 PoisonStacks=0;
    UPROPERTY() double PoisonDecayAt=0.;
    UPROPERTY() TArray<double> FearExpirations;
    UPROPERTY() TObjectPtr<AActor> FearThreat=nullptr;
    UPROPERTY() TArray<FFPSStatusDisplayNet> Display;
    UPROPERTY() double ElectrifiedTime=0.;
    UPROPERTY() double ChillTime=0.;
    UPROPERTY() double FrozenTime=0.;
    UPROPERTY() double HasteTime=0.;
    UPROPERTY() double ChainTime=0.;
    UPROPERTY() double CorrosionTime=0.;
    UPROPERTY() double ShredTime=0.;
    UPROPERTY() double WardTime=0.;
    UPROPERTY() double VulnerabilityTime=0.;
    UPROPERTY() double BleedTime=0.;
    UPROPERTY() double RuneVulnerabilityTime=0.;
    UPROPERTY() double RiposteTime=0.;
    UPROPERTY() double StunTime=0.;
    UPROPERTY() double BindTime=0.;
    UPROPERTY() double SlowTime=0.;
    UPROPERTY() double WaxTime=0.;
    UPROPERTY() double WeaponHasteTime=0.;
    UPROPERTY() double PetrifyTime=0.;
    UPROPERTY() double MarkedTime=0.;
    UPROPERTY() double InspireTime=0.;
    UPROPERTY() double CamelTime=0.;
    UPROPERTY() double ImmuneTime=0.;
    UPROPERTY() double MineTime=0.;
    UPROPERTY() double TigerRoarEndsAt=0.;
    UPROPERTY() double PhysicalVulnerabilityEndsAt=0.;
    UPROPERTY() double BerserkDecayAt=0.;
    UPROPERTY() double WagerEndsAt=0.;
    UPROPERTY() double ComposureEndsAt=0.;
    UPROPERTY() float ElectrifiedBonus=0.f;
    UPROPERTY() float ChillSlow=0.f;
    UPROPERTY() float CorrosionDuration=0.f;
    UPROPERTY() float CorrosionReduction=0.f;
    UPROPERTY() float Shred=0.f;
    UPROPERTY() float Ward=0.f;
    UPROPERTY() float RuneVulnerability=0.f;
    UPROPERTY() float TigerRoarBonus=0.f;
    UPROPERTY() float PhysicalVulnerabilityBonus=0.f;
    UPROPERTY() float RiposteSpeed=0.f;
    UPROPERTY() float RiposteStamina=0.f;
    UPROPERTY() float SlowPct=0.f;
    UPROPERTY() float WaxPct=0.f;
    UPROPERTY() float WeaponHasteMul=0.f;
    UPROPERTY() float PetrifyMul=0.f;
    UPROPERTY() float MarkedValue=0.f;
    UPROPERTY() float InspireSpeed=0.f;
    UPROPERTY() float InspireAtk=0.f;
    UPROPERTY() float CamelReduction=0.f;
    UPROPERTY() float BerserkPeriod=0.f;
    UPROPERTY() float BerserkSpeedPerStack=0.f;
    UPROPERTY() float WagerPeriod=0.f;
    UPROPERTY() float WagerBonusPerStack=0.f;
    UPROPERTY() float ComposurePeriod=0.f;
    UPROPERTY() float ComposureStabilityPerStack=0.f;
    UPROPERTY() float ComposureRecoilReductionPerStack=0.f;
    UPROPERTY() int32 ElectrifiedStacks=0;
    UPROPERTY() int32 ChillStacks=0;
    UPROPERTY() int32 HasteStacks=0;
    UPROPERTY() int32 ChainStacks=0;
    UPROPERTY() int32 CorrosionStacks=0;
    UPROPERTY() int32 VulnerabilityStacks=0;
    UPROPERTY() int32 BleedStacks=0;
    UPROPERTY() int32 BerserkStacks=0;
    UPROPERTY() int32 BerserkLimit=0;
    UPROPERTY() int32 WagerStacks=0;
    UPROPERTY() int32 ComposureStacks=0;
};

/** One small relevant-actor replica; existing components remain gameplay owners. */
UCLASS()
class FPSGAME_API UFPSStatusReplicationComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSStatusReplicationComponent();
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_State) FFPSStatusNetState State;
    UFUNCTION() void OnRep_State();
    void ApplyState(bool bPublishDisplay);
    double ServerTime() const;

};
