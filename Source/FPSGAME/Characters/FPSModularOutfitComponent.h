#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSPlayerBodyTypes.h"
#include "FPSOutfitStairVisibility.h"
#include "FPSModularOutfitComponent.generated.h"

class USkeletalMeshComponent;
class USkeletalMesh;
struct FStreamableHandle;
class FJsonObject;
struct FFPSOutfitSecondaryMotion;
struct FHitResult;

/** One complete presentation transaction for a weapon rig or the world body. */
USTRUCT()
struct FFPSOutfitPresentation
{
    GENERATED_BODY()
    UPROPERTY(Transient) TWeakObjectPtr<USkeletalMeshComponent> Source;
    UPROPERTY(Transient) TObjectPtr<USkeletalMesh> SourceAsset;
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> Parts;
    // Per LOD material state before this component took ownership.
    TArray<TArray<int32>> PreviouslyVisible;
    TArray<int32> HiddenMaterials;
    FString Key;
    bool bWorld = false;
    TSharedPtr<FFPSOutfitSecondaryMotion> SecondaryMotion;
    TArray<FFPSRobeStairSections> StairSections;
    TSharedPtr<FFPSRobeHemEnvelope> RobeHem;
};

/** Geometry-only clothing. Follows accepted weapon poses; owns neither inventory nor animations. */
UCLASS(BlueprintType, ClassGroup=(Player), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSModularOutfitComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSModularOutfitComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    /** Existing server-authoritative world-body equipment replication supplies remote appearances. */
    void SetWorldOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit);
    void RefreshInventory();
    /** Local visual pose layers use the current equipment, never inventory copies. */
    bool IsSteelGauntletEquipped() const;
    bool IsChainmailEquipped() const;
    /** Replicated world outfit on remote pawns, current equipped item on the owner. */
    FName EquippedOutfit(int32 Slot) const { return Equipped.FindRef(Slot); }
    bool WantsRobeStairSupport() const;
    /** Reuses the world body's foot-support probes for local and remote pawns. */
    void ObserveRobeStairSupport(const TArray<FHitResult>& Hits);
    /** Offline authoring only; never changes the imported close-range mesh. */
    UFUNCTION(BlueprintCallable, Category="Outfit|Authoring", meta=(ScriptName="configure_outfit_lods"))
    static bool ConfigureDistanceLODs(USkeletalMesh* Mesh);
    /** Retired authoring entry retained for compatibility; always returns false. */
    UFUNCTION(BlueprintCallable, Category="Outfit|Authoring", meta=(ScriptName="build_chainmail_cloth"))
    static bool BuildChainmailCloth(USkeletalMesh* Mesh,USkeletalMesh* Proxy);
    /** Builds the blue robe's continuous skirt proxy and stable Witch capture. */
    UFUNCTION(BlueprintCallable, Category="Outfit|Authoring", meta=(ScriptName="build_mage_robe_drape"))
    static bool BuildMageRobeDrape(USkeletalMesh* Mesh);
    /** Commandlet authoring: add the WPO pin without an editor GraphNode. */
    UFUNCTION(BlueprintCallable, Category="Outfit|Authoring", meta=(ScriptName="add_robe_hem_offset_pin"))
    static int32 AddRobeHemOffsetPin(UObject* Expression);
    /** Commandlet authoring: preserve the source opacity mask in robe inner layers. */
    UFUNCTION(BlueprintCallable, Category="Outfit|Authoring", meta=(ScriptName="add_robe_hem_mask_pin"))
    static int32 AddRobeHemMaskPin(UObject* Expression);

private:
    UPROPERTY(Transient) TArray<FFPSOutfitPresentation> Presentations;
    TSharedPtr<FJsonObject> Configuration;
    TMap<FString,TSharedPtr<FStreamableHandle>> PendingLoads;
    TSet<FString> FailedLoads;
    TMap<int32,FName> Equipped;
    FDelegateHandle InventoryChanged;
    float DiscoverCountdown = 0.f;
    bool bDirty = true;
    bool bEnding = false;
    float RobeStairUntil = -1.f;
    bool bHideRobeCalves = false;
    void UpdateRobeStairVisibility();
    void DiscoverSources();
    void UpdatePresentation(USkeletalMeshComponent* Source,const TSharedPtr<FJsonObject>& Profile,bool bWorld,bool bLowerBody=false);
    void ReleasePresentation(FFPSOutfitPresentation& Presentation);
    void FollowVisibility(FFPSOutfitPresentation& Presentation);
};
