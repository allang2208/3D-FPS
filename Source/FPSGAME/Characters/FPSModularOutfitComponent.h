#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSPlayerBodyTypes.h"
#include "FPSModularOutfitComponent.generated.h"

class USkeletalMeshComponent;
class USkeletalMesh;
struct FStreamableHandle;
class FJsonObject;

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
    /** Offline authoring only; never changes the imported close-range mesh. */
    UFUNCTION(BlueprintCallable, Category="Outfit|Authoring", meta=(ScriptName="configure_outfit_lods"))
    static bool ConfigureDistanceLODs(USkeletalMesh* Mesh);

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
    void DiscoverSources();
    void UpdatePresentation(USkeletalMeshComponent* Source,const TSharedPtr<FJsonObject>& Profile,bool bWorld);
    void ReleasePresentation(FFPSOutfitPresentation& Presentation);
    void FollowVisibility(FFPSOutfitPresentation& Presentation);
};
