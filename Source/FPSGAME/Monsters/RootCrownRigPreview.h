#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "RootCrownRigPreview.generated.h"

class USkeletalMesh;
class UAnimSequence;
class UMonsterCombatComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UAudioComponent;
class USoundBase;
class UStaticMesh;
class UDynamicMeshComponent;
class ARootCrownRootField;
class ARootCrownNeedleProjectile;
class UMonsterCorpseRagdollComponent;
class UPhysicsAsset;
class URootCrownHitComponent;

UENUM()
enum class ERootCrownReaction : uint8 { None, Hit, Stunned, Airborne, Landing, Down, GetUp, Dying };

USTRUCT()
struct FRootCrownReactionState
{
    GENERATED_BODY()
    UPROPERTY() ERootCrownReaction Phase=ERootCrownReaction::None;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() double EndsAt=0.;
    UPROPERTY() uint8 Direction=0;
    UPROPERTY() float DeathLead=.65f;
};

USTRUCT()
struct FRootCrownEdgeFrame
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) float Time=0.f;
    UPROPERTY(EditAnywhere) TArray<FVector> Points;
};

USTRUCT()
struct FRootCrownSlashClock
{
    GENERATED_BODY()
    UPROPERTY() bool Active=false;
    UPROPERTY() uint32 Serial=0;
    UPROPERTY() double StartedAt=0.;
    UPROPERTY() float OpeningYaw=0.f;
    UPROPERTY() bool bNeedles=false;
    UPROPERTY() bool bRoots=false;
};

/** Root Crown locomotion stage; keeps the original asset/F6 identity. */
UCLASS(Blueprintable)
class FPSGAME_API ARootCrownRigPreview : public ACharacter
{
    GENERATED_BODY()
public:
    ARootCrownRigPreview(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void Landed(const FHitResult& Hit) override;
    virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Rig") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Combat") TObjectPtr<UPhysicsAsset> HitSurfacePhysics;
    UPROPERTY(VisibleAnywhere, Category="RootCrown|Combat") TObjectPtr<URootCrownHitComponent> HitDetection;
    UFUNCTION(BlueprintCallable, Category="RootCrown|Authoring")
    static UPhysicsAsset* BuildHitSurfacePhysics(USkeletalMesh* InMesh,const FString& AssetPath);
    bool IsWeakpointHit(const FHitResult& Hit) const;
    void RefreshPoseTick();
    void PresentGunContact(const FHitResult& Hit,const FVector& Direction,float Damage);
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Rig") TObjectPtr<UAnimSequence> PreviewAnimation;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Animation") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Animation") TObjectPtr<UAnimSequence> MoveClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Animation") TObjectPtr<UAnimSequence> TurnLeftClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Animation") TObjectPtr<UAnimSequence> TurnRightClip;
    UPROPERTY(EditAnywhere, Category="RootCrown|Movement", meta=(ClampMin="1",Units="cm/s")) float WalkSpeed=150.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Movement", meta=(ClampMin="1")) float TurnSpeed=150.f;
    // Authored stride values stay fixed when movement tuning changes.
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Animation", meta=(ClampMin="1")) float StrideDistance=90.f;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Animation", meta=(ClampMin="1")) float TurnStrideDegrees=72.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Movement") float AggroRadius=2200.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Movement") float LeashRadius=3200.f;
    UPROPERTY(VisibleAnywhere, Category="RootCrown|AI") TObjectPtr<UMonsterCombatComponent> Combat;
    FVector Home=FVector::ZeroVector;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Slash") TObjectPtr<UAnimSequence> SlashClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Slash") TArray<FRootCrownEdgeFrame> SlashFrames;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Slash") TObjectPtr<UMaterialInterface> SlashMaterial;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Slash") TObjectPtr<UMaterialInterface> SlashArcMaterial;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Slash") TObjectPtr<USoundBase> SlashGestureSound;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Slash") TObjectPtr<USoundBase> SlashContactSound;
    UPROPERTY(EditAnywhere, Category="RootCrown|Slash", meta=(ClampMin="0")) float SlashDamage=70.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Slash", meta=(ClampMin="0",Units="s")) float SlashCooldown=5.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Slash", meta=(ClampMin="1",Units="cm")) float SlashTriggerRange=800.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Slash", meta=(ClampMin="1",Units="cm")) float SlashHitRadius=44.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Slash", meta=(ClampMin="0",Units="cm")) float SlashKnockback=120.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Slash", meta=(ClampMin="1")) float SlashReachScale=2.f;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Needles") TObjectPtr<UAnimSequence> NeedleClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Needles") TObjectPtr<UStaticMesh> NeedleMesh;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Needles") TObjectPtr<UMaterialInterface> NeedleMaterial;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Needles") TObjectPtr<USoundBase> NeedleGestureSound;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Needles") TObjectPtr<USoundBase> NeedleImpactSound;
    UPROPERTY(EditAnywhere, Category="RootCrown|Needles", meta=(ClampMin="0")) float NeedleDamage=24.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Needles", meta=(ClampMin="0")) float NeedleCooldown=8.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Needles", meta=(ClampMin="0")) float NeedleMinRange=600.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Needles", meta=(ClampMin="1")) float NeedleMaxRange=1800.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Needles", meta=(ClampMin="1")) float NeedleSpeed=1600.f;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Roots") TObjectPtr<UAnimSequence> RootClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Roots") TObjectPtr<UStaticMesh> RootKnotMesh;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Roots") TObjectPtr<UMaterialInterface> RootFleshMaterial;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Roots") TObjectPtr<UMaterialInterface> RootWarningMaterial;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Mines") TObjectPtr<UMaterialInterface> MineSignalMaterial;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Roots") TObjectPtr<USoundBase> RootGestureSound;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Roots") TObjectPtr<USoundBase> RootBreakSound;
    UPROPERTY(EditAnywhere, Category="RootCrown|Roots", meta=(ClampMin="0")) float RootDamage=60.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Roots", meta=(ClampMin="1")) float RootKnotHealth=80.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Roots", meta=(ClampMin="1")) float RootCooldown=14.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Mines", meta=(ClampMin="1")) float MineTriggerRadius=140.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Mines", meta=(ClampMin="1")) float MineBlastRadius=280.f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Mines", meta=(ClampMin="0.1")) float MineFuseSeconds=.45f;
    UPROPERTY(EditAnywhere, Category="RootCrown|Mines", meta=(ClampMin="1")) float MineLifetime=25.f;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TArray<TObjectPtr<UAnimSequence>> HitClips;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<UAnimSequence> StunClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<UAnimSequence> AirClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<UAnimSequence> LandClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<UAnimSequence> GetUpClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<USoundBase> HitSound;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<USoundBase> LandSound;
    UPROPERTY(EditDefaultsOnly, Category="RootCrown|Reactions") TObjectPtr<USoundBase> DeathSound;
    UPROPERTY(EditAnywhere, Replicated, Category="RootCrown|Stats") float MaxHealth=4200.f;
    UPROPERTY(VisibleAnywhere, Replicated, Category="RootCrown|Stats") float Health=4200.f;
    UPROPERTY(EditAnywhere, Replicated, Category="RootCrown|Stats") int32 Level=12;
    UPROPERTY(EditAnywhere, Replicated, Category="RootCrown|Stats") EMonsterRank Rank=EMonsterRank::Boss;
    UPROPERTY(EditAnywhere, Category="RootCrown|Stats") int32 ExperienceReward=600;
    UPROPERTY(EditAnywhere, Category="RootCrown|Death") float CorpseSeconds=25.f;
    UPROPERTY(VisibleAnywhere, Category="RootCrown|Death") TObjectPtr<UMonsterCorpseRagdollComponent> CorpseRagdoll;
    bool Dead() const {return Health<=0.f||Reaction.Phase==ERootCrownReaction::Dying;}
    bool IsKnockedDown() const;
    bool StartLaunch(APawn* Attacker,const FVector& Velocity,float HoldSeconds);
    void ExtendControl(float Seconds);
    ERootCrownReaction ReactionPhase() const {return Reaction.Phase;}
    uint32 ReactionSerial() const {return Reaction.Serial;}
    UAnimSequence* ReactionClip(float& Seconds,bool& Loop) const;
    float ReactionAge() const;
    bool SamplingDeathHandoff() const {return Reaction.Phase==ERootCrownReaction::Dying&&ReactionAge()>=Reaction.DeathLead;}
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    bool IsSlashing() const {return IsAttacking() && !SlashClock.bNeedles && !SlashClock.bRoots;}
    bool IsNeedleFiring() const {return IsAttacking() && SlashClock.bNeedles;}
    bool IsRootEnclosing() const {return IsAttacking() && SlashClock.bRoots;}
    bool IsAttacking() const {return SlashClock.Active&&!Dead()&&Reaction.Phase==ERootCrownReaction::None;}
    UAnimSequence* CurrentAttackClip() const {return SlashClock.bRoots?RootClip:SlashClock.bNeedles?NeedleClip:SlashClip;}
    float CombatStoppingRange() const {return FMath::Max(225.f,SlashTriggerRange*.5f);}
    bool RegisterNeedleHit(uint32 Salvo,int32 Wave,AActor* Victim);
    bool Controlled() const {return !Dead()&&(Reaction.Phase!=ERootCrownReaction::None||(HasAuthority()&&ControlUntil>0.));}
    bool Busy() const {return Dead()||IsAttacking()||Controlled();}
    void SetTarget(APawn* Victim) {Target=Victim;}
    bool DesiredFacingYaw(float& Yaw) const;
    void InterruptAttack(float Seconds);
    void FinishHitReaction();
    float SlashAge() const;
    uint32 SlashSerial() const {return SlashClock.Serial;}
    double ActionClock() const;
private:
    void ApplyRig();
    bool CanSeeTarget(const APawn* Victim) const;
    bool CanSlash(APawn* Victim) const;
    bool CanNeedle(APawn* Victim) const;
    bool CanRoots(APawn* Victim) const;
    bool PrepareRootField(APawn* Victim);
    void CancelRootField();
    bool SlashCanReach(const APawn* Victim) const;
    FVector SlashPointWorld(const FVector& Point,bool Expanded,const FTransform& GroundedRoot) const;
    void InitializeNeedleOutlets();
    FVector NeedleMuzzle(int32 Wave) const;
    void UpdateSlashArc();
    void BuildSlashArc(int32 FrameIndex);
    void TickNeedles(float Age);
    void ReleaseNeedles(int32 Wave);
    void FinishSlash();
    void SlashContact(int32 FrameIndex);
    void TickReaction(float DeltaSeconds);
    void SetReaction(ERootCrownReaction Phase);
    void BeginDeath();
    void PresentDeath();
    void CancelFlyingNeedles();
    UPROPERTY(ReplicatedUsing=OnRep_Reaction) FRootCrownReactionState Reaction;
    UFUNCTION() void OnRep_Reaction();
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> ReactionVoice;
    UPROPERTY(ReplicatedUsing=OnRep_Slash) FRootCrownSlashClock SlashClock;
    double ControlUntil=0.;
    UFUNCTION() void OnRep_Slash();
    UFUNCTION(NetMulticast,Unreliable) void MulticastSlashContact(FVector_NetQuantize Location,double At);
    UFUNCTION(NetMulticast,Unreliable) void MulticastGunContact(FVector_NetQuantize Location,FVector_NetQuantizeNormal Direction,FName Bone,float Damage,double At);
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> TensionMaterial;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> SlashArc;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SlashArcMID;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> SlashVoice;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> ContactVoice;
    TWeakObjectPtr<APawn> Target;
    TSet<TWeakObjectPtr<AActor>> SlashVictims;
    FTransform ReferenceRoot=FTransform::Identity;
    double NextSlashAt=0.;
    int32 NextContactFrame=1;
    bool bContactSoundPlayed=false;
    double NextNeedleAt=0.;
    int32 NextNeedleWave=0;
    uint32 NeedleSalvo=0;
    FVector LockedNeedleAim=FVector::ZeroVector;
    FVector NeedleOutletLocal[3]{};
    uint32 SlashArcSerial=0;
    int32 SlashArcFrame=INDEX_NONE;
    bool bSlashArcGeometry=false;
    double NextRootsAt=0.;
    TWeakObjectPtr<ARootCrownRootField> RootField;
    TArray<TWeakObjectPtr<ARootCrownNeedleProjectile>> FlyingNeedles;
    uint8 LastHitDirection=0;
    bool bDeathPrepared=false,bDeathHandoff=false,bDeathFallback=false;
    uint32 PresentedReactionSerial=MAX_uint32;
    double LastGunContactAt=-1.;
    TSet<TWeakObjectPtr<AActor>> NeedleVictims[3];
};
