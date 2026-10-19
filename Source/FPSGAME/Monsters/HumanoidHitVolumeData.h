#pragma once
#include "CoreMinimal.h"
#include "Engine/AssetUserData.h"
#include "HumanoidHitVolumeData.generated.h"

USTRUCT()
struct FHumanoidCriticalHull
{
    GENERATED_BODY()
    UPROPERTY() FBox Bounds = FBox(ForceInit);
    /** Outward unit planes in HeadBone local coordinates. */
    UPROPERTY() TArray<FPlane> Planes;
};

/** Saved beside fitted query shapes; anatomical head damage is separate from hats/gills. */
UCLASS()
class FPSGAME_API UHumanoidHitVolumeData : public UAssetUserData
{
    GENERATED_BODY()
public:
    UPROPERTY() FName HeadBone;
    UPROPERTY() TArray<FHumanoidCriticalHull> HeadHulls;
    UPROPERTY() FString SourceMesh;
    UPROPERTY() FString OriginalPhysicsAsset;
    UPROPERTY() int32 Revision = 1;
    /** Returns whether this hit belongs to a fitted character, even for an ordinary body hit. */
    static bool ResolveCriticalHit(const FHitResult& Hit, bool& bCritical);
    /** Remove the head designation from ordinary hood/gill contacts before reporting a hit. */
    static FName NetworkBoneName(const FHitResult& Hit);
};
