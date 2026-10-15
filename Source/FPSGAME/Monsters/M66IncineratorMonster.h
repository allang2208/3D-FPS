#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "M66IncineratorMonster.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UMonsterCombatComponent;
class UMonsterCorpseRagdollComponent;
class UCombatStatusFormula;
class UPhysicsAsset;
class AM66BackMist;
class UMaterialInterface;
class UNiagaraSystem;
class USoundBase;
class UM66FurnaceVisualComponent;
class UM66CorpseSyncComponent;
class UM66AudioComponent;
class USoundAttenuation;

UENUM()
enum class EM66Reaction : uint8 { None, Hit, Stunned, Airborne, Landing, Down, GetUp, Dying };
UENUM()
enum class EM66AttackKind : uint8 { Sweep, GroundSlam, FurnaceBreath };
USTRUCT()
struct FM66ReactionState
{
    GENERATED_BODY()
    UPROPERTY() EM66Reaction Phase=EM66Reaction::None;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() double EndsAt=0.;
    UPROPERTY() uint8 Direction=0;
    UPROPERTY() float DeathLead=.9f;
    UPROPERTY() bool bFromKnockdown=false;
};

USTRUCT()
struct FM66SweepFrame
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) float Time=0.f;
    UPROPERTY(EditAnywhere) TArray<FVector> Points;
};
USTRUCT()
struct FM66SweepClock
{
    GENERATED_BODY()
    UPROPERTY() bool Active=false;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() EM66AttackKind Kind=EM66AttackKind::Sweep;
    UPROPERTY() FRotator BreathAim=FRotator::ZeroRotator;
    UPROPERTY() bool bBreathAimLocked=false;
};

/** M66 navigation, alternating sweep/slam and authoritative reaction states. */
UCLASS(Blueprintable)
class FPSGAME_API AM66IncineratorMonster : public ACharacter
{
    GENERATED_BODY()
public:
    AM66IncineratorMonster(const FObjectInitializer& Initializer=FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void Landed(const FHitResult& Hit) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M66") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere,Category="M66") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;
    UPROPERTY(VisibleAnywhere,Category="M66") TObjectPtr<UM66CorpseSyncComponent> CorpseSync;
    void AcceptServerCorpse();
    UPROPERTY(VisibleAnywhere,Category="M66") TObjectPtr<UM66AudioComponent> BodyAudio;
    UPROPERTY(EditDefaultsOnly,Category="M66|Audio") TMap<FName,TObjectPtr<USoundBase>> BodySounds;
    UPROPERTY(EditDefaultsOnly,Category="M66|Audio") TObjectPtr<USoundAttenuation> BodyAudioAttenuation;
    UPROPERTY(EditDefaultsOnly,Category="M66|Audio") float BodyAudioGain=.8f;
    UPROPERTY(VisibleAnywhere,Category="M66") TObjectPtr<UCombatStatusFormula> Status;
    UPROPERTY(EditDefaultsOnly,Category="M66|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly,Category="M66|Assets") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Assets") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Assets") TObjectPtr<UAnimSequence> TurnLeftClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Assets") TObjectPtr<UAnimSequence> TurnRightClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Attack") TObjectPtr<UAnimSequence> SweepClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Attack") TArray<FM66SweepFrame> SweepFrames;
    UPROPERTY(EditDefaultsOnly,Category="M66|Attack") FTransform SweepReferenceRoot=FTransform::Identity;
    UPROPERTY(EditAnywhere,Category="M66|Attack",meta=(ClampMin="0")) float SweepDamage=40.f;
    UPROPERTY(EditAnywhere,Category="M66|Attack",meta=(ClampMin="1",Units="cm")) float SweepTriggerRange=300.f;
    UPROPERTY(EditDefaultsOnly,Category="M66|Attack",meta=(ClampMin="1",Units="cm")) float SweepHitRadius=16.f;
    UPROPERTY(EditAnywhere,Category="M66|Attack",meta=(ClampMin="2.6",Units="s")) float SweepCooldown=3.6f;
    UPROPERTY(EditDefaultsOnly,Category="M66|GroundSlam") TObjectPtr<UAnimSequence> SlamClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|GroundSlam") TArray<FM66SweepFrame> SlamFrames;
    UPROPERTY(EditDefaultsOnly,Category="M66|GroundSlam") FTransform SlamReferenceRoot=FTransform::Identity;
    UPROPERTY(EditAnywhere,Category="M66|GroundSlam",meta=(ClampMin="0")) float SlamDamage=135.f;
    UPROPERTY(EditAnywhere,Category="M66|GroundSlam",meta=(ClampMin="1",Units="cm")) float SlamTriggerRange=330.f;
    UPROPERTY(EditDefaultsOnly,Category="M66|GroundSlam",meta=(ClampMin="1",Units="cm")) float SlamHitRadius=32.f;
    UPROPERTY(EditAnywhere,Category="M66|GroundSlam",meta=(ClampMin="3.5",Units="s")) float SlamCooldown=6.f;
    UPROPERTY(EditAnywhere,Category="M66|GroundSlam",meta=(ClampMin="1",Units="cm")) float SlamAreaRadius=400.f;
    UPROPERTY(EditAnywhere,Category="M66|GroundSlam",meta=(ClampMin=".1",Units="s")) float SlamWaveSeconds=.55f;
    UPROPERTY(EditAnywhere,Category="M66|GroundSlam",meta=(ClampMin="0",Units="s")) float SlamStunSeconds=2.f;
    UPROPERTY(EditDefaultsOnly,Category="M66|GroundSlam") TObjectPtr<UMaterialInterface> SlamWaveMaterial;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") TObjectPtr<UAnimSequence> BreathClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") TObjectPtr<UNiagaraSystem> BreathSystem;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") TObjectPtr<UMaterialInterface> BreathGlowMaterial;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") TObjectPtr<USoundBase> BreathSound;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") TObjectPtr<USoundBase> BreathInhaleSound;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") FName BreathMouthMorph=TEXT("M66_FurnaceOpen");
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") FVector BreathMouthOffset=FVector::ZeroVector;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") FTransform BreathReferenceRoot=FTransform::Identity;
    UPROPERTY(EditDefaultsOnly,Category="M66|Furnace") TArray<FVector> BreathMouthSamples;
    UPROPERTY(EditAnywhere,Category="M66|Furnace",meta=(ClampMin="0")) float BreathDamage=25.f;
    UPROPERTY(EditAnywhere,Category="M66|Furnace",meta=(Units="cm",ClampMin="1")) float BreathRange=900.f;
    UPROPERTY(EditAnywhere,Category="M66|Furnace",meta=(Units="cm",ClampMin="0")) float BreathMinimumRange=400.f;
    UPROPERTY(EditAnywhere,Category="M66|Furnace",meta=(ClampMin="1",ClampMax="90")) float BreathArcDegrees=35.f;
    UPROPERTY(EditAnywhere,Category="M66|Furnace",meta=(Units="s",ClampMin="3.4")) float BreathCooldown=12.f;
    UPROPERTY(VisibleAnywhere,Category="M66|Furnace") TObjectPtr<UM66FurnaceVisualComponent> BreathVisuals;
    UPROPERTY(EditAnywhere,Category="M66|BackSmoke") bool bEnableBackSmoke=true;
    UPROPERTY(EditAnywhere,Category="M66|BackSmoke",meta=(ClampMin="50",Units="cm")) float BackSmokeRadius=260.f;
    UPROPERTY(EditAnywhere,Category="M66|BackSmoke",meta=(ClampMin=".1",Units="s")) float BackSmokeBlindSeconds=2.f;
    UPROPERTY(EditAnywhere,Category="M66|BackSmoke",meta=(ClampMin=".1",Units="s")) float BackSmokeHoldSeconds=8.f;
    FVector BackSmokeOutlet(int32 Index) const;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TArray<TObjectPtr<UAnimSequence>> HitClips;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TObjectPtr<UAnimSequence> StunClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TObjectPtr<UAnimSequence> AirClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TObjectPtr<UAnimSequence> LandClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TObjectPtr<UAnimSequence> GetUpClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditDefaultsOnly,Category="M66|Reactions") TObjectPtr<UPhysicsAsset> ReactionPhysics;
    UPROPERTY(EditAnywhere,Replicated,Category="M66|Stats") float MaxHealth=6000.f;
    UPROPERTY(VisibleAnywhere,Replicated,Category="M66|Stats") float Health=6000.f;
    UPROPERTY(EditAnywhere,Category="M66|Stats") int32 Level=12;
    UPROPERTY(EditAnywhere,Category="M66|Stats") EMonsterRank Rank=EMonsterRank::Boss;
    UPROPERTY(EditAnywhere,Category="M66|Stats") int32 ExperienceReward=0;
    UPROPERTY(EditAnywhere,Category="M66|Death") float CorpseSeconds=25.f;
    UPROPERTY(EditAnywhere,Category="M66|Movement",meta=(ClampMin="1",Units="cm/s")) float WalkSpeed=160.f;
    UPROPERTY(EditAnywhere,Category="M66|Movement",meta=(ClampMin="1",Units="cm/s")) float ReturnSpeed=130.f;
    UPROPERTY(EditAnywhere,Category="M66|Movement",meta=(ClampMin="1")) float TurnSpeed=100.f;
    UPROPERTY(EditDefaultsOnly,Category="M66|Animation",meta=(ClampMin="1",Units="cm")) float StrideDistance=144.f;
    UPROPERTY(EditDefaultsOnly,Category="M66|Animation",meta=(ClampMin="1")) float TurnStrideDegrees=60.f;
    UPROPERTY(EditAnywhere,Category="M66|AI",meta=(Units="cm")) float AggroRadius=2200.f;
    UPROPERTY(EditAnywhere,Category="M66|AI",meta=(Units="cm")) float LeashRadius=3200.f;
    UPROPERTY(EditAnywhere,Category="M66|AI",meta=(Units="cm")) float StoppingDistance=230.f;
    FVector Home=FVector::ZeroVector;
    void SetLocomotion(bool Moving,bool Returning);
    bool Dead() const {return Health<=0.f||Reaction.Phase==EM66Reaction::Dying;}
    bool IsWeakpointHit(const FHitResult& Hit) const;
    bool IsKnockedDown() const;
    bool Controlled() const {return !Dead()&&Reaction.Phase!=EM66Reaction::None;}
    bool Busy() const {return Dead()||Controlled()||Sweep.Active;}
    void SetCombatTarget(APawn* Pawn) { CombatTarget=Pawn; }
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    void CancelAttack() { StopSweep(); }
    bool DesiredCombatFacing(float& Yaw) const;
    bool IsSweeping() const {return Sweep.Active&&!Dead()&&!Controlled();}
    bool IsGroundSlamming() const {return IsSweeping()&&Sweep.Kind==EM66AttackKind::GroundSlam;}
    bool IsBreathing() const {return IsSweeping()&&Sweep.Kind==EM66AttackKind::FurnaceBreath;}
    bool DesiredBreathFacing(float& Yaw) const;
    void FurnaceBreathFrame(FVector& Origin,FQuat& Rotation) const;
    UAnimSequence* ActiveAttackClip() const {return Sweep.Kind==EM66AttackKind::FurnaceBreath?BreathClip:(Sweep.Kind==EM66AttackKind::GroundSlam?SlamClip:SweepClip);}
    uint32 SweepSerial() const {return Sweep.Serial;}
    float SweepAge() const;
    EM66Reaction ReactionPhase() const {return Reaction.Phase;}
    uint32 ReactionSerial() const {return Reaction.Serial;}
    bool HoldKnockdownDeathPose() const
    {return !HasAuthority()&&Reaction.Phase==EM66Reaction::Dying&&Reaction.bFromKnockdown&&!bDeathHandoff;}
    UAnimSequence* ReactionClip(float& Seconds,bool& Loop) const;
    void InterruptAttack(float Seconds);
    void FinishHitReaction();
    void ExtendControl(float Seconds);
    bool StartLaunch(APawn* Attacker,const FVector& Velocity,float HoldSeconds);
    UFUNCTION(BlueprintCallable,Category="M66|Authoring") static UPhysicsAsset* BuildReactionPhysics(USkeletalMesh* InMesh);
private:
    void ApplyRig();
    void PrepareCleftWeakpoint(const TArray<FTransform>& ReferencePose);
    FMatrix CleftBoneToSource[2];
    bool bCleftFrameReady=false;
    void PrepareBackSmokeOutlets();
    void StartBackSmoke();
    void StopBackSmoke();
    double ActionClock() const;
    float ReactionAge() const;
    void SetReaction(EM66Reaction Phase,float AlreadyElapsed=0.f);
    void TickReaction(float DeltaSeconds);
    void RefreshPoseTick();
    void TickSweep();
    void StopSweep();
    bool HasSweepSight(const APawn* Victim) const;
    bool CanUseAttack(const APawn* Victim,bool GroundSlam) const;
    bool SweepCanReach(const APawn* Victim,bool GroundSlam=false) const;
    FVector SweepPointWorld(const FVector& Point,bool GroundSlam=false) const;
    void SweepContact(int32 FrameIndex);
    bool FindSlamGround(FHitResult& Ground) const;
    bool SlamAreaCanReach(const APawn* Victim) const;
    void ReleaseSlamWave();
    bool CanUseBreath(const APawn* Victim) const;
    void TickBreath();
    void BreathHit();
    FVector MouthAtAge(float Age) const;
    void BeginDeath();
    void PresentDeath();
    UPROPERTY(ReplicatedUsing=OnRep_Reaction) FM66ReactionState Reaction;
    UFUNCTION() void OnRep_Reaction();
    UPROPERTY(ReplicatedUsing=OnRep_Sweep) FM66SweepClock Sweep;
    UFUNCTION() void OnRep_Sweep();
    TWeakObjectPtr<APawn> CombatTarget;
    TSet<TWeakObjectPtr<AActor>> SweepVictims;
    double NextSweepAt=0.;
    double NextSlamAt=0.,NextAttackAt=0.;
    double NextBreathAt=0.,NextBreathAimUpdate=0.;
    int32 NextBreathHit=0;
    bool bPreferSlam=false;
    bool bSlamReleased=false;
    int32 NextSweepFrame=0;
    double ControlUntil=0.;
    uint8 LastHitDirection=0;
    bool bDeathPrepared=false,bDeathHandoff=false,bDeathFallback=false;
    int32 BackSmokeBones[4]={INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE};
    FVector BackSmokeLocalOutlets[4]{};
    UPROPERTY(Transient) TObjectPtr<AM66BackMist> BackMist;
};
