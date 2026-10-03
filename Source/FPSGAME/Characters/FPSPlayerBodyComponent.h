#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSPlayerBodyTypes.h"
#include "FPSPlayerBodyGrip.h"
#include "FPSBodyMotionBinding.h"
#include "FPSBodyReactionState.h"
#include "FPSPlayerBodyComponent.generated.h"

/** World-space body and equipment, separate from the camera's existing viewmodels. */
UCLASS(ClassGroup=(Player), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSPlayerBodyComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSPlayerBodyComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;

    UFUNCTION(BlueprintPure, Category="Player Body") FFPSBodyState GetBodyState() const { return DisplayState; }
    /** Future authoritative combat adapters publish here; this is deliberately not a client RPC. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Player Body")
    void SetAuthoritativeState(const FFPSBodyState& State);
    void SetAuthoritativeEquipment(const TArray<FFPSBodyWeapon>& Weapons, const TArray<FFPSBodyOutfitSlot>& Outfit);
    UFUNCTION(BlueprintCallable, Category="Player Body") void RefreshEquipment();
    /** 联机：拥有端把离散动作过渡（换弹/施法/挥砍/格挡等）上报到服务端，
     *  服务端并入远端 pawn 的权威身体态。仅在服务端调用。 */
    void ServerRecordAction(EFPSBodyAction Action, FName Variant, float Duration);
    void RecordAcceptedHit(AActor* Attacker,float Damage,float MaxHealth);
    void RecordKnockback(const FVector& Direction,float Distance,float Duration);
    UFUNCTION(BlueprintPure, Category="Player Body") class USkeletalMeshComponent* GetBodyMesh() const;
    /** Applies `fps.body.WorldBody` to the body, world weapon, attachment and outfit
     *  components. Safe to call every visibility refresh; only changed flags are set. */
    void ApplyWorldBodyVisibility();
    /** 把 `fps.body.WorldBodyShadow` 施加到身体网格与世界装备网格上。
     *  第一人称下这些网格看不见（OwnerNoSee + bCastHiddenShadow），
     *  却仍在为阴影贴图渲染一遍深度。 */
    void ApplyWorldBodyShadow();
    /** Local F6 view only; keeps the first-person camera as the gameplay aim anchor. */
    bool IsThirdPersonViewEnabled() const;
    void ApplyCameraView(struct FMinimalViewInfo& View);
    void ApplyInteractionView(FVector& Eye, FRotator& View) const;
    void RefreshViewMode();
    // The accepted first-person consumable executor supplies visual release events.
    bool PresentConsumableDiscard(class UStaticMeshComponent* Source,const FVector& Velocity,float Lifetime);
    /** Only catalog IDs are accepted. Persists the owning player's choice. */
    UFUNCTION(BlueprintCallable, Category="Player Body") bool SetHeadAndHair(FName HeadId,FName HairId);

private:
    UPROPERTY(ReplicatedUsing=OnRep_BodyState) FFPSBodyState ReplicatedState;
    UPROPERTY(ReplicatedUsing=OnRep_Equipment) TArray<FFPSBodyWeapon> ReplicatedWeapons;
    UPROPERTY(ReplicatedUsing=OnRep_Outfit) TArray<FFPSBodyOutfitSlot> ReplicatedOutfit;
    UFUNCTION() void OnRep_BodyState();
    UFUNCTION() void OnRep_Equipment();
    UFUNCTION() void OnRep_Outfit();
    TWeakObjectPtr<class AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<class UFPSPlayerBodyAnimInstance> BodyAnimation;
    UPROPERTY(Transient) TArray<TObjectPtr<class USkeletalMeshComponent>> WorldWeapons;
    UPROPERTY(Transient) TArray<TObjectPtr<class UStaticMeshComponent>> WorldParts;
    // Includes the weapon and every copied part; array indices can change when an asset is absent.
    TMap<TWeakObjectPtr<class UPrimitiveComponent>, uint8> WorldEquipmentHands;
    UPROPERTY(Transient) TArray<TObjectPtr<class USkeletalMeshComponent>> OutfitMeshes;
    // 刚性装备件（背包等静态网格按骨骼 socket 挂载），随 OutfitMeshes 同批重建/显隐。
    UPROPERTY(Transient) TArray<TObjectPtr<class UStaticMeshComponent>> OutfitStaticMeshes;
    UPROPERTY(Transient) TMap<TObjectPtr<class UMeshComponent>, FFPSBodyOriginalMaterials> OriginalMaterials;
    TSharedPtr<class FJsonObject> Configuration;
    FFPSBodyState DisplayState;
    TArray<FFPSBodyWeapon> LocalWeapons;
    TArray<FFPSBodyOutfitSlot> LocalOutfit;
    FString EquipmentKey;
    FDelegateHandle ProfileChanged;
    float RefreshCountdown = 0.f;
    float RemoteEquipCountdown = 0.f;
    float VisibilityCountdown = 0.f;
    float WorldWeaponsHiddenUntil = 0.f;
    float OffhandWeaponHiddenUntil = 0.f;
    bool bExternalAuthorityState = false;
    bool bEquipmentDirty = true;
    bool bOutfitDirty = true;
    EFPSBodyAction PreviousAction = EFPSBodyAction::None;
    float UnclockedActionStartedAt = 0.f;
    float ServerClock() const;
    void InitializeBody();
    FFPSBodyState SampleLocalState() const;
    /** 服务端：为非本机控制的远端 pawn 组装权威身体态——服务端可信事实
     *  （CMC 意图位/装备/瞄准俯仰）+ 客户端汇报的离散动作。 */
    FFPSBodyState SampleRemoteAuthorityState() const;
    EFPSBodyAction ReportedAction = EFPSBodyAction::None;
    FName ReportedActionVariant;
    float ReportedActionStartedAt = -100.f;
    float ReportedActionDuration = 0.f;
    void CaptureEquipment();
    FFPSBodyWeapon CaptureWeapon(class USkeletalMeshComponent* Mesh, class UAnimSequence* Idle, FName Grip) const;
    void RebuildWeapons(const TArray<FFPSBodyWeapon>& Weapons);
    void BuildShovelGrip(const FFPSBodyWeapon& Definition,class UStaticMeshComponent& Part);
    void UpdateWorldWeaponPresentation();
    bool ShouldWorldBodyCastShadow() const;
    bool IsWorldWeaponStowed(class UPrimitiveComponent* Mesh) const;
    void ApplyOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit);
    void UpdateOwnerVisibility();
    void UpdateWorldOwnerVisibility(bool bHideFromOwner);

    // State edges (including None/cancel) are reliable. Continuous cosmetic samples
    // are bounded to 12.5 Hz; one sequence orders both RPC streams.
    UFUNCTION(Server, Reliable) void ServerBodyTransition(const FFPSBodyState& State, uint32 Sequence);
    UFUNCTION(Server, Unreliable) void ServerBodySnapshot(const FFPSBodyState& State, uint32 Sequence);
    void SendBodyPresentation(float Delta);
    void AcceptBodyPresentation(const FFPSBodyState& State, uint32 Sequence);
    static void AdvanceBodyPresentation(FFPSBodyState& State, float Now);
    FFPSBodyState PreviousLocalPresentation;
    FFPSBodyState ReportedPresentation;
    bool bHasLocalPresentation = false;
    bool bHasReportedPresentation = false;
    uint32 SentPresentationSequence = 0;
    uint32 ReceivedPresentationSequence = 0;
    float PresentationSendCountdown = 0.f;
    float LastPresentationReceivedAt = -100.f;
    UPROPERTY(ReplicatedUsing=OnRep_Appearance) FFPSBodyAppearance ReplicatedAppearance;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> HeadMesh;
    UPROPERTY(Transient) TArray<TObjectPtr<class UGroomComponent>> HeadGrooms;
    UPROPERTY(Transient) TObjectPtr<class ULODSyncComponent> AppearanceLODSync;
    TSharedPtr<struct FStreamableHandle> AppearanceLoad;
    FFPSBodyAppearance AppliedAppearance;
    uint32 AppearanceRequest = 0;
    UFUNCTION() void OnRep_Appearance();
    FFPSBodyAppearance ResolveAppearance(FFPSBodyAppearance Appearance) const;
    void RefreshAppearance(class UColdSteelStatusModel* Profile);
    void ApplyAppearance(FFPSBodyAppearance Appearance);
    void UpdateAppearanceVisibility();
    FTransform HandRigOffsets[2] = {FTransform::Identity,FTransform::Identity};
    void CaptureBow(const class UBowWeaponComponent& Bow,FFPSBodyWeapon& Weapon) const;
    void SampleBowState(const class UBowWeaponComponent& Bow,FFPSBodyState& State) const;
    void BuildBow(const FFPSBodyWeapon& Definition,class USkeletalMeshComponent* Rig);
    void UpdateBow();
    void ClearBow();
    void UpdateBowVisibility(bool HideOwner);
    UPROPERTY(Transient) TObjectPtr<class USkeletalMeshComponent> BowRig;
    UPROPERTY(Transient) TArray<TObjectPtr<class UBowPartComponent>> WorldBowParts;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<class UAnimSequence>> BowClips;
    FFPSBodyGripRig BowGripRigs[2];
    FFPSBodyBowSettings BowSettings;
    FName SampledBowClip;
    float SampledBowTime = -1.f;
    FTransform BowRiserMount = FTransform::Identity;
    TArray<FFPSBodyMotionBinding> MotionBindings;
    TMap<TWeakObjectPtr<class UPrimitiveComponent>,int32> MotionEquipmentIndices;
    TArray<FFPSBodyMotionMap> MotionMaps;
    TWeakObjectPtr<class USkeletalMesh> MotionBodyAsset;
    TWeakObjectPtr<class USkeletalMesh> MotionFingerAsset;
    int32 MotionFingerBones[2][15];
    TArray<TPair<int32,int32>> MotionHalfBones[2];
    FFPSBodyGripRig* MotionMap(class USkeletalMeshComponent* Source,FName Hand,int32 Side);
    void CaptureMotion(FFPSBodyState& State);
    void ApplyMotion(float Delta);
    void CaptureMotionHand(class USkeletalMeshComponent* Source,FName Hand,int32 Side,bool Wrist,FFPSBodyMotionSample& Sample);
    void UpdateConsumable(const FFPSBodyMotionSample& Sample);
    void CreateConsumable(FName Definition);
    void ReleaseConsumable(int32 Part,const FVector& Velocity,float Lifetime);
    void ClearMotion();
    void OnBodyPoseFinalized();
    FDelegateHandle BodyPoseFinalizedHandle;
    uint8 QueuedWorldDiscards=0;
    bool bPendingBottleDrop=false,bQueuedBottleDrop=false;
    FFPSBodyMotionSample SmoothedContacts;
    FTransform BaseSupportGrip=FTransform::Identity;
    bool bMotionSampleValid=false;
    FName WorldConsumable;
    uint16 WorldConsumableSerial=0;
    uint8 WorldDiscardFlags=0,PendingDiscardFlags=0;
    uint16 LocalConsumableSerial=0;
    float PendingDiscardUntil=-1.f;
    UPROPERTY(Transient) TArray<TObjectPtr<class UStaticMeshComponent>> ConsumableParts;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInstanceDynamic> ConsumableLiquid;
    UPROPERTY(Transient) TObjectPtr<class UPointLightComponent> WorldStaffLight;
    UPROPERTY(Transient) TArray<TObjectPtr<class UMaterialInstanceDynamic>> WorldStaffMaterials;
    TSharedPtr<struct FStreamableHandle> ConsumableLoad;
    uint32 ConsumableRequest=0;
    float LastWorldLight=-1.f,LastLiquidLevel=-10000.f;
    void UpdateReactions();
    UPROPERTY(Replicated) FFPSBodyReactionState Reactions;
    TWeakObjectPtr<class UCombatStatusFormula> ReactionStatus;
    TWeakObjectPtr<class UPlayerGuardBreakComponent> ReactionGuard;
    float ReactionComponentRefresh=0.f;

};

/** `fps.body.WorldBody` state, read at each use site rather than mirrored into a
 *  member, because a console variable set from the command line lands after the world
 *  has been initialised. Declared here so the camera path can honour the switch. */
FPSGAME_API bool FPSPlayerBodyWorldBodyHidden();
FPSGAME_API bool FPSPlayerBodyWorldBodySuppressed();
/** `fps.body.WorldBodyShadow` 状态：1 = 身体与世界装备照常投影（默认），
 *  0 = 关闭它们的阴影投射。用于分离「阴影深度 pass」在整帧里的占比。 */
FPSGAME_API bool FPSPlayerBodyWorldBodyShadowEnabled();
