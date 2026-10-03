#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "PlayerGuardBreakComponent.generated.h"
class APlayerController;

/** Pawn-owned guard break: switching weapons cannot clear the timed input lock. */
UCLASS(ClassGroup=(Combat),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UPlayerGuardBreakComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UPlayerGuardBreakComponent();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    void Apply(float Seconds);
    bool IsActive() const { return LockedController.IsValid(); }
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void Release();
    TWeakObjectPtr<APlayerController> LockedController;
    FTimerHandle Timer;
    void ApplyInputLock(float Seconds);
    UFUNCTION() void OnRep_StunUntil();
    UPROPERTY(ReplicatedUsing=OnRep_StunUntil) double StunUntil=0.;
};
