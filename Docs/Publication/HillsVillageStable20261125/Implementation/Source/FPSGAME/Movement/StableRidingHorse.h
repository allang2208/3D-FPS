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

UENUM()
enum class EStableHorseVisit : uint8 { Present, Departing, Arriving };

UENUM()
enum class EStableJumpPhase : uint8 { Grounded, Gathering, Airborne, Landing };

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
    void Landed(const FHitResult& Hit) override;
    FVector Saddle() const;
    FVector Stirrup(bool bLeft) const;
    void SetRider(AFPSGAMECharacter* NewRider);
    AFPSGAMECharacter* GetRider() const { return Rider; }
    AFPSGAMECharacter* GetLeader() const { return Leader; }
    void SetLeader(AFPSGAMECharacter* NewLeader);
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
    UFUNCTION() void OnRep_Individual();
    FStableHorseTraits Traits;
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
    void UpdateGait(float Delta);
    void Follow(float Delta,float MovementScale);
    void PlanFollowPath(const FVector& Goal);
    void FinishFollowQuery(uint32 Id,ENavigationQueryResult::Type Result,FNavPathSharedPtr Path);
    bool WalkableApproach(const FVector& Goal) const;
    void ClearFollowRoute();
    FNavPathSharedPtr FollowPath;
    uint32 PendingQuery=0;
    int32 NextCorner=1;
    FVector PlannedGoal=FVector::ZeroVector;
    double NextPlanTime=0.;
    float BlockedSeconds=0.f;
    bool bFollowing=false,bAtHeel=false,bDirectApproach=false,bNavInvoker=false;
    bool bPreviouslyAllowedLedges=true;
};
