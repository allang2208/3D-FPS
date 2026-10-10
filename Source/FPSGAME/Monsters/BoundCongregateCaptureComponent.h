#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BoundCongregateCaptureComponent.generated.h"

class ABoundCongregate;
class ACharacter;

/** Target-owned restraint: one captor, native swept motion, no look/weapon lock. */
UCLASS()
class FPSGAME_API UBoundCongregateCaptureComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UBoundCongregateCaptureComponent();
    static UBoundCongregateCaptureComponent* GetOrAdd(ACharacter* Victim);
    static bool IsCaptured(const AActor* Victim);
    bool Capture(ABoundCongregate* Captor);
    void Release(ABoundCongregate* Captor);
    bool IsHeldBy(const ABoundCongregate* Captor) const;
    bool IsHeld() const;
    static constexpr int32 RequiredEscapeHits=1;
    int32 GetEscapeHits() const { return EscapeHits; }
    float GetTentacleHealth() const;
    float GetTentacleMaxHealth() const;
    /** Called once at the authored F quick-melee contact, not on key press. */
    bool HitRestraintWithQuickMelee();
    virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Captor) TObjectPtr<ABoundCongregate> Source;
    UPROPERTY(Replicated) uint8 EscapeHits=0;
    UFUNCTION() void OnRep_Captor();
    void ApplyControl();
    void ClearControl();
    uint16 PullMotionId=0;
    UFUNCTION(Server,Reliable) void ServerQuickMeleeContact();
    double NextEscapeContact=0.;
};
