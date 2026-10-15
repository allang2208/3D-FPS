#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/NetSerialization.h"
#include "M66AudioComponent.generated.h"
class AM66IncineratorMonster;
class UAudioComponent;

USTRUCT()
struct FM66SoundEvent
{
    GENERATED_BODY()
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() FName Cue;
    UPROPERTY() double At=0.;
    UPROPERTY() FVector_NetQuantize Location;
};
UCLASS()
class FPSGAME_API UM66AudioComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM66AudioComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void PreReplication(IRepChangedPropertyTracker& Tracker) override;
    void Emit(FName Cue,const FVector& At,double Time=-1.);
    uint32 ConsumedSerial() const {return LastConsumed;}
    uint32 EmittedSerial() const {return NextSerial;}
    int32 ResolvedEvents() const {return ResolvedCount;}
private:
    double Clock() const;
    UFUNCTION() void OnRep_Events();
    UPROPERTY(Replicated) double InitialServerTime=-1.;
    UPROPERTY(ReplicatedUsing=OnRep_Events) TArray<FM66SoundEvent> Events;
    UPROPERTY(Transient) TObjectPtr<AM66IncineratorMonster> Monster;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> SmokeVoice;
    uint32 NextSerial=0,LastConsumed=0,AttackSerial=0;
    int32 ResolvedCount=0;
    float PreviousPhase=0.f;
    bool bHavePhase=false,bSwingPlayed=false,bRecoveryPlayed=false;
    double NextHurtAt=0.,NextStepAt=0.;
};
