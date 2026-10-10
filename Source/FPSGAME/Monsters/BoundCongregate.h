#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "BoundCongregate.generated.h"

class UAnimSequence;
class UMonsterCombatComponent;
class UMonsterCorpseRagdollComponent;
class USkeletalMesh;
class UPhysicsAsset;
class USoundBase;
class UAudioComponent;
class UCapsuleComponent;

UENUM()
enum class EBoundCongregateState : uint8 { Idle, Crawl, Bite, Stagger, Dead, TentacleWindup, TentacleStrike, TentacleWrap, TentacleDrag, TentacleRecover, Flurry };

USTRUCT()
struct FBoundCongregateState
{
    GENERATED_BODY()
    UPROPERTY() EBoundCongregateState State=EBoundCongregateState::Idle;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() TObjectPtr<ACharacter> CapturedTarget;
    UPROPERTY() FVector TentacleAim=FVector::ZeroVector;
    UPROPERTY() float TentacleRadius=34.f;
    UPROPERTY() float ReleasedWrap=0.f;
    UPROPERTY() float ReleasedWeight=1.f;
    UPROPERTY() float ReleasedStrike=1.f;
    UPROPERTY() double TentacleRecoveryStartedAt=-1.;
};

/** Ten donor limbs and separate torn garments; decisions use the shared monster tree. */
UCLASS()
class FPSGAME_API ABoundCongregate : public ACharacter
{
    GENERATED_BODY()
public:
    explicit ABoundCongregate(const FObjectInitializer& Initializer=FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void GetActorEyesViewPoint(FVector& Location,FRotator& Rotation) const override;

    UPROPERTY(VisibleAnywhere,Category="Congregate") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere,Category="Congregate") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;
    UPROPERTY(EditDefaultsOnly,Category="Congregate") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> TurnLeftClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> TurnRightClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> BiteClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> FlurryClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> HitClip;
    UPROPERTY(EditDefaultsOnly,Category="Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Vitals",Replicated) float Health=1800.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Vitals",Replicated) float MaxHealth=1800.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Vitals") int32 Level=10;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Vitals") EMonsterRank Rank=EMonsterRank::Normal;
    UPROPERTY(EditAnywhere,Category="Vitals") int32 PhysicalDefense=45;
    UPROPERTY(EditAnywhere,Category="Vitals") int32 MagicDefense=25;
    UPROPERTY(EditAnywhere,Category="Vitals") int32 ExperienceReward=150;
    UPROPERTY(EditAnywhere,Category="Movement") float WalkSpeed=60.f;
    UPROPERTY(EditAnywhere,Category="Movement") float AnimationWalkSpeed=50.f;
    UPROPERTY(EditAnywhere,Category="AI") float AggroRadius=2400.f;
    UPROPERTY(EditAnywhere,Category="AI") float LeashRadius=3600.f;
    UPROPERTY(EditAnywhere,Category="Combat") float BiteTriggerRange=350.f;
    UPROPERTY(EditAnywhere,Category="Combat") float BiteReach=235.f;
    UPROPERTY(EditAnywhere,Category="Combat") float BiteDamage=55.f;
    UPROPERTY(EditAnywhere,Category="Combat") float BiteCooldown=2.5f;
    UPROPERTY(EditAnywhere,Category="Combat") float BiteContactSeconds=.56f;
    UPROPERTY(EditAnywhere,Category="Death") float CorpseSeconds=25.f;
    UPROPERTY(VisibleInstanceOnly,Category="AI") FVector Home=FVector::ZeroVector;
    UPROPERTY(ReplicatedUsing=OnRep_State) FBoundCongregateState NetState;
    UPROPERTY(EditDefaultsOnly,Category="Audio") TObjectPtr<USoundBase> BreathSound;
    UPROPERTY(EditDefaultsOnly,Category="Audio") TObjectPtr<USoundBase> BiteSound;
    UPROPERTY(EditDefaultsOnly,Category="Audio") TObjectPtr<USoundBase> FlurrySound;
    UPROPERTY(EditDefaultsOnly,Category="Audio") TObjectPtr<USoundBase> DeathSound;
    UPROPERTY(VisibleAnywhere,Category="Audio") TObjectPtr<UAudioComponent> Voice;
    UPROPERTY(EditDefaultsOnly,Category="Congregate") float MeshYaw=0;
    UPROPERTY(VisibleAnywhere,Category="Audio") TObjectPtr<UAudioComponent> ActionVoice;

    bool Dead() const { return NetState.State==EBoundCongregateState::Dead; }
    bool Controlled() const { return NetState.State==EBoundCongregateState::Stagger; }
    bool Busy() const { return Dead()||Controlled()||NetState.State==EBoundCongregateState::Bite||NetState.State==EBoundCongregateState::Flurry||TentacleActive(); }
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    void SetLocomotion(bool Moving,bool Returning=false);
    void SetTarget(APawn* Victim) { Target=Victim; }
    void InterruptAttack(float Seconds);
    void StartHitPresentation();
    void SetHitPresentationTime(float Elapsed,float Remaining);
    void FinishHitReaction();
    double StateElapsed() const;
    UFUNCTION(BlueprintCallable,Category="Congregate|Authoring")
    static bool BuildSurfacePhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* Physics);
    UFUNCTION(BlueprintCallable,Category="Congregate|Authoring")
    static bool BuildGarmentSimulation(USkeletalMesh* SourceMesh);
    UFUNCTION(BlueprintCallable,Category="Congregate|Authoring")
    static float ReferenceFacingYaw(USkeletalMesh* SourceMesh);
    UFUNCTION(BlueprintCallable,Category="Congregate|Authoring")
    static void PrepareCorpseMesh(USkeletalMesh* SourceMesh);
protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION() void OnRep_State();
    void ApplyVisual();
    void SetState(EBoundCongregateState State);
    void PresentState();
    void Sample(float Time);
    void Contact();
    bool CanBite(APawn* Victim) const;
    bool CanFlurry(APawn* Victim) const;
    void TickMelee(float Dt);
    void FlurryContact(int32 Beat,float PlaybackTime);
    bool HasSight(APawn* Victim) const;
    double Clock() const;
    TWeakObjectPtr<APawn> Target;
    double NextAttack=0.;
    float AttackYaw=0.f,ReactionSeconds=0.f,ClothBudgetElapsed=0.f;
    bool bContactConsumed=true,bClothSuspended=false,bWantsCloth=true;
    double NextBite=0.,NextFlurry=0.;
    uint8 AttackChoice=0,NextFlurryHit=0,NextFlurrySound=0;
public:
    UPROPERTY(EditAnywhere,Category="Combat|Flurry",meta=(ClampMin="0")) float FlurryRange=280.f;
    UPROPERTY(EditAnywhere,Category="Combat|Flurry",meta=(ClampMin="0")) float FlurryDamage=18.f;
    UPROPERTY(EditAnywhere,Category="Combat|Flurry",meta=(ClampMin="0")) float FlurryFinisherDamage=32.f;
    UPROPERTY(EditAnywhere,Category="Combat|Flurry",meta=(ClampMin="0.1")) float FlurryCooldown=4.5f;
    UPROPERTY(EditAnywhere,Category="Combat|Flurry",meta=(ClampMin="1")) float FlurryPalmRadius=45.f;
    bool TentacleActive() const { return !Dead()&&(NetState.CapturedTarget||TentacleRecovering()||(NetState.State>=EBoundCongregateState::TentacleWindup&&NetState.State<=EBoundCongregateState::TentacleRecover)); }
    bool TentacleRecovering() const { return !Dead()&&!NetState.CapturedTarget&&(NetState.State==EBoundCongregateState::TentacleRecover||(NetState.TentacleRecoveryStartedAt>=0.&&TentacleRecoveryElapsed()<TentacleRecoverSeconds)); }
    double TentacleRecoveryElapsed() const { return NetState.TentacleRecoveryStartedAt>=0.?FMath::Max(0.,Clock()-NetState.TentacleRecoveryStartedAt):StateElapsed(); }
    bool IsDragging(const ACharacter* Victim) const;
    FVector CapturePullVelocity(const ACharacter* Victim) const;
    void CancelTentacle();
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0")) float TentacleRange=3000.f;
    float TentacleReleaseDuration() const;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.1")) float TentacleCooldown=2.f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.1")) float TentacleWindupSeconds=.62f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.01")) float TentacleStrikeSeconds=.09f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.1")) float TentacleWrapSeconds=.4f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.1")) float TentacleHoldSeconds=3.5f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.1")) float TentacleRecoverSeconds=.48f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0")) float TentacleImpactDamage=20.f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0")) float TentacleTickDamage=8.f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0.1")) float TentacleDamageInterval=.5f;
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="0")) float TentaclePullSpeed=65.f;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    bool CanTentacle(APawn* Victim) const;
    bool BeginTentacle(APawn* Victim);
    void TickTentacle(float Dt);
    void EndTentacle(bool bRecover);
    void TentacleHit(ACharacter* Victim,const FHitResult& Hit);
    double NextTentacle=0.,NextSqueeze=0.;
    FVector PreviousTentacleTip=FVector::ZeroVector,LastCapturedPosition=FVector::ZeroVector;
    float TentacleBlockedSeconds=0.f;
    bool bTentacleFinalPoseRequested=false;
public:
    UPROPERTY(EditAnywhere,Category="Combat|Tentacle",meta=(ClampMin="1")) float TentacleMaxHealth=300.f;
    UPROPERTY(Replicated,VisibleInstanceOnly,Category="Combat|Tentacle") float TentacleHealth=300.f;
    bool IsTentacleHit(const FHitResult& Hit) const;
    static bool IsTentaclePart(const FHitResult& Hit);
    float ApplyTentacleShot(float Damage);
private:
    void UpdateTentacleHitShapes();
    void UpdateTentacleHitShapeState();
    void BeginCapturedBite(ACharacter* Victim);
    TArray<TWeakObjectPtr<UCapsuleComponent>> TentacleHitShapes;
    FDelegateHandle TentaclePoseHandle;
};
