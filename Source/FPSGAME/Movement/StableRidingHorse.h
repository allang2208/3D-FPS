#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AI/Navigation/NavigationTypes.h"
#include "FPSStaminaTuning.h"
#include "HorseRosterTypes.h"
#include "StableRidingHorse.generated.h"

class UAnimSequence;
class UStableHoofstepNotify;
class UAnimSequenceBase;
class AFPSGAMECharacter;
class UCapsuleComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
struct FStableTackBonuses;

UENUM()
enum class EStableHorseVisit : uint8 { Present, Departing, Arriving };

UENUM()
enum class EStableJumpPhase : uint8 { Grounded, Gathering, Airborne, Landing };

UENUM()
enum class EStableShowcaseState : uint8
{
    StallFeed,
    StallIdle,
    StallLook,
    RoamIdle,
    RoamLook,
    RoamGraze,
    RoamTurn,
    RoamWalk
};

USTRUCT()
struct FStableHorseJump
{
    GENERATED_BODY()
    UPROPERTY() EStableJumpPhase Phase=EStableJumpPhase::Grounded;
    UPROPERTY() double Since=0.;
    UPROPERTY() float TimeToApex=0.f;
};

/** The placed stable resident is the mount throughout its lifetime. */
UCLASS()
class FPSGAME_API AStableRidingHorse : public ACharacter
{
    GENERATED_BODY()
public:
    AStableRidingHorse(const FObjectInitializer& ObjectInitializer=FObjectInitializer::Get());
    FQuat GroundTilt() const;
    FVector GroundOffset() const;
    void BeginPlay() override;
    void EndPlay(EEndPlayReason::Type Reason) override;
    void Tick(float Delta) override;
    void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
    bool PlayingCanter() const { return CanterAnimation && CurrentClip==CanterAnimation; }
    bool InJump() const { return JumpState.Phase!=EStableJumpPhase::Grounded; }
    float GetPivotWeight() const { return PivotWeight; }
    bool IsSteppingInPlace() const { return FMath::Abs(PivotWeight)>.12f; }
    float GetHealth() const { return Health; }
    float GetStamina() const { return Stamina; }
    float GetMaximumStamina() const { return MaxStamina; }
    void ShareRiderHealthLoss(float AcceptedDamage);
    float GetMaximumHealth() const { return MaxHealth; }
    uint8 GetEquippedTackMask() const { return EquippedTackMask; }
    void SetEquippedTackMask(uint8 NewMask);
    FStableTackBonuses TackBonuses() const;
    const FStableHorseAffixBonuses& Affixes() const { return AffixBonuses; }
    float MountedDamageReduction() const;
    bool IsRetreating() const { return Health<=0.f || RetreatStartedAt>=0.; }
    float TakeDamage(float Amount,const FDamageEvent& Event,AController* InstigatorController,AActor* Causer) override;
    void BeginRiddenJump();
    uint8 HomeStall() const;
    bool ResolveIdentity();
    FGuid Identity() const {return IndividualId;}
    FGuid SourceIdentity() const {return OriginId;}
    bool HasActiveKeeper() const {return KeeperModel.IsValid();}
    bool RecordClaim(FGuid Owner,FGuid Id,uint8 EntryBirthVersion);
    const TCHAR* HorseName() const {return FStableHorseTraits::Name(IndividualId,BirthVersion);}
    void ApplyEarnedLevel(const FStableMountRecord& Entry);
    bool NeedsRecall() const {return bNeedsRecall;}
    bool IsFarFrom(const APawn& Pawn) const;
    static constexpr double FarDistance=4000.;
    FStableMountRecord Condition() const;
    void RestoreCondition(const FStableMountRecord& Saved);
    void ApplyPotionHealth(float After);
    EStableHorseVisit Visit() const {return VisitState;}
    const FGuid& Keeper() const {return KeeperProfile;}
    void SetKeeper(class UColdSteelStatusModel& Model,const FStableMountRecord& Entry);
    void CacheKeeperCondition(bool bSave=false);
    void BeginVisit(EStableHorseVisit Phase,AFPSGAMECharacter* KeeperPawn);
    void ApplyHorseFade(float Fade);
    bool IsMarketShowcase() const { return bMarketShowcase; }
    bool IsShowcaseFading() const { return bMarketShowcase && ShowcaseFadeDir!=0; }
    bool IsShowcaseFadingOut() const { return bMarketShowcase && ShowcaseFadeDir>0; }
    int32 MarketShowcasePrice() const { return ShowcasePrice; }
    void MarkMarketShowcase() { bMarketShowcase=true; }
    void ConfigureMarketShowcase(const struct FStableHorseOffer& Offer,bool bInStall,bool bCanFeed,
                                 const TArray<UAnimSequence*>& AmbientClips,float InitialPhase,bool bFadeIn,
                                 const FTransform& InVillageToWorld,const FVector2D& InLocalRoamMin,const FVector2D& InLocalRoamMax);
    void BeginShowcaseFadeOut();
    void Landed(const FHitResult& Hit) override;
    FVector Saddle() const;
    FVector Stirrup(bool bLeft) const;
    void SetRider(AFPSGAMECharacter* NewRider);
    AFPSGAMECharacter* GetRider() const { return Rider; }
    AFPSGAMECharacter* GetLeader() const { return Leader; }
    void SetLeader(AFPSGAMECharacter* NewLeader, bool bParkAfterArrival = false);
    float EffectiveStopDistanceTo(const FVector& TargetFeet, float ExtraMargin = 0.f) const;
    void Drive(float Forward, float Turn, bool bCanter);
    void Halt();
    void PlayHoofstep(const UStableHoofstepNotify& Contact, const UAnimSequenceBase* Clip);
    UPROPERTY(EditAnywhere,Category="Horse") TObjectPtr<UAnimSequence> StallAnimation;
    UPROPERTY(EditAnywhere,Category="Horse") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditAnywhere,Category="Horse") TObjectPtr<UAnimSequence> WalkAnimation;
    UPROPERTY(EditAnywhere,Category="Horse") TObjectPtr<UAnimSequence> CanterAnimation;
    UPROPERTY(EditDefaultsOnly,Category="Horse") TObjectPtr<UAnimSequence> JumpAnimation;
private:
    UPROPERTY(VisibleAnywhere,Category="Horse") TObjectPtr<class UStableManeComponent> Mane;
    UPROPERTY(VisibleAnywhere,Category="Horse|Collision") TObjectPtr<UCapsuleComponent> ForebodyCollision;
    UPROPERTY(VisibleAnywhere,Category="Horse|Collision") TObjectPtr<UCapsuleComponent> HindbodyCollision;
    UPROPERTY(VisibleAnywhere,Category="Horse|Collision") TObjectPtr<UCapsuleComponent> NeckCameraCollision;
    UPROPERTY(VisibleAnywhere,Category="Horse|Collision") TObjectPtr<UCapsuleComponent> HeadCameraCollision;
    void UpdateAuxiliaryCollision(bool bCameraBlocking, bool bPawnBlocking);
    UPROPERTY(EditDefaultsOnly,Category="Horse|Condition",meta=(ClampMin="1")) float MaxHealth=300.f;
    UPROPERTY(Replicated) float Health=300.f;
    UPROPERTY(EditDefaultsOnly,Category="Horse|Condition",meta=(ClampMin="1")) float MaxStamina=300.f;
    UPROPERTY(EditDefaultsOnly,Category="Horse|Condition",meta=(ClampMin="0")) float JumpDrainPerSecond=24.f;
    UPROPERTY(Replicated) float Stamina=300.f;
    FColdSteelStaminaTuning StaminaRates;
    float RecoveryWait=0.f;
    bool bExhausted=false;
    void UpdateStamina(float Delta,bool Running);
    float LoseHealth(float Amount);
    void ScheduleInjuryRecovery();
    UPROPERTY(Replicated) int8 PivotDegreesPerSecond=0;
    float PivotWeight=0.f;
    FTimerHandle RestRecoveryTimer;
    UPROPERTY(Replicated) double RetreatStartedAt=-1.;
    UPROPERTY() TObjectPtr<UAnimSequence> RearAnimation;
    UPROPERTY() TObjectPtr<class UMaterialInterface> CoatMaterial;
    UPROPERTY() TObjectPtr<class UMaterialInterface> FadedCoatMaterial;
    FGuid AppliedAppearance;
    FTimerHandle IdentityRetry;
    void ResolveInitialIdentity();
    void ApplyIndividualAppearance();
    TWeakObjectPtr<class UColdSteelStatusModel> KeeperModel;
    UPROPERTY(Replicated) FGuid KeeperProfile;
    UPROPERTY(EditInstanceOnly,Replicated,Category="Horse") uint8 RegisteredStall=0;
    UPROPERTY(ReplicatedUsing=OnRep_Individual) FGuid IndividualId;
    UPROPERTY(ReplicatedUsing=OnRep_Individual) uint8 BirthVersion=FStableHorseTraits::IndependentRolls;
    UPROPERTY(ReplicatedUsing=OnRep_Individual) int32 HorseLevel=1;
    UPROPERTY(ReplicatedUsing=OnRep_EquippedTack) uint8 EquippedTackMask=0;
    UFUNCTION() void OnRep_Individual();
    UFUNCTION() void OnRep_EquippedTack();
    void RefreshTackLimits(bool bScaleCurrentVitals);
    void RefreshTackVisuals();
    void SyncCoatMaterialAndFade();
    static constexpr int32 TackSlotCount=4;
    UPROPERTY() TObjectPtr<USkeletalMesh> TackMeshAssets[TackSlotCount];
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> TackVisuals;
    uint8 AppliedTackVisualMask=0xFF;
    float LastHorseFade=0.f;
    FStableHorseTraits Traits;
    FStableHorseAffixBonuses AffixBonuses;
    float NaturalRegenAccumulator=0.f;
    UPROPERTY(Replicated) bool bNeedsRecall=false;
    FGuid OriginId;
    FString ClaimSlot;
    double NextFollowFeedback=0.;
    double NoProgressSince=0.;
    FVector ProgressLocation=FVector::ZeroVector;
    void UpdateFollowFeedback(double Now,double Distance);
    UPROPERTY(ReplicatedUsing=OnRep_Visit) EStableHorseVisit VisitState=EStableHorseVisit::Present;
    UPROPERTY(Replicated) double VisitStartedAt=0.;
    TWeakObjectPtr<AFPSGAMECharacter> ArrivalLeader;
    float VisitTravelYaw=0.f;
    UFUNCTION() void OnRep_Visit();
    void TickVisit(float Delta);
    float EscapeYaw=0.f;
    double NextEscapeTurn=0.;
    bool bEscapeRunning=false,bFadeMaterialsApplied=false;
    void TickRetreat(float Delta);
    void RunFromDanger(float Delta);
    UPROPERTY(Replicated) FStableHorseJump JumpState;
    double JumpClock() const;
    void SetJumpPhase(EStableJumpPhase Next);
    void AdvanceJump(float Delta);
    void PoseJump();
    UPROPERTY(ReplicatedUsing=OnRep_Rider) TObjectPtr<AFPSGAMECharacter> Rider;
    UFUNCTION() void OnRep_Rider(AFPSGAMECharacter* PreviousRider);
    TWeakObjectPtr<AFPSGAMECharacter> RecentlyClearedRider;
    double RecentlyClearedUntil=0.;
    void UpdateClearedRiderCollision(double Now);
    UPROPERTY(Replicated) TObjectPtr<AFPSGAMECharacter> Leader;
    UPROPERTY(Replicated) bool bLeftStall=false;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentClip;
    int32 LastHoofVariation=INDEX_NONE;
    float Throttle=0.f, Steering=0.f;
    bool bWantsForwardCanter=false;
    UPROPERTY(ReplicatedUsing=OnRep_RiddenCanter) bool bRiddenCanter=false;
    UFUNCTION() void OnRep_RiddenCanter();
    void RefreshRiddenCanter();
    bool ClearBody(const FVector& Delta, const FRotator& DestinationRotation) const;
    bool IsBlockedByAnotherHorse(const FVector& MoveDir, bool bIncludeShowcase, const AStableRidingHorse** OutBlocker = nullptr) const;
    static double PointToHorseSegmentDistSq2D(const FVector& Point, const AStableRidingHorse& Horse);
    static bool SegmentClearsHorse2D(const FVector& From, const FVector& To, const AStableRidingHorse& Horse, double MinClearanceCm);
    void UpdateGait(float Delta);
    void Follow(float Delta,float MovementScale);
    void PlanFollowPath(const FVector& Goal);
    void FinishFollowQuery(uint32 Id,ENavigationQueryResult::Type Result,FNavPathSharedPtr Path);
    bool WalkableApproach(const FVector& Goal) const;
    bool CanHorseStandAt(const FVector& Ground, const FRotator& Heading, const AActor* IgnoreActor) const;
    bool ComputeRecallParkSpot(const AFPSGAMECharacter& TargetPawn, FVector& OutGoal, float& OutYaw) const;
    void ClearFollowRoute();
    FNavPathSharedPtr FollowPath;
    uint32 PendingQuery=0;
    int32 NextCorner=1;
    FVector PlannedGoal=FVector::ZeroVector;
    double NextPlanTime=0.;
    float BlockedSeconds=0.f;
    double NextFollowBlockCheck=0.;
    double FollowResumeCheckAt=0.;
    FVector FollowBlockAnchorLoc=FVector::ZeroVector;
    FVector FollowPausedPlayerLoc=FVector::ZeroVector;
    float FollowStalledSeconds=0.f;
    bool bFollowYieldPaused=false;
    bool bFollowBlockedByHorse=false;
    FVector LastGaitLocation=FVector::ZeroVector;
    bool bHasLastGaitLocation=false;
    float SmoothedActualSpeed=0.f;
    bool bFollowing=false,bAtHeel=false,bDirectApproach=false,bNavInvoker=false;
    bool bPreviouslyAllowedLedges=true;
    bool bRecallParking=false,bHasRecallParkGoal=false;
    FVector RecallParkGoal=FVector::ZeroVector;
    FVector RecallAnchorPlayer=FVector::ZeroVector;
    float RecallParkYaw=0.f;
    float RecallSettleSeconds=0.f;
    bool bMarketShowcase=false;
    bool bShowcaseCanRoam=false;
    bool bShowcaseCanFeed=false;
    int32 ShowcasePrice=0;
    int8 ShowcaseFadeDir=0;
    float ShowcaseFadeProgress=0.f;
    EStableShowcaseState ShowcaseState=EStableShowcaseState::StallIdle;
    double ShowcaseStateEndsAt=0.;
    double ShowcaseWalkStuckSince=0.;
    double NextShowcaseYieldScan=0.;
    double NextShowcaseClearCheck=0.;
    double ShowcaseMoveCooldownUntil=0.;
    double ShowcaseRetryWaitUntil=0.;
    uint8 ShowcaseBlockRetries=0;
    bool bCachedShowcaseYield=false;
    bool bCachedShowcaseForwardClear=true;
    float ShowcaseTurnStallSeconds=0.f;
    float LastShowcaseTurnYaw=0.f;
    FVector LastShowcaseTickLoc=FVector::ZeroVector;
    float SmoothedShowcaseSpeed=0.f;
    TWeakObjectPtr<const AStableRidingHorse> ShowcaseLastBlocker;
    FVector ShowcaseWalkProgressLoc=FVector::ZeroVector;
    FVector ShowcaseWalkGoal=FVector::ZeroVector;
    float ShowcaseWalkSpeed=160.f;
    FTransform ShowcaseVillageToWorld=FTransform::Identity;
    FVector2D ShowcaseLocalRoamMin=FVector2D::ZeroVector;
    FVector2D ShowcaseLocalRoamMax=FVector2D::ZeroVector;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ShowcaseClipFeed;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ShowcaseClipQIdle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ShowcaseClipQIdleLook;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ShowcaseClipQHeadLow;
    void EnterShowcaseState(EStableShowcaseState NextState);
    bool PickShowcaseRoamTarget(FVector& OutWorldGoal, const AStableRidingHorse* AvoidBlocker = nullptr) const;
    void PlayShowcaseClip(UAnimSequence* Clip,float Rate=1.f,float Phase=-1.f);
    void TickShowcase(float Delta);
    void UpdateHorseRayTracingVisibility(bool bForce = false);
    bool bHorseRTVisible = true;
    double NextHorseRTCheckAt = -1.;
};
