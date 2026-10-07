#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "VortexCofferM25.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UPhysicsAsset;
class UMonsterCombatComponent;
class UM25BackElectricComponent;
class UM25MagicComponent;
class UM25BiteComponent;
class UMonsterCorpseRagdollComponent;
class UAudioComponent;
class USoundBase;
class USoundAttenuation;

/** Wide-bodied M-25 with shared-tree locomotion and electrode-based electric attacks. */
UCLASS()
class FPSGAME_API AVortexCofferM25 : public ACharacter
{
    GENERATED_BODY()
public:
    explicit AVortexCofferM25(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void GetActorEyesViewPoint(FVector& Location, FRotator& Rotation) const override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M25") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M25|Electric") TObjectPtr<UM25BackElectricComponent> BackElectric;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M25|Magic") TObjectPtr<UM25MagicComponent> Magic;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Visual") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Animation") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Animation") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly, Category="M25|Visual") float MeshYaw = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Movement", meta=(ClampMin="0.0", Units="cm/s")) float WalkSpeed = 110.f;
    UPROPERTY(EditDefaultsOnly, Category="M25|Animation", meta=(ClampMin="1.0", Units="cm/s")) float AnimationWalkSpeed = 16.f;
    UPROPERTY(EditAnywhere, Category="M25|AI", meta=(Units="cm")) float AggroRadius = 3000.f;
    UPROPERTY(EditAnywhere, Category="M25|AI", meta=(Units="cm")) float LeashRadius = 4500.f;
    UPROPERTY(EditAnywhere, Category="M25|AI", meta=(Units="cm")) float StoppingDistance = 270.f;
    UPROPERTY(VisibleInstanceOnly, Category="M25|AI") FVector Home = FVector::ZeroVector;

protected:
    virtual void BeginPlay() override;
private:
    void ApplyVisual();
    TWeakObjectPtr<APawn> CombatTarget;
    bool bCombatPoseOverride = false, bSavedUpdateRateOptimization = true;
    uint8 SavedPoseTick = 0;
public:
    // A ready second channel can enter the shared BT attack branch while the first runs.
    bool AttackBusy() const;
    bool CanAttackTarget(APawn* Target) const;
    bool StartAttack(APawn* Target);
    void SetCombatTarget(APawn* Target);
    void RefreshCombatPoseTick();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M25|Bite") TObjectPtr<UM25BiteComponent> Bite;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Animation") TObjectPtr<UAnimSequence> BiteClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Replicated, Category="M25|Vitals", meta=(ClampMin="1")) float MaxHealth = 1500.f;
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Replicated, Category="M25|Vitals") float Health = 1500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Vitals", meta=(ClampMin="0")) int32 PhysicalDefense = 25;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Vitals", meta=(ClampMin="0")) int32 MagicalDefense = 40;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Vitals", meta=(ClampMin="1")) int32 Level = 8;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Vitals") EMonsterRank Rank = EMonsterRank::Normal;
    UPROPERTY(EditAnywhere, Category="M25|Vitals") int32 ExperienceReward = 100;
    UPROPERTY(EditDefaultsOnly, Category="M25|Hit") TObjectPtr<UPhysicsAsset> HitSurfacePhysics;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Animation") TObjectPtr<UAnimSequence> HitClip;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditDefaultsOnly, Category="M25|Vitals", meta=(ClampMin="2", Units="s")) float CorpseSeconds = 20.f;
    bool Dead() const { return DeathStartedAt >= 0.f || IsActorBeingDestroyed(); }
    bool Controlled() const { return bHitReaction && !Dead(); }
    bool IsWeakpointHit(const FHitResult& Hit) const;
    void InterruptAttack(float Seconds);
    void StartHitPresentation();
    void SetHitPresentationTime(float Elapsed, float Remaining);
    void FinishHitReaction();
    float HitAnimationTime() const { return HitTime; }
    float DeathAnimationTime() const;
    UFUNCTION(BlueprintCallable, Category="M25|Editor")
    static UPhysicsAsset* BuildHitSurfacePhysics(USkeletalMesh* InMesh, const FString& AssetPath);
private:
    UPROPERTY(ReplicatedUsing=OnRep_Death) float DeathStartedAt = -1.f;
    UFUNCTION() void OnRep_Death();
    bool bHitReaction = false;
    float HitTime = 0.f;
    float CombatClock() const;
    void ApplyHitCollision();
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|AI") bool bSearchForPlayers = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|AI", meta=(ClampMin="300", Units="cm")) float SearchRadius = 1200.f;
    // The shared BT owns navigation. This only supplies a cached reachable idle-search goal.
    bool SearchDestination(FVector& Destination);
    void DeferSearch();
    void FaceNearbyTarget(APawn* Target, float DeltaSeconds);
private:
    FVector SearchGoal = FVector::ZeroVector;
    double NextSearchAt = 0., SearchGoalDeadline = 0.;
    bool bHasSearchGoal = false;
public:
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M25|Death") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;

    // Authored one-shots/loops; components below read these actor-level references.
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> IdleSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> CrawlSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> BiteSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> HitSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> DeathSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> CrackleSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> ChargeSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> LanceChargeSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<USoundBase> LanceReleaseSound;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<UAudioComponent> IdleVoice;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M25|Audio") TObjectPtr<UAudioComponent> CrawlVoice;
    USoundAttenuation* OneShotAttenuation(float Falloff) const;
private:
    void UpdateLoopAudio();
};
