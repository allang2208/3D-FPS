#pragma once

#include "CoreMinimal.h"
#include "NurseZombie.h"
#include "BlindSupplicantMonster.generated.h"

class UBlindSupplicantAnimInstance;
class UAudioComponent;
class USoundBase;
class UNiagaraComponent;
enum class EM07MagicElement : uint8;

/** M-07, a 3.1 m sensory experiment. AI decisions use the shared monster tree. */
UCLASS(Blueprintable, Placeable)
class FPSGAME_API ABlindSupplicantMonster : public ANurseZombie
{
    GENERATED_BODY()
public:
    ABlindSupplicantMonster(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void InterruptAttack(float Seconds = .25f) override;
    bool CanAttackTarget(APawn* Victim) const;
    bool PrepareAttack(APawn* Victim);
    float CombatStoppingRange() const;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Identity") FText MonsterDisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> SlowWalkClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> ChaseClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> MeleeLeftClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> MeleeRightClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> WallListenClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> MagicGatherClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation") TObjectPtr<UAnimSequence> MagicReleaseClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic") bool bMagicAttacksEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0")) float MagicAttack = 40.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0")) float FireballDamageMultiplier = 1.6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0")) float IceColumnDamageMultiplier = 1.4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0")) float LightningDamageMultiplier = 1.5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic") bool bUsePlayerSkillCooldowns = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0", Units="s")) float FireballCooldown = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0", Units="s")) float IceColumnCooldown = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0", Units="s")) float LightningCooldown = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="100", Units="cm")) float FireballRange = 1400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="100", Units="cm")) float IceColumnRange = 1500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="100", Units="cm")) float LightningRange = 1200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="1", Units="cm/s")) float FireballSpeed = 1500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="1", Units="cm/s")) float IceColumnSpeed = 2000.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="1", Units="cm")) float FireballImpactRadius = 140.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="1", Units="cm")) float IceColumnImpactRadius = 24.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="100", Units="cm")) float MagicMinimumDistance = 240.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Magic", meta=(ClampMin="0", Units="s")) float MagicReleaseContactTime = .30f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Combat", meta=(ClampMin="1", Units="cm")) float SweepHitRadius = 35.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Combat", meta=(ClampMin="0.5", ClampMax="2.5")) float MeleePlaybackRate = 1.30f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation", meta=(ClampMin="0", Units="s")) float AnimationBlendSeconds = .18f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation", meta=(ClampMin="1", Units="cm/s")) float SourceWalkSpeed = 160.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Animation", meta=(ClampMin="1", Units="cm/s")) float SourceChaseSpeed = 360.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Combat", meta=(ClampMin="1", Units="cm/s")) float ChaseSpeed = 360.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Cloth", meta=(ClampMin="100", Units="cm")) float ClothResumeDistance = 650.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Cloth", meta=(ClampMin="100", Units="cm")) float ClothSuspendDistance = 850.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Cloth") bool bEnableGillBoneClearance = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Cloth", meta=(ClampMin="0", ClampMax="24", Units="deg")) float GillClearanceAngleDegrees = 18.f;
    // Contact values are authored clip seconds; PrepareAttack converts them
    // with the same per-attack playback rate used by the pose evaluator.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Combat", meta=(ClampMin="0", Units="s")) float LeftContactTime = .47f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Combat", meta=(ClampMin="0", Units="s")) float RightContactTime = .50f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Combat", meta=(ClampMin="0.01", Units="s")) float ContactWindowSeconds = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|CoreStats", meta=(ClampMin="0")) int32 PhysicalDefense = 16;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|CoreStats", meta=(ClampMin="0")) int32 MagicalDefense = 24;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|CoreStats", meta=(ClampMin="0")) int32 CriticalResistance = 12;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|CoreStats", meta=(ClampMin="0")) float CombatAttributeWeight = 7.5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Identity") bool bWallListening = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Identity", meta=(ClampMin="10", Units="cm")) float WallListenDistance = 120.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M07|Identity") bool bPresentingWallListen = false;

protected:
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void SetAttackAnimationTime(float Seconds) override;
    virtual float GetAttackDuration() const override;
    virtual void ProcessAttackContact(float Previous, float Current) override;
    virtual void SetWalkAnimationRate(float Rate) override;
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration) override;
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining) override;
    virtual void StartDeathPresentation() override;
private:
    enum class EAttack : uint8 { None, SweepLeft, SweepRight, Fireball, IceColumn, Lightning };
    EAttack ActiveAttack = EAttack::None;
    TWeakObjectPtr<APawn> LockedAttackTarget;
    FVector LockedAimPoint = FVector::ZeroVector;
    FVector LockedAttackDirection = FVector::ForwardVector;
    FVector PreviousClaw = FVector::ZeroVector;
    float ActiveAttackDuration = 0.f;
    float ActiveMeleePlaybackRate = 1.f;
    float ActiveGatherDuration = 0.f;
    float AttackDamageSnapshot = 0.f;
    double MagicReadyTimes[3] = {0., 0., 0.};
    double MagicGlobalReadyTime = 0.;
    double ReservedElementReadyTime = 0.;
    double ReservedGlobalReadyTime = 0.;
    bool bMagicCooldownReserved = false;
    int32 NextMagicIndex = 0;
    bool bMagicReleaseStarted = false;
    bool bAttackCommitted = false;
    bool bAttackCancelled = false;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> MagicCharge;
    bool HasAttackSight(const APawn* Victim) const;
    bool IsLivingPlayer(const APawn* Victim) const;
    int32 ReadyMagicIndex(const APawn* Victim) const;
    bool IsMagicAttack() const;
    EM07MagicElement ActiveMagicElement() const;
    FVector AttackClawPosition() const;
    FVector CastingPalmPosition() const;
    void BeginMagicCharge();
    void StopMagicCharge();
    void CancelPendingAttack();
    void ReleaseMagic();
    void SweepClaw(FVector From, FVector To);
    void ApplyPlayerSkillCooldownDefaults();
    void AlignVisual();
    UBlindSupplicantAnimInstance* PosePlayer();
    void RefreshWallPresentation();
    void StartDeathRagdoll();
    void UpdateDeathPresentation();
    void ClearDeathHandoffPenetration();
    void RefreshLocomotionPresentation();
    FTimerHandle WallPresentationTimer;
    double DeathPresentationStart = -1.;
    float DeathGroundZ = 0.f;
    FVector IncomingHitDirection = FVector::ZeroVector;
    bool bNextAttackLeft = true;
    bool bRagdollStarted = false;
    bool bClothSuspendedForCorpse = false;
    bool bWantsClothSimulation = true;
    void UpdateClothDistance(float DeltaSeconds);

    void StopWallMimic();
    double NextWallMimicTime = 0.0;
public:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M07|Identity") TObjectPtr<UAudioComponent> WallMimicVoice;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Identity") TObjectPtr<USoundBase> WallMimicSound;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Identity", meta=(ClampMin="8", Units="s")) float WallMimicIntervalSeconds = 24.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M07|Identity", meta=(ClampMin="0", ClampMax="1")) float WallMimicVolume = .65f;
};
