#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M25BiteComponent.generated.h"

class AVortexCofferM25;
class APawn;

USTRUCT()
struct FM25BiteState
{
    GENERATED_BODY()
    UPROPERTY() bool bActive = false;
    UPROPERTY() float StartedAt = 0.f;
    UPROPERTY() float Duration = 1.4f;
    UPROPERTY() float PlayRate = 1.f;
    UPROPERTY() FVector_NetQuantizeNormal Forward = FVector::ForwardVector;
};

/** Physical mouth attack: independent of the back's magic cooldowns and execution state. */
UCLASS(ClassGroup=(Monsters), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UM25BiteComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM25BiteComponent();
    bool CanAttack(APawn* Target) const;
    bool StartAttack(APawn* Target);
    void SetTarget(APawn* Target);
    void Interrupt();
    bool IsBusy() const { return State.bActive; }
    float AnimationTime() const;
    float AnimationWeight() const;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Bite") bool bBiteEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Bite", meta=(ClampMin="0")) float PhysicalAttack = 65.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Bite", meta=(ClampMin="0", Units="s")) float BiteCooldown = 2.5f;
    UPROPERTY(EditAnywhere, Category="M25|Bite", meta=(ClampMin="1", Units="cm")) float TriggerReach = 110.f;
    UPROPERTY(EditAnywhere, Category="M25|Bite", meta=(ClampMin="1", ClampMax="89", Units="deg")) float HalfAngle = 40.f;
    UPROPERTY(EditAnywhere, Category="M25|Bite", meta=(ClampMin="1", Units="cm")) float ContactRadius = 80.f;
    UPROPERTY(EditAnywhere, Category="M25|Bite", meta=(ClampMin="0", Units="s")) float ContactStart = .60f;
    UPROPERTY(EditAnywhere, Category="M25|Bite", meta=(ClampMin="0", Units="s")) float ContactEnd = .76f;
    UPROPERTY(EditAnywhere, Category="M25|Bite", meta=(ClampMin="0.5", ClampMax="2")) float PlaybackRate = 2.f;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_State) FM25BiteState State;
    TWeakObjectPtr<AVortexCofferM25> Monster;
    TWeakObjectPtr<APawn> Target;
    double ReadyAt = 0.;
    float PreviousAnimationTime = 0.f;
    float AttackDamage = 0.f;
    bool bCommitted = false, bHitConsumed = false;
    FVector PreviousMouth = FVector::ZeroVector, StartMouthLocal = FVector::ZeroVector;
    float Clock() const;
    bool CanExecute() const;
    bool LivingPlayer(const APawn* Victim) const;
    bool InFront(const APawn* Victim, FVector Mouth, FVector Forward) const;
    bool ClearSegment(FVector From, FVector To, const APawn* Victim) const;
    FVector Mouth() const;
    void Contact();
    void Cancel();
    UFUNCTION() void OnRep_State();
};
