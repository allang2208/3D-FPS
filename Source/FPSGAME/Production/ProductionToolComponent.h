#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ProductionResource.h"
#include "ProductionAxeImpactMotion.h"
#include "ProductionToolStats.h"
#include "../Weapons/PojunGrip.h"
#include "WarhammerHeavyMotion.h"
#include "../Weapons/TwoHandInspectAudio.h"
#include "FinalTollHeavyMotion.h"
#include "ThunderHammerThrow.h"
#include "ThunderHammerCall.h"
#include "WarhammerRiftState.h"
#include "RuneboundSealState.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "TimerManager.h"
#include "ProductionToolComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class UPrimitiveComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UAnimSequence;
class USceneComponent;
class USoundBase;
class UParticleSystem;
class UColdSteelPickupPrompt;
class UColdSteelStatusModel;
class UAzureDragonEnergyComponent;
class UDynamicMeshComponent;
class AThunderHammerThrown;
class ULineBatchComponent;
struct FColdSteelItem;
struct FStreamableHandle;

/** Local production-tool presentation. Profile owns inventory and depletion commits. */
UCLASS(ClassGroup=(Production),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UProductionToolComponent : public UActorComponent
{
    GENERATED_BODY()
    friend class UFPSConsumableAuditCommandlet;
    friend class UWarhammerSprintAuditCommandlet;
    friend class ULeapStrikeAuditCommandlet;
    friend class URuneSwordComponent;
    friend class UFPSCharacterMovementComponent;
    friend class UWarhammerModificationAuditCommandlet;
    friend class UThunderHammerRecallAuditCommandlet;
    friend class URuneSwordAuditCommandlet;
    friend class USkillNetworkAuditCommandlet;
    friend class URuneboundReviewAuditCommandlet;
    friend class ARuneboundReviewController;
    friend class ARuneboundReviewGameMode;
    friend class AThunderHammerWireController;
    friend class AThunderHammerWireGameMode;
    friend class AThunderHammerClosureController;
    friend class AThunderHammerClosureGameMode;
public:
    UProductionToolComponent();
    virtual void BeginPlay() override;
    void InitializeLocalTool();
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    bool IsRuneboundAwakened(const FColdSteelItem& Item) const;
    void RecordRuneboundHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit);
    void RecordStormDriveHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit);
    bool IsEquipped() const { return !EquippedId.IsEmpty(); }
    bool IsPojunChainOccupied() const;
    bool IsBusy() const { return IsPojunChainOccupied() || IsLeapStrikeActive() || IsThunderRecallLocked() || Elapsed>=0.f || EquipElapsed>=0.f || ThunderCallReleaseAge>=0.f || ThunderCatchAge>=0.f || bBluntCharging || bBluntReturningCharge || bBluntWhirlwind || bBluntUppercut || IsQuickCombatActive() || IsGuardActive(); }
    bool IsWarhammerEquipped() const { return IsEquipped() && Kind==TEXT("warhammer"); }
    bool IsGuardActive() const;
    bool HasAuthorityAttackInFlight() const;
    bool CanQueueGuard() const;
    bool CanStartGuard() const;
    void PrepareGuard();
    bool PresentGuardPose();
    void PlayGuardSound(bool Parried);
    bool BeginQuickCombat();
    bool IsQuickCombatActive() const;
    bool UsesConicalSeat() const { return bConicalSeat; }
    bool GetQuickCombatStrikeProbe(FVector& Origin,float PoseSeconds);
    bool IsEquipping() const { return EquipElapsed>=0.f; }
    /** Warhammer inspect: cosmetic real-time clock, never IsBusy; any action or movement break cancels it.
     *  L plays the full InspectV1; bWalking plays the accelerated shaft-turn half (InspectWalkSpeedV3). */
    bool BeginInspect(bool bWalking=false);
    void CancelInspect();
    bool IsInspecting() const { return InspectElapsed>=0.f; }
    USkeletalMeshComponent* ArmsMesh() const { return bUsesArms ? Viewmodel.Get() : nullptr; }
    bool GetEnchantmentBladeAttachment(USceneComponent*& Parent,FName& Socket,FTransform& LocalFrame,float& Length) const;
    void GetFlameArmorAttachments(struct FFlameArmorAttachmentBuffer& Out) const;
    void RefreshHeldTool();
    void BeginUse();
    void BeginPrimaryAttack();
    void ReleasePrimaryAttack();
    bool IsThunderHammerAway() const;
    bool IsThunderRecallLocked() const;
    bool QueueThunderWeaponSwitch();
    bool ValidateThunderEquipmentChange(const FColdSteelProfile& Before,const FColdSteelProfile& After,FString& Reason) const;
    void CommitThunderEquipmentChange(const FColdSteelProfile& State);
    bool GetThunderCatchFrame(FTransform& Frame) const;
    void ThunderHammerReturned(AThunderHammerThrown* Hammer,bool bCaught);
    float HeavyChargeFraction() const;
    bool IsHeavyCharging() const;
    bool IsThunderCalling() const;
    bool OwnsThunderCallResources() const {return IsThunderCalling()||bThunderCallResourcesDirty;}
    bool IsHeavyChargeConsumingStamina() const {return bThunderCallSeat?IsThunderCalling():IsHeavyCharging();}
    void NoteThunderCallResourcesSpent(){bThunderCallResourcesDirty=true;}
    void CancelHeavyCharge();
    float DashReadyFraction() const;
    bool TryBeginSprintAttack();
    bool GetCommittedSprintMovement(uint32 AttackId,FVector& Direction,float& DistanceCM,float& LimitCM,float& RecoverySeconds) const;
    bool IsSprintMovementPending(uint32 AttackId) const {return AttackId&&int32(AttackId-BluntLastServerRequestId)>0;}
    bool BeginWhirlwind();
    bool IsWhirlwindActive() const { return bBluntWhirlwind; }
    bool BeginUppercut();
    bool IsPojunUppercutStride() const { return bBluntUppercut&&PojunAttack!=PojunGrip::EAttack::Ordinary&&PojunSlashTime<0.f; }
    bool IsUppercutActive() const { return bBluntUppercut; }
    FString UppercutStatusText() const;
    bool BeginLeapStrike();
    void SetLeapAimPreview(bool Active);
    void ReleaseLeapAimPreview();
    bool IsLeapAimPreviewActive() const {return bLeapAimPreview;}
    bool ClampLeapStrikeView(FRotator& View);
    /** Actual takeoff through landing; includes an interrupted leap's remaining fall. */
    bool IsLeapControlImmune() const;
    bool IsLeapStrikeActive() const {return bLeapStrike||bLeapPending;}
    FString LeapStrikeStatusText(bool IncludeNotice=true) const;
    float GetLeapStrikeAge() const {return LeapAge;}
    float GetLeapStrikePoseRate() const {return LeapPoseRate;}
    bool GetGroundSlamCameraPitch(float& Pitch,float& Weight) const;
    bool GetGroundSlamCameraLocation(FVector& Point) const;
    bool ConstrainLeapStrikeView(FVector& WorldPoint) const;
    void UpdateLeapStrikeCamera(FVector& WorldPoint,float Delta);
    bool IsGroundSlamActive() const;
    /** Right-click while a shovel is out: raise one 20 cm layer, spending soil. */
    void BeginRefill();
    void CancelUse();
    void ShowFeedback(const FString& Message);
    /** Owner advances the shared hit/pose clock before composing its camera. */
    void AdvanceActionBeforeCamera(float Delta);
    void GetCameraMotion(FVector& Location,FRotator& Rotation) const;
    UPROPERTY(EditAnywhere,Category="Production",meta=(ClampMin="100",ClampMax="500",Units="cm")) float Reach = 320.f;
    // Camera-space travel and angles around the accepted two-hand idle hold.
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion",meta=(Units="cm")) FVector AxeWalkTravelCM=FVector(.3f,.8f,.55f);
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion",meta=(Units="cm")) FVector AxeRunTravelCM=FVector(.65f,2.8f,1.65f);
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion") FRotator AxeWalkAngles=FRotator(.3f,.35f,.65f);
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion") FRotator AxeRunAngles=FRotator(1.2f,1.2f,2.4f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion",meta=(Units="cm")) FVector PickaxeWalkTravelCM=FVector(.3f,.7f,.5f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion",meta=(Units="cm")) FVector PickaxeRunTravelCM=FVector(.55f,2.3f,1.35f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion") FRotator PickaxeWalkAngles=FRotator(.3f,.3f,.55f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion") FRotator PickaxeRunAngles=FRotator(1.f,1.f,2.f);
private:
    bool bThunderCallSeat=false,bThunderCallResourcesDirty=false;
    bool bThunderCallHoldConfirmed=false;
    float ThunderCallReleaseAge=-1.f,ThunderCallPreviewWait=0.f;
    int64 ThunderCallResourceRevision=0;
    UPROPERTY(Replicated) bool bThunderCallCharging=false;
    UPROPERTY(Replicated) double ThunderCallVisualStartedAt=0.;
    UPROPERTY(Replicated) float ThunderCallVisualSeconds=2.f;
    UPROPERTY(Transient) TObjectPtr<class UDecalComponent> ThunderCallDecal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ThunderCallAimMID;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ThunderCallChargeSound;
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> ThunderCallChargeAudio;
    bool bThunderCallAudioActive=false;
    float ThunderCallChargeProgress() const;
    void TickThunderCallAudio();
    void StopThunderCallAudio();
    void TickThunderCall(float Delta);
    void ReleaseThunderCall();
    void FinishThunderCallResources();
    void ClearThunderCallVisual();
    UFUNCTION(Server,Reliable) void ServerConfirmThunderCall(uint32 AttackId);
    UFUNCTION(Server,Reliable) void ServerReleaseThunderCall(uint32 AttackId,FVector_NetQuantize Point);
    UFUNCTION(Client,Reliable) void ClientThunderCallResult(uint32 AttackId,bool Accepted);
    UFUNCTION(Client,Reliable) void ClientThunderCallResources(int64 Revision,float Mana,float Stamina,float RecoveryDelay,bool Exhausted,double CrystalManaTotal);
    bool bThunderThrowSeat=false,bThunderRecallPending=false;
    bool bThunderSwitchQueued=false;
    FString ThunderActionInstance;
    void ServiceThunderLifecycle();
    float ThunderMagicSnapshot=-1.f,ThunderCatchAge=-1.f,ThunderReachAge=-1.f,ThunderPreviewWait=0.f;
    UPROPERTY(ReplicatedUsing=OnRep_ThunderAway) FString ThunderAwayInstance;
    UPROPERTY(ReplicatedUsing=OnRep_ThunderCatch) double ThunderCatchStartedAt=-100.;
    UPROPERTY(Replicated) TObjectPtr<AThunderHammerThrown> ThrownHammer;
    UPROPERTY(Transient) TObjectPtr<ULineBatchComponent> ThunderPreview;
    TArray<FVector> ThunderPreviewPoints;
    bool UsesThunderThrowHeavy() const {return bThunderThrowSeat&&bBluntHeavy&&!bBluntSprintAttack;}
    bool HandleThunderPrimary();
    bool LaunchThunderHammer(const FColdSteelSkillShot& Shot,float Magic);
    void TickThunderThrow(float Delta);
    bool PresentThunderCatch(float Delta);
    UFUNCTION() void OnRep_ThunderAway(const FString& Previous);
    UFUNCTION() void OnRep_ThunderCatch();
    UFUNCTION(Server,Reliable) void ServerRecallThunderHammer();
    UFUNCTION(Client,Reliable) void ClientThunderRecallRejected();
    bool UsesFinalTollHeavy() const;
    void AdvanceFinalTollHeavy(float Delta);
    void RecordFinalTollHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit);
    float FinalTollToughnessMultiplier(const FColdSteelSkillShot& Shot,AActor* Target) const;
    void PublishFinalTollSeals();
    void ReconcileFinalTollSeals(bool Active);
    UFUNCTION() void OnRep_FinalTollSeals();
    UPROPERTY(ReplicatedUsing=OnRep_FinalTollSeals) FRuneboundSealSnapshot FinalTollSealState;
    bool bFinalTollSealsDirty=true;
    UFUNCTION(NetMulticast,Unreliable) void MulticastFinalTollSeal(const FString& Instance,AActor* Target,FVector_NetQuantize Point,double At,bool Complete,uint32 Serial);
    struct FFinalTollMark { TWeakObjectPtr<AActor> Target;double Expires=0.,Started=0.;uint32 Serial=0;FVector LocalPoint=FVector::ZeroVector; };
    struct FFinalTollReceipt { TWeakObjectPtr<AActor> Target;uint32 Serial=0; };
    TArray<FFinalTollReceipt> FinalTollRecentHits;
    struct FFinalTollVisualMark { TWeakObjectPtr<AActor> Target;double Expires=0.,Started=0.;FVector LocalPoint=FVector::ZeroVector;bool Complete=false; };
    TArray<FFinalTollMark> FinalTollMarks;
    TArray<FFinalTollVisualMark> FinalTollVisualMarks;
    bool bFinalTollHead=false,bFinalTollVisual=false;
    bool bConicalSeat=false;
    FVector ConicalStrikeLocal=FVector::ZeroVector;
    bool bPojunGrip=false,bPojunZhufengRune=false;
    UPROPERTY(Transient) TObjectPtr<class UBeiweiSwordTrailComponent> PojunRuneTrail;
    bool ChixiaoTrailActive() const;
    bool ZhufengTrailActive() const;
    void UpdatePojunRuneTrail(bool Present);
    FVector PojunBladeBase=FVector::ZeroVector,PojunBladeTip=FVector::ZeroVector;
    TOptional<FVector> PojunStrikeLocal;
    uint8 FinalTollStrikes=0;
    uint32 FinalTollHeavySerial=0;
    double FinalTollCommitUntil=0.;
    float FinalTollActionRate=1.f;
    FTimerHandle FinalTollContactTimer;
    void TickRunebound(float Delta);
    void UpdateRuneboundPresentation(float Delta,bool Equipped);
    void ClearRuneboundPresentation();
    double RuneboundClock() const;
    void QueueRuneboundDetonation(const FHitResult& Hit,const FColdSteelSkillShot& Shot);
    UFUNCTION(NetMulticast,Unreliable) void MulticastRuneboundImpact(const FString& Instance,uint32 AttackSerial,double ServerAt,bool bDetonation);
    struct FRuneboundHitBurst
    {
        double ServerAt=-100.;
        uint32 AttackSerial=0;
        FVector Origin=FVector::ZeroVector;
        FQuat Rotation=FQuat::Identity;
        bool bHasOrigin=false;
        bool bDetonation=false,bFinalToll=false;
    };
    TArray<FRuneboundHitBurst> RuneboundHitBursts;
    UPROPERTY(Replicated) FString RuneboundInstance;
    UPROPERTY(Replicated) uint8 RuneboundCharge=0;
    UPROPERTY(Replicated) double RuneboundActiveUntil=0.;
    UPROPERTY(Replicated) float RuneboundActivationSeconds=20.f;
    TArray<uint32> RuneboundRecentAttacks;
    int32 RuneboundDetonationHits=0;
    UPROPERTY(Transient) TObjectPtr<UAzureDragonEnergyComponent> RuneboundHud;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> RuneboundMotes;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> FinalTollLightningMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FinalTollLightningMID;
    TWeakObjectPtr<UStaticMeshComponent> FinalTollLightningHead;
    float FinalTollLightningRefresh=0.f;
    void UpdateFinalTollLightning(float Delta,bool Equipped);
    void UpdateStormDriveLightning(float Delta);
    void ClearStormDriveLightning();
    UFUNCTION(NetMulticast,Unreliable) void MulticastStormDriveImpact(AActor* Target,FVector Point,FVector Normal,uint32 Seed,double ServerAt);
    struct FStormDriveBurst
    {
        TWeakObjectPtr<AActor> Target;
        FVector LocalPoint=FVector::ZeroVector,WorldPoint=FVector::ZeroVector,Normal=FVector::UpVector;
        double ServerAt=-100.;
        uint32 Seed=0;
    };
    FStormDriveBurst StormDriveBursts[4];
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> StormDriveMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> StormDriveMIDs;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> StormDriveMaterial;
    TWeakObjectPtr<UStaticMeshComponent> StormDriveSeat;
    TSharedPtr<FStreamableHandle> StormDriveLoad;
    float StormDriveSeatRefresh=0.f,StormDriveShapeRefresh=0.f;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> RuneboundMoteMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RuneboundMoteMID;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> RuneboundRuneMIDs;
    TSharedPtr<FStreamableHandle> RuneboundAssetLoad;
    UPROPERTY(Transient) TArray<TObjectPtr<UDynamicMeshComponent>> WarhammerRiftMeshes;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WarhammerRiftMIDs;
    WarhammerRift::FTrail WarhammerRiftTrails[WarhammerRift::PoolSize];
    TWeakObjectPtr<UStaticMeshComponent> WarhammerRiftHead;
    TWeakObjectPtr<UAnimSequence> WarhammerRiftPreviousMotion;
    FTransform WarhammerRiftPreviousFrame;
    float WarhammerRiftPreviousSeconds=-1.f,WarhammerRiftHeadRefresh=0.f;
    int32 WarhammerRiftActive=INDEX_NONE,WarhammerRiftNext=0,WarhammerRiftKey=INDEX_NONE;
    void FeedWarhammerRift(FName Clip,float SourceSeconds,int32 ChainStage=INDEX_NONE,float ChainContact=0.f);
    void TickWarhammerRifts(float Delta,bool Present);
    void ClearWarhammerRifts(bool Destroy=false);
    TWeakObjectPtr<UStaticMeshComponent> RuneboundMoteAnchor;
    float RuneboundVisual=0.f,RuneboundMaterialRefresh=0.f;
    bool bRuneboundSwiftVisual=false;
    int32 RuneboundShownCharge=-1;
    double RuneboundShownActivation=0.;
    UFUNCTION(Server,Reliable) void ServerBeginBluntUppercut(uint32 AttackId);
    UFUNCTION(Client,Reliable) void ClientBluntUppercutResult(uint32 AttackId,bool Accepted);
    UFUNCTION(Client,Reliable) void ClientBluntUppercutImpact(uint32 AttackId);
    bool bBluntUppercut=false,bBluntUppercutReleased=false,bBluntUppercutLungeStarted=false,bBluntUppercutLungeBlocked=false;
    float BluntUppercutTime=0.f,BluntUppercutPause=0.f,BluntUppercutImpactAge=1.f;
    float BluntUppercutDamage=0.f,BluntUppercutReach=0.f,BluntUppercutRange=1.f;
    int32 BluntUppercutHits=0,BluntUppercutKills=0;
    FString BluntUppercutInstance;
    FVector BluntUppercutDirection=FVector::ZeroVector;
    FColdSteelSkillShot BluntUppercutShot;
    TSet<TWeakObjectPtr<AActor>> BluntUppercutHitActors;
    PojunGrip::EAttack PojunAttack=PojunGrip::EAttack::Ordinary;
    float PojunSlashTime=-1.f;
    float PojunCutRate() const;
    FString PojunAttackItemData;
    bool PojunAttackStillEquipped(const FColdSteelItem& Item);
    void StartPojunAttack(PojunGrip::EAttack Attack,UColdSteelStatusModel* Profile);
    void StartBluntUppercut(UColdSteelStatusModel* Profile);
    void TickBluntUppercut(float Delta);
    void SweepBluntUppercut(float From,float To,const FTransform& Before,const FTransform& After);
    void FinishBluntUppercut();
    float BluntUppercutPoseTime() const;
    UFUNCTION(Server,Reliable) void ServerBeginLeapStrike(uint32 Serial,const FString& WeaponId,FVector_NetQuantizeNormal Direction,FVector_NetQuantize Target);
    UFUNCTION(Client,Reliable) void ClientLeapStrikeResult(uint32 Serial,bool Accepted,FVector_NetQuantize Target,
        FVector_NetQuantize Floor,FVector_NetQuantizeNormal Normal,double StartedAt,const FLeapStrikeCast& Cast,
        double TotalSpent,float Cooldown,float Duration,int64 Revision);
    UFUNCTION(Server,Reliable) void ServerCancelLeapStrike(uint32 Serial);
    UFUNCTION(Client,Reliable) void ClientStopLeapStrike(uint32 Serial);
    bool bLeapStrike=false,bLeapPending=false,bLeapLaunched=false,bLeapLanded=false,bLeapWhoosh=false;
    uint32 LeapSerial=0,LeapReceivedSerial=0;
    float LeapAge=0.f,LeapPoseChangedAt=0.f,LeapFlightAge=0.f,LeapPoseRate=1.f;
    float LeapExpectedFlight=0.f,LeapStalledTime=0.f;
    FVector LeapProgressPosition=FVector::ZeroVector;
    uint64 LeapContactFrame=MAX_uint64;
    double LeapStartedAt=0.;
    double LeapNoticeUntil=0.,LeapCameraReleaseUntil=0.;
    FString LeapWeapon;
    FName LeapPoseClip;
    FVector LeapStart=FVector::ZeroVector,LeapTarget=FVector::ZeroVector,LeapFloor=FVector::ZeroVector,LeapNormal=FVector::UpVector;
    FVector LeapEyeLocal=FVector::ZeroVector,LeapImpactPoint=FVector::ZeroVector;
    FVector LeapContactLocal=FVector::ZeroVector;
    FVector LeapCameraCollisionOffset=FVector::ZeroVector;
    FQuat LeapSlamRotation=FQuat::Identity;
    FColdSteelSkillShot LeapShot;
    FLeapStrikeCast LeapCast;
    bool bLeapTrainingPending=false;
    TWeakObjectPtr<UColdSteelStatusModel> LeapRewardModel;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> LeapAimMaterial;
    UPROPERTY(Transient) TObjectPtr<class UDecalComponent> LeapAimDecal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LeapAimMID;
    bool bLeapAimPreview=false,bLeapPreviewValid=false,bLeapPreviewPathClear=false;
    float LeapPreviewPathAge=0.f;
    float LeapPreviewRadius=0.f;
    FVector LeapPreviewTarget=FVector::ZeroVector,LeapPreviewDirection=FVector::ForwardVector;
    FVector LeapRequestDirection=FVector::ForwardVector;
    FRotator LeapLookCenter=FRotator::ZeroRotator;
    bool bLeapAirborne=false;
    void SetLeapAirborne(bool Active);
    bool LeapPreviewInputAvailable() const;
    void RefreshLeapAimPreview(float Delta);
    FVector LeapImpactForFloor(const FVector& Floor,const FVector& Direction,FVector& Normal) const;
    bool IsLeapPathClear(const FVector& Target) const;
    bool ValidateLeapLanding(const FVector& Requested,FVector& Target,FVector& Floor,FVector& Normal) const;
    bool CommitLeapStrike(const FVector& Target,const FVector& Floor,const FVector& Normal,const FVector& Direction);
    bool SolveLeapTarget(const FVector& Direction,FVector& Target,FVector& Floor,FVector& Normal,
        bool CheckPath=true,bool AllowShorten=true) const;
    bool StartLeapStrike(const FVector& Target,const FVector& Floor,const FVector& Normal,double StartedAt,
        const FLeapStrikeCast& Cast,bool Paid=false);
    void TickLeapStrike(float Delta);
    bool LaunchLeapStrike();
    void CompleteLeapLanding(const FHitResult& Ground);
    float LeapStartFloorZ() const;
    bool IsLeapFloorHeightAllowed(float FloorZ) const;
    void FinishLeapStrike(bool Interrupted=true);
    void PresentLeapStrike();
    bool GetLeapStrikeCameraLocation(FVector& Point) const;
    void LeapStrikeCamera(FVector& Location,FRotator& Rotation) const;
    UFUNCTION(Server,Reliable) void ServerBeginBluntWhirlwind(uint32 AttackId);
    UFUNCTION(Client,Reliable) void ClientBluntWhirlwindResult(uint32 AttackId,bool Accepted);
    UFUNCTION(Client,Reliable) void ClientBluntWhirlwindImpact(uint32 AttackId,float Pause,float Strength);
    bool bBluntWhirlwind=false,bBluntWhirlwindTrained=false;
    float BluntWhirlwindTime=0.f,BluntWhirlwindYaw=0.f,BluntWhirlwindPause=0.f,BluntWhirlwindPauseSpent=0.f;
    float BluntWhirlwindImpactAge=1.f,BluntWhirlwindImpactStrength=1.f;
    int32 BluntWhirlwindHitCount=0,BluntWhirlwindKillCount=0;
    FString BluntWhirlwindInstance;
    FWhirlwindCast BluntWhirlwindCast;
    FWhirlwindTuning BluntWhirlwindTuning;
    FColdSteelSkillShot BluntWhirlwindShot;
    TSet<TWeakObjectPtr<AActor>> BluntWhirlwindHitActors;
    void StartBluntWhirlwind(UColdSteelStatusModel* Profile);
    void TickBluntWhirlwind(float Delta);
    void SweepBluntWhirlwind(float FromDegrees,float ToDegrees);
    void FinishBluntWhirlwind();
    void TrainBluntWhirlwind();
    float BluntWhirlwindPoseTime() const;
    void BeginBluntWhirlwindFocus();
    void UpdateBluntWhirlwindFocus();
    void EndBluntWhirlwindFocus();
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BluntWhirlwindFocus;
    struct FBluntWhirlwindDepth
    {
        TWeakObjectPtr<UPrimitiveComponent> Part;
        bool Enabled=false;
        int32 Stencil=0;
        uint8 WriteMask=0;
    };
    TArray<FBluntWhirlwindDepth> BluntWhirlwindDepth;
    float BluntWhirlwindSavedBlur=0.f;
    bool bBluntWhirlwindSavedBlurOverride=false,bBluntWhirlwindFocusActive=false;
    UFUNCTION(Server,Reliable) void ServerBeginBluntAttack(uint32 AttackId,bool bReleaseCharge,bool bSprintAttack,const FString& WeaponId);
    UFUNCTION(Server,Reliable) void ServerBeginBluntCharge(uint32 AttackId,const FString& WeaponId);
    void TickAuthorityBluntCharge();
    UFUNCTION(Server,Reliable) void ServerCancelBluntAttack(uint32 AttackId);
    UFUNCTION(Client,Reliable) void ClientBluntAttackResult(uint32 AttackId,int32 Stage,bool bAccepted,bool bConfirmed,bool bHeavy,bool bSprint=false);
    UFUNCTION(Client,Reliable) void ClientBluntStaminaSpent(uint32 AttackId,float Amount);
    UFUNCTION(Client,Reliable) void ClientBluntMartialCommitted(uint32 AttackId,float Amount,int64 Revision,
        float Whirlwind,float WhirlwindDuration,float Uppercut,float UppercutDuration,double ServerAt);
    void SendBluntMartialReceipt(UColdSteelStatusModel* Profile,uint32 AttackId,float Amount);
    bool ApplyBluntStaminaReceipt(UColdSteelStatusModel* Profile,uint32 AttackId,float Amount);
    FTimerHandle BluntContactTimer;
    double BluntServerReadyAt=0.;
    double BluntServerGroundSlamUntil=0.;
    double BluntServerComboExpires=0.,LastBluntEnd=-100.;
    FString BluntServerInstance;
    int32 BluntStage=0,NextBluntStage=0,BluntServerNextStage=0;
    uint32 BluntAttackId=0,BluntServerAttackId=0;
    uint32 BluntLastServerRequestId=0;
    uint32 LastBluntStaminaReceipt=0;
    bool bQueuedBluntAttack=false;
    bool bBluntCharging=false,bBluntHeavy=false,bBluntReleaseCharge=false,bBluntServerCharging=false;
    bool bBluntReturningCharge=false;
    float BluntChargeReturnFrom=0.f,BluntChargeReturnAge=0.f,BluntChargeReturnDuration=.45f;
    float BluntChargePoseSeconds() const;
    bool bBluntSprintAttack=false;
    float BluntSprintSeconds=0.f;
    double BluntSprintReadyAt=-100.;
    FString BluntSprintInstance;
    FVector BluntSprintDirection=FVector::ForwardVector,BluntSprintAnchorLocation=FVector::ZeroVector;
    float BluntSprintLungeDistance=0.f;
    double BluntServerSprintContactAt=0.;
    double BluntServerSprintStartedAt=0.,BluntServerSprintMoveUntil=0.;
    bool bBluntSprintLungeBlocked=true,bBluntServerSprintAttack=false;
    void AdvanceBluntSprintLunge(float FromTime,float ToTime);
    void UpdateBluntSprintAnchor(bool bUpdateFloor);
    FQuat BluntSlamRotation=FQuat::Identity;
    FVector BluntSlamEye=FVector::ZeroVector;
    void AdvanceBluntSprintReadiness(float Delta);
    double BluntChargeStartedAt=0.,BluntServerChargeStartedAt=0.;
    FString BluntServerChargeInstance;
    float BluntChargeSeconds=2.f,BluntHeavyMultiplier=2.5f,BluntWaveRadius=300.f,BluntArcDegrees=120.f;
    float BluntHeavyStunSeconds=2.f;
    FVector BluntFloorPoint=FVector::ZeroVector,BluntFloorNormal=FVector::UpVector;
    bool bBluntFloorTarget=false;
    float BluntChargeResume(float Held) const;
    /** V6 ordinary cut: clip seconds of the current attack (non-linear attack-speed map). */
    float BluntClipTime() const;
    float BluntHitClipTime() const;
    float BluntClipRate() const;
    /** DPS-neutral visual chain: a buffered next cut starts its load from this
     *  cut's turnaround; gameplay still begins it when this cut ends. */
    void StartBluntChain(float Remaining);
    void AdvanceBluntChain(float Delta,float End);
    float BluntChainClipTime() const;
    float BluntStartClip=0.f;
    bool bBluntChain=false,bBluntHandoffEntry=false;
    void HandOffBluntPose();
    int32 BluntChainStage=0;
    float BluntChainAge=0.f,BluntChainSpan=0.f,BluntChainStartClip=0.f,BluntChainBlend=.3f;
    TArray<FHitResult> BluntContactHits(bool bPofeng) const;
    bool ResolveBluntContact(float StunSeconds=0.f,bool bPofeng=false);
    bool FindBluntGround(FHitResult& Hit) const;
    bool BeginBluntShockwave(bool bSprintAttack,float StunSeconds,float ThunderMagic);
    void AdvanceBluntCharge(float Delta);
    void SelectBluntMotion();
    void FinishUse();
    bool UsesPickaxeMotion() const { return Kind==TEXT("pickaxe") || Kind==TEXT("warhammer"); }
    bool UsesTwoHandMotion() const { return Kind==TEXT("axe") || UsesPickaxeMotion(); }
    static void LoadEnchantmentAnchors();
    friend class UFPSPlayerBodyComponent;
    bool GetEnchantmentBladeSpan(FVector& Base,FVector& Tip) const;
    friend class UWarhammerNetworkAuditCommandlet;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> Pivot;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ToolMesh;
    TWeakObjectPtr<UMaterialInstanceDynamic> LeiXiCoreMaterial;
    bool bLeiXiCoreActive=false;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Viewmodel;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Motions;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentMotion;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> GuardSounds;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> ImpactDust;
    UPROPERTY(Transient) TObjectPtr<UColdSteelPickupPrompt> Prompt;
    TSharedPtr<FStreamableHandle> LoadHandle;
    FString EquippedId, Kind, ToolName, Feedback;
    float SwingSeconds=.68f, ContactSeconds=.24f, Elapsed=-1.f, HintCountdown=0, FeedbackSeconds=0;
    float EquipElapsed=-1.f, VisualTime=0.f, SprintBlend=0.f;
    float InspectElapsed=-1.f, WalkInspectDelay=2.5f;
    UPROPERTY(Transient) FTwoHandInspectAudio InspectAir;
    FName InspectClip=FName(TEXT("Inspect"));
    bool ShouldBreakInspect() const;
    void ScheduleWalkInspect(bool bAfterInspect);
    bool IsWalkInspectStride() const;
    void TickWalkInspect(float Delta);
    void PlayInspectCues(float From,float To,float Rate);
    float AxeStridePhase=0.f;
    FVector AxeLocomotionOffset=FVector::ZeroVector;
    FQuat AxeLocomotionRotation=FQuat::Identity;
    bool bContacted=false;
    bool bUsesArms=false, bHitConfirmed=false, bSwingSoundPlayed=false;
    FProductionAxeImpactMotion AxeMotion;
    FColdSteelSkillShot AxeStrike;
    float AxeHarvestReach=320.f, AxeCombatReach=180.f;
    float AxeHarvestRadius=32.f, AxeCombatRadius=24.f;
    /** 改造实值：采集距离/半径、体力、伤害与挥砍速度都读它，不在各处二次换算。 */
    FProductionToolStats ToolStats;
    /** 挥砍速度倍率：真实时间 = 作者时间 ÷ RateScale。1 = 未改造，动作与镜头时序逐帧不变。 */
    float RateScale=1.f;
    float HasteActionRate=1.f,BluntMasteryInterval=1.f;
    /** 同一实例改了改造件也要刷新：物品 Data 变化即视为换装。 */
    uint32 EquippedDataHash=0;
    /** 作者节奏（SwingSeconds/ContactSeconds 与镜头关键帧）换算成真实时间。 */
    float BluntMotionRate() const { return UsesFinalTollHeavy()?FinalTollActionRate:bBluntSprintAttack?HasteActionRate:bBluntHeavy?RateScale*BluntMasteryInterval:RateScale; }
    float BluntLiftSeconds() const { return bBluntHeavy&&bBluntSprintAttack?WarhammerSprint::LiftSeconds/HasteActionRate:0.f; }
    float AuthoredElapsed() const { return UsesThunderThrowHeavy()?Elapsed*BluntMotionRate():UsesFinalTollHeavy()?Elapsed:bBluntHeavy?WarhammerHeavy::SourceTime(Elapsed-BluntLiftSeconds(),BluntMotionRate()):Elapsed*RateScale; }
    float RealContactSeconds() const { return UsesFinalTollHeavy()?FinalTollHeavy::FirstContact/FinalTollActionRate:BluntLiftSeconds()+ContactSeconds/BluntMotionRate(); }
    float RealSwingSeconds() const { return UsesThunderThrowHeavy()?ThunderHammerThrow::Duration/BluntMotionRate():UsesFinalTollHeavy()?FinalTollHeavy::Duration/FinalTollActionRate:bBluntHeavy?BluntLiftSeconds()+WarhammerHeavy::RealDuration(BluntMotionRate()):SwingSeconds/RateScale; }
    void ApplyToolStats(const FColdSteelItem* Item,UColdSteelStatusModel* Profile);
    bool CanPresent() const;
    bool CanUse(bool bContinuing = false) const;
    /** Shared single-target query for the hint and the contact event. */
    bool TraceAxeContact(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const;
    bool ResolveAxeEnemyContact(const FHitResult& Hit);
    /** 铲子自卫接触（2026-10-17 装备化）：与斧／镐同款瞄准变换与战斗距离，只打敌人。 */
    bool TraceShovelEnemyContact(FHitResult& Hit) const;
    bool ResolveShovelEnemyContact(const FHitResult& Hit);
    /** Owner-side cosmetic prediction of the server's ordinary hammer contact
     *  (same sector query and enemy filter, no damage) so the hit stop lands on
     *  the contact frame instead of one round trip later. */
    bool PredictBluntEnemyContact() const;
    bool TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const;
    bool ResolveContact();
    bool HasReadyPresentation() const;
    void SampleMotion(FName Clip,float Seconds);
    void SamplePojunChain(float Source,float Length,TConstArrayView<float> Contacts);
    void PlayPojunSwing(float Volume,float Pitch=1.f) const;
    UFUNCTION(NetMulticast,Unreliable) void MulticastPojunCutImpact(FVector_NetQuantize Location);
    void UpdateHandPresentation(float Delta);
    void UpdateTwoHandLocomotion(float Delta);
    void UpdateHint();
};
