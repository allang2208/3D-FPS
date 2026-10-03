#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "M10Mawcrawler.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UPhysicsAsset;
class UMonsterCombatComponent;
class UMonsterCorpseRagdollComponent;
class UAudioComponent;
class USoundBase;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class AM10PoisonGas;
UENUM(BlueprintType)
enum class EM10State : uint8 { Idle, Crawl, Returning, Bite, Stagger, Dying, Corpse, Howl, RearGas };

/** Dedicated eight-limb creature. Shared BT decides; this owns contact timing. */
UCLASS(Blueprintable)
class FPSGAME_API AM10Mawcrawler : public ACharacter
{
    GENERATED_BODY()
public:
    AM10Mawcrawler(const FObjectInitializer& Initializer=FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M10") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M10") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;
    UPROPERTY(EditDefaultsOnly,Category="M10|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly,Category="M10|Assets") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Assets") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Assets") TObjectPtr<UAnimSequence> BiteClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Assets") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") float MaxHealth=1800.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") float PhysicalAttack=55.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") float PhysicalDefense=45.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") float MagicDefense=20.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") int32 Level=10;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") EMonsterRank Rank=EMonsterRank::Elite;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Stats") int32 ExperienceReward=650;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|Movement",meta=(Units="cm/s")) float WalkSpeed=55.f;
    UPROPERTY(EditAnywhere,Category="M10|Animation",meta=(ClampMin="1")) float AnimationWalkSpeed=46.153846f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|AI") float AggroRadius=1600.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="M10|AI") float LeashRadius=2800.f;
    UPROPERTY(EditAnywhere,Category="M10|Bite",meta=(Units="cm")) float BiteTriggerRange=450.f;
    UPROPERTY(EditAnywhere,Category="M10|Bite",meta=(Units="cm")) float MouthReach=150.f;
    UPROPERTY(EditAnywhere,Category="M10|Bite",meta=(Units="s")) float BiteContactSeconds=.70f;
    UPROPERTY(EditAnywhere,Category="M10|Bite",meta=(Units="s")) float BiteCooldown=3.2f;
    UPROPERTY(EditAnywhere,Category="M10|Death") float CorpseSeconds=20.f;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Replicated,Category="M10") float Health=1800.f;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,ReplicatedUsing=OnRep_State,Category="M10") EM10State State=EM10State::Idle;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M10") FVector Home;
    bool Dead() const {return State==EM10State::Dying||State==EM10State::Corpse||Health<=0.f;}
    bool Busy() const {return Dead()||State==EM10State::Bite||State==EM10State::Stagger||State==EM10State::Howl||State==EM10State::RearGas;}
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    void SetTarget(APawn* Victim) {Target=Victim;}
    void SetLocomotion(bool Moving,bool Returning);
    void InterruptAttack(float Seconds);
    void StartHitPresentation();
    void SetHitPresentationTime(float Elapsed,float Remaining);
    void FinishHitReaction();
    UFUNCTION(BlueprintCallable,Category="M10|Authoring") static bool BuildPhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* Asset);
    UFUNCTION(BlueprintCallable,Category="M10|Authoring") static bool ConfigureSurfaceRig(USkeletalMesh* SourceMesh);
    UFUNCTION(BlueprintCallable,Category="M10|Authoring") static FString BuildNavigation(UWorld* World);
    UFUNCTION(BlueprintCallable,Category="M10|Authoring") static FString BuildMapNavigation(const FString& MapPackage);
private:
    UFUNCTION() void OnRep_State();
    void ApplyVisual();
    void SetState(EM10State NewState);
    void PresentState();
    void Play(UAnimSequence* Clip,bool Loop,bool ExternalClock,float Blend=.15f);
    void Sample(float Time);
    FVector Mouth() const;
    bool CanSee(const AActor* Victim) const;
    void BiteContact();
    float StateSeconds=0.f,CooldownLeft=0.f,ReactionSeconds=0.f;
    float LockedYaw=0.f;
    bool bConsumed=false;
    TWeakObjectPtr<APawn> Target;
public:
    // Appended reflected members preserve the order of the existing class.
    UPROPERTY(EditDefaultsOnly,Category="M10|Turning") TObjectPtr<UAnimSequence> CurveLeftClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Turning") TObjectPtr<UAnimSequence> CurveRightClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Turning") TObjectPtr<UAnimSequence> PivotLeftClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Turning") TObjectPtr<UAnimSequence> PivotRightClip;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float SlowTurnAngle=30.f;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float PivotStartAngle=70.f;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float PivotFinishAngle=25.f;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float MovingTurnSpeed=36.f;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float PivotTurnSpeed=30.f;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float TurnAcceleration=97.5f;
    UPROPERTY(EditAnywhere,Category="M10|Turning") float BiteFacingAngle=15.f;
    bool GetCloseFacingYaw(float& Yaw) const;
    /** Unit ellipses expressed relative to the head bone, authored from each iris. */
    UPROPERTY(EditDefaultsOnly,Category="M10|Weakpoints") TArray<FTransform> EyeWeakpointFrames;
    UPROPERTY(EditAnywhere,Category="M10|Weakpoints",meta=(ClampMin="0",ClampMax="1")) float RangedBodyDamageMultiplier=.7f;
    UPROPERTY(EditAnywhere,Category="M10|Bite",meta=(Units="cm")) float BiteLungeDistance=150.f;
    bool IsWeakpointHit(const FHitResult& Hit) const;
private:
    float DamageSurfaceMultiplier(const FDamageEvent& Event) const;
    void AdvanceBiteLunge(float Seconds);
    float BiteLungeProgress=0.f;
public:
    UPROPERTY(EditDefaultsOnly,Category="M10|Howl") TObjectPtr<UAnimSequence> HowlClip;
    UPROPERTY(EditDefaultsOnly,Category="M10|Howl") TObjectPtr<USoundBase> HowlSound;
    UPROPERTY(EditDefaultsOnly,Category="M10|Howl") TObjectPtr<UStaticMesh> HowlWaveMesh;
    UPROPERTY(EditDefaultsOnly,Category="M10|Howl") TObjectPtr<UMaterialInterface> HowlWaveMaterial;
    UPROPERTY(EditAnywhere,Category="M10|Howl",meta=(Units="cm",ClampMin="1")) float HowlRange=1000.f;
    UPROPERTY(EditAnywhere,Category="M10|Howl",meta=(Units="deg",ClampMin="1",ClampMax="180")) float HowlAngle=120.f;
    UPROPERTY(EditAnywhere,Category="M10|Howl",meta=(ClampMin="0")) float HowlDamagePerTick=27.5f;
    UPROPERTY(EditAnywhere,Category="M10|Howl",meta=(Units="s",ClampMin="0")) float HowlCooldown=30.f;
private:
    // Authored clip: 0.6 s windup, [0.6,3.6) channel, 0.6 s recovery.
    static constexpr float HowlWindup=.6f;
    static constexpr float HowlChannel=3.f;
    static constexpr float HowlInterval=.5f;
    static constexpr float HowlRecovery=.6f;
    bool CanBite(APawn* Victim) const;
    bool CanHowl(APawn* Victim) const;
    bool IsInHowlSector(const APawn* Victim) const;
    void TickHowl();
    void DealHowl();
    void PrepareHowlPresentation();
    void UpdateHowlPresentation(float Seconds);
    void StopHowlPresentation();
    UPROPERTY() TObjectPtr<UAudioComponent> HowlVoice;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> HowlWaves;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> HowlMaterials;
    UPROPERTY(Replicated) double HowlStartedAt=0.;
    float HowlCooldownLeft=2.f;
    int32 NextHowlPulse=0;
    bool bHowlVoiceStarted=false;
public:
    UPROPERTY(EditDefaultsOnly,Category="M10|RearGas") TObjectPtr<UAnimSequence> RearGasClip;
    UPROPERTY(EditAnywhere,Category="M10|RearGas",meta=(Units="cm",ClampMin="1")) float RearGasTriggerRange=600.f;
    UPROPERTY(EditAnywhere,Category="M10|RearGas",meta=(Units="deg",ClampMin="1",ClampMax="180")) float RearGasTriggerAngle=120.f;
    UPROPERTY(EditAnywhere,Category="M10|RearGas",meta=(Units="s",ClampMin="0")) float RearGasCooldown=12.f;
    UPROPERTY(EditAnywhere,Category="M10|RearGas",meta=(ClampMin="0")) float RearGasDamagePerSecond=6.f;
    FVector RearGasOutlet(int32 Index=0) const;
private:
    static constexpr float RearGasWindup=1.2f;
    static constexpr float RearGasChannel=6.f;
    static constexpr float RearGasRecovery=.8f;
    void PrepareRearGas();
    bool CanRearGas(APawn* Victim) const;
    bool IsInRearGasRange(const APawn* Victim) const;
    void TickRearGas();
    void StopRearGas();
    UPROPERTY(Replicated) double RearGasStartedAt=0.;
    TWeakObjectPtr<AM10PoisonGas> ActiveRearGas;
    FVector RearGasLocalOutlets[3];
    int32 RearGasBone=INDEX_NONE;
    float RearGasCooldownLeft=0.f;
    bool bRearGasReleased=false;
public:
    /** Hold the nearer rear end only within gas range, independently of cooldowns. */
    bool PrefersRearAttack(const APawn* Victim) const;
};
