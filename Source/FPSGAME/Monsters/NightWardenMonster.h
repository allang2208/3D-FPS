#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "NightWardenMonster.generated.h"

class UAnimSequence;
class UMonsterCombatComponent;

/** Shared BT locomotion and a single authoritative giant-arm melee clock. */
UCLASS(Blueprintable)
class FPSGAME_API ANightWardenMonster : public ACharacter
{
    GENERATED_BODY()
public:
    ANightWardenMonster(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    bool CanAttack(APawn* Candidate) const;
    bool StartAttack(APawn* Candidate);
    void FaceMeleeTarget(APawn* Candidate, float DeltaSeconds);
    void CancelAttack();
    void StopForControl(float Seconds);
    bool IsControlled() const;
    float AttackPresentationTime() const;
    bool IsAttacking() const { return bAttacking; }
    uint32 CurrentAttackSerial() const { return AttackSerial; }

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="NightWarden") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Animation") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Animation") TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Melee") TObjectPtr<UAnimSequence> AttackClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="NightWarden|Melee", meta=(ClampMin="0")) float AttackDamage = 45.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="NightWarden|Melee", meta=(Units="cm")) float AttackRange = 170.f;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Melee", meta=(Units="s")) float ContactStart = .96f;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Melee", meta=(Units="s")) float ContactEnd = 1.20f;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Melee", meta=(Units="s")) float FacingLockTime = .78f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="NightWarden|Melee", meta=(Units="s")) float AttackCooldown = 1.1f;
    // Samples are baked from this exact fitted animation, in mesh-local cm.
    // The server can sweep the real forearm/palm arc without evaluating a render mesh.
    UPROPERTY(EditDefaultsOnly, Category="NightWarden|Melee") TArray<FVector> ForearmTrace;
    UPROPERTY(EditDefaultsOnly, Category="NightWarden|Melee") TArray<FVector> PalmTrace;
    UPROPERTY(EditDefaultsOnly, Category="NightWarden|Melee") float TraceSampleRate = 60.f;
    UPROPERTY(EditDefaultsOnly, Category="NightWarden|Melee", meta=(Units="cm")) float TraceRadius = 15.f;
    // Fixed authoring speed of the 2.4 second loop, independent of gameplay speed modifiers.
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="NightWarden|Animation", meta=(ClampMin="1", Units="cm/s")) float SourceWalkSpeed = 177.376873f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="NightWarden|Movement", meta=(ClampMin="0", Units="cm/s")) float WalkSpeed = 177.376873f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="NightWarden|AI", meta=(Units="cm")) float AggroRadius = 1400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="NightWarden|AI", meta=(Units="cm")) float StoppingDistance = 150.f;
    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category="NightWarden|AI") FVector Home = FVector::ZeroVector;
private:
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    void TickAttack(float DeltaSeconds);
    void SweepAttack(float FromTime, float ToTime);
    bool HasAttackSight(const APawn* Candidate) const;
    double CombatTime() const;
    UPROPERTY(Replicated) bool bAttacking = false;
    UPROPERTY(Replicated) uint32 AttackSerial = 0;
    UPROPERTY(Replicated) double AttackStartedAt = 0.;
    UPROPERTY(Replicated) float StoppedAttackTime = 0.f;
    UPROPERTY(Replicated) double ControlUntil = 0.;
    TWeakObjectPtr<APawn> AttackTarget;
    TSet<TWeakObjectPtr<APawn>> HitPlayers;
    float PreviousAttackTime = 0.f, AttackDamageSnapshot = 0.f;
    double NextAttackAt = 0.;
    bool bMovementOrientationBeforeAttack = true;
    bool bWantsClothSimulation = true;
};
