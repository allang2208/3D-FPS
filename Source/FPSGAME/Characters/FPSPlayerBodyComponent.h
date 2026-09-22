#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSPlayerBodyTypes.h"
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
    UPROPERTY(Transient) TMap<TObjectPtr<class UMeshComponent>, FFPSBodyOriginalMaterials> OriginalMaterials;
    TSharedPtr<class FJsonObject> Configuration;
    FFPSBodyState DisplayState;
    TArray<FFPSBodyWeapon> LocalWeapons;
    TArray<FFPSBodyOutfitSlot> LocalOutfit;
    FString EquipmentKey;
    FDelegateHandle ProfileChanged;
    float RefreshCountdown = 0.f;
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
    void CaptureEquipment();
    FFPSBodyWeapon CaptureWeapon(class USkeletalMeshComponent* Mesh, class UAnimSequence* Idle, FName Grip) const;
    void RebuildWeapons(const TArray<FFPSBodyWeapon>& Weapons);
    void UpdateWorldWeaponPresentation();
    bool ShouldWorldBodyCastShadow() const;
    bool IsWorldWeaponStowed(class UPrimitiveComponent* Mesh) const;
    void ApplyOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit);
    void UpdateOwnerVisibility();
    void UpdateWorldOwnerVisibility(bool bHideFromOwner);
};

/** `fps.body.WorldBody` state, read at each use site rather than mirrored into a
 *  member, because a console variable set from the command line lands after the world
 *  has been initialised. Declared here so the camera path can honour the switch. */
FPSGAME_API bool FPSPlayerBodyWorldBodyHidden();
FPSGAME_API bool FPSPlayerBodyWorldBodySuppressed();
/** `fps.body.WorldBodyShadow` 状态：1 = 身体与世界装备照常投影（默认），
 *  0 = 关闭它们的阴影投射。用于分离「阴影深度 pass」在整帧里的占比。 */
FPSGAME_API bool FPSPlayerBodyWorldBodyShadowEnabled();
