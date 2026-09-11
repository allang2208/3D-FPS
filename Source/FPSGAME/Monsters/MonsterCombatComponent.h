#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "MonsterCombatComponent.generated.h"
class UAnimSequence;
class APawn;
/** Shared execution gate. Decisions belong to the AI tree, damage clocks to each monster. */
UCLASS(ClassGroup=AI, meta=(BlueprintSpawnableComponent))
class FPSGAME_API UMonsterCombatComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UMonsterCombatComponent();
 virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick) override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") TObjectPtr<UAnimSequence> HitClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") float PoiseThreshold=60;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") float StaggerDuration=.55f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") float StunDuration=1.2f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Reaction") float PoiseResetSeconds=2.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Reaction") float Poise=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Reaction") int32 HitReactions=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Reaction") bool bStunned=false;
 bool IsDead() const;
 bool IsBusy() const;
 bool IsControlled() const;
 bool CanAttack(APawn* Target) const;
 bool TryAttack(APawn* Target);
 void SetLocomotion(bool Moving,bool Returning=false);
 void SetTarget(APawn* Target);
 float AggroRange() const;
 float LeashRange() const;
 float StopRange() const;
 FVector Home() const;
 void ReachedHome();
 void ReceiveHit(float Damage,APawn* Attacker);
 void BeginReaction(float Duration);
 void FinishReaction();
 UFUNCTION(BlueprintCallable,Category="MonsterAI|Editor") static bool AuthorHitClip(UAnimSequence* Clip,bool bHandBrain);
private:
 float SinceHit=100.f,ReactionTime=0,ReactionDuration=0;
};
