#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "SpiralPillarM14.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UPhysicsAsset;
class UMaterialInterface;
class AM14MucusProjectile;
class UMonsterCombatComponent;
class UMonsterCorpseRagdollComponent;
class UM14SoftBodyData;
class UM14SoftBodyDeathComponent;
class UAudioComponent;
class USoundBase;
class USoundAttenuation;
UENUM(BlueprintType)
enum class EM14State : uint8 { Idle, Crawl, Returning, Bite, Stagger, Dying, Corpse, Spit, SweepLeft, SweepRight, TrunkSlam, Whirlwind };

/** Source-preserving nonhumanoid pillar; shared BT owns decisions and one clock executes attacks. */
UCLASS(Blueprintable)
class FPSGAME_API ASpiralPillarM14 : public ACharacter
{
    GENERATED_BODY()
public:
    ASpiralPillarM14(const FObjectInitializer& Initializer=FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void PossessedBy(AController* NewController) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M14") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M14") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> TurnLeftClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> TurnRightClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> BiteClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") float MaxHealth=1800.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") float PhysicalAttack=48.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") float PhysicalDefense=40.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") float MagicDefense=20.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") int32 Level=10;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") EMonsterRank Rank=EMonsterRank::Elite;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M14|Stats") int32 ExperienceReward=650;
    UPROPERTY(EditAnywhere,Category="M14|Movement",meta=(ClampMin="0")) float WalkSpeed=112.f;
    UPROPERTY(EditAnywhere,Category="M14|Animation",meta=(ClampMin="1")) float AnimationWalkSpeed=28.f;
    UPROPERTY(EditAnywhere,Category="M14|AI") float AggroRadius=3300.f;
    UPROPERTY(EditAnywhere,Category="M14|AI") float LeashRadius=4000.f;
    UPROPERTY(EditAnywhere,Category="M14|Bite") float BiteTriggerRange=185.f;
    UPROPERTY(EditAnywhere,Category="M14|Bite") float MouthReach=70.f;
    UPROPERTY(EditAnywhere,Category="M14|Bite") float BiteContactSeconds=.86f;
    UPROPERTY(EditAnywhere,Category="M14|Bite") float BiteCooldown=3.2f;
    UPROPERTY(EditAnywhere,Category="M14|Death") float CorpseSeconds=20.f;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Replicated,Category="M14") float Health=1800.f;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,ReplicatedUsing=OnRep_State,Category="M14") EM14State State=EM14State::Idle;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M14") FVector Home;
    bool Dead() const { return Health<=0.f||State==EM14State::Dying||State==EM14State::Corpse; }
    bool IsAttacking() const { return State==EM14State::Bite||State==EM14State::Spit||State==EM14State::TrunkSlam||State==EM14State::Whirlwind||IsSweeping(); }
    bool IsSweeping() const { return State==EM14State::SweepLeft||State==EM14State::SweepRight; }
    bool Busy() const { return Dead()||IsAttacking()||State==EM14State::Stagger; }
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    void SetTarget(APawn* Victim) { Target=Victim; }
    void SetLocomotion(bool Moving,bool Returning);
    void InterruptAttack(float Seconds);
    void StartHitPresentation();
    void SetHitPresentationTime(float Elapsed,float Remaining);
    void FinishHitReaction();
    bool IsWeakpointHit(const FHitResult& Hit) const;
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool BuildPhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* Asset);
private:
    UFUNCTION() void OnRep_State();
    void ApplyVisual();
    void SetState(EM14State Next);
    void PresentState();
    void Play(UAnimSequence* Clip,bool Loop,bool Clock,float Blend=.16f);
    void Sample(float Seconds);
    FVector Mouth() const;
    bool CanSee(const APawn* Victim) const;
    void BiteContact();
    TWeakObjectPtr<APawn> Target;
    float StateSeconds=0.f,CooldownLeft=0.f,ReactionSeconds=0.f,LockedYaw=0.f,PreviousYaw=0.f;
    bool bConsumed=false;
public:
    // A single connected corpse carries the continuous skin; living hit shapes stay separate.
    UPROPERTY(EditDefaultsOnly,Category="M14|Death") TObjectPtr<UPhysicsAsset> CorpsePhysicsAsset;
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool BuildCorpsePhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* QueryAsset,UPhysicsAsset* CorpseAsset);
    // Append new reflected properties to retain the existing native layout prefix.
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> SpitClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> SweepPositiveClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> SweepNegativeClip;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UMaterialInterface> MucusMaterial;
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UMaterialInterface> MucusCoreMaterial;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitMinRange=400.f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitMaxRange=3000.f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitAimLockSeconds=.65f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitReleaseSeconds=1.10f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitCooldown=3.5f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitSpeed=1000.f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitTravelRange=3300.f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitDamageMultiplier=.75f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitSlowPercent=.25f;
    UPROPERTY(EditAnywhere,Category="M14|Spit") float SpitSlowSeconds=2.5f;
    UPROPERTY(EditAnywhere,Category="M14|Sweep") float SweepTriggerRange=250.f;
    UPROPERTY(EditAnywhere,Category="M14|Sweep") float SweepStartSeconds=.80f;
    UPROPERTY(EditAnywhere,Category="M14|Sweep") float SweepEndSeconds=1.20f;
    UPROPERTY(EditAnywhere,Category="M14|Sweep") float SweepCooldown=4.8f;
    UPROPERTY(EditAnywhere,Category="M14|Sweep") float SweepDamageMultiplier=.9f;
    UPROPERTY(EditAnywhere,Category="M14|Sweep") float SweepRadius=18.f;
    float AttackStopRange() const;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    EM14State ChooseAttack(APawn* Victim) const;
    UAnimSequence* AttackClip(EM14State Attack) const;
    void TickAttack(float Dt);
    void ReleaseSpit();
    void SweepContact();
    void CancelProjectile();
    bool bPositiveXIsRight=true,bSpitAimLocked=false;
    float SpitCooldownLeft=0.f,SweepCooldownLeft=0.f,NextSweepSample=0.f;
    FVector SpitAimPoint=FVector::ZeroVector;
    FVector SweepTipOffsets[8];
    TWeakObjectPtr<APawn> AttackTarget;
    TWeakObjectPtr<AM14MucusProjectile> ActiveProjectile;
    TSet<TWeakObjectPtr<AActor>> SweepVictims;
public:
    UPROPERTY(EditDefaultsOnly,Category="M14|Death") TArray<FName> SoftDeathMorphTargets;
    UPROPERTY(EditDefaultsOnly,Category="M14|Death",meta=(ClampMin="0",ClampMax="1")) float DeathPhysicsFraction=.6f;
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool BuildSoftCorpsePhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* CorpseAsset,const TArray<FVector>& BlenderPointsCm,const TArray<int32>& HullSizes);
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool BuildSoftDeathMorphs(USkeletalMesh* SourceMesh);
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> TrunkSlamClip;
    UPROPERTY(EditAnywhere,Category="M14|TrunkSlam") float SlamMinRange=190.f;
    UPROPERTY(EditAnywhere,Category="M14|TrunkSlam") float SlamTriggerRange=320.f;
    UPROPERTY(EditAnywhere,Category="M14|TrunkSlam") float SlamContactSeconds=1.20f;
    UPROPERTY(EditAnywhere,Category="M14|TrunkSlam") float SlamCooldown=6.f;
    UPROPERTY(EditAnywhere,Category="M14|TrunkSlam") float SlamDamageMultiplier=1.35f;
    UPROPERTY(EditAnywhere,Category="M14|TrunkSlam") float SlamBodyRadius=45.f;
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool ApplyHardwareSkin(USkeletalMesh* SourceMesh,const FString& DataFile,const TArray<FName>& SourceBones);
private:
    void SlamContact();
    float SlamCooldownLeft=0.f;
    void ApplySoftDeath(float Seconds);
    bool StartCorpsePhysics();
public:
    UPROPERTY(EditDefaultsOnly,Category="M14|Assets") TObjectPtr<UAnimSequence> WhirlwindClip;
    UPROPERTY(EditAnywhere,Category="M14|Whirlwind",meta=(ClampMin="0")) float WhirlwindCooldown=12.f;
    UPROPERTY(EditAnywhere,Category="M14|Whirlwind",meta=(ClampMin="0")) float WhirlwindTriggerRange=308.75f;
    UPROPERTY(EditAnywhere,Category="M14|Whirlwind",meta=(ClampMin="0")) float WhirlwindDamageMultiplier=2.4f;
    UPROPERTY(EditAnywhere,Category="M14|Whirlwind",meta=(ClampMin="0")) float WhirlwindKnockback=250.f;
private:
    void TickWhirlwindContact();
    void WhirlwindContact(float FromTime,float ToTime);
    float WhirlwindCooldownLeft=0.f;
    int32 WhirlwindSample=1;
    TSet<TWeakObjectPtr<AActor>> WhirlwindVictims;
    FVector SpitAimVelocity=FVector::ZeroVector;
    float SpitAimSampleSeconds=0.f;
public:
    // Sample times for the baked tissue collapse; only adjacent shapes are active.
    UPROPERTY(EditDefaultsOnly,Category="M14|Death") TArray<float> SoftDeathMorphTimes;
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool ApplySoftDeathSequence(USkeletalMesh* SourceMesh,const FString& DataFile,const TArray<FName>& MorphNames);
    UFUNCTION(BlueprintCallable,Category="M14|Authoring") static bool ApplySupportSkin(USkeletalMesh* SourceMesh,const FString& DataFile,const TArray<FName>& SourceBones);
    UPROPERTY(EditDefaultsOnly,Category="M14|Death") TObjectPtr<UM14SoftBodyData> SoftBodyDeathData;
    UPROPERTY(VisibleAnywhere,Category="M14|Death") TObjectPtr<UM14SoftBodyDeathComponent> SoftBodyDeath;

    // Authored cues; the projectile reads its own impact reference.
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> CrawlSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> BiteSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> HitSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> DeathSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> SpitSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> TrunkSlamSound;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<USoundBase> WhirlwindSound;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M14|Audio") TObjectPtr<UAudioComponent> CrawlVoice;
    USoundAttenuation* OneShotAttenuation(float Falloff) const;
private:
    void UpdateLoopAudio();
};
