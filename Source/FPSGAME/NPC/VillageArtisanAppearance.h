#pragma once

#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

class USkeletalMeshComponent;
struct FResidentConversationFacing;

namespace VillageArtisanAssets
{
    extern const FSoftObjectPath StandingBreath;
}

/** Work clothes and head follow the same strong Jason body and standing animation. */
struct FVillageArtisanAppearance
{
    FSoftObjectPath HeadMesh;
    FSoftObjectPath WorkwearMesh;

    TArray<FSoftObjectPath> Paths() const;
    bool IsCompiling() const;
    void Dress(USkeletalMeshComponent& Body, USkeletalMeshComponent& Head, USkeletalMeshComponent& Workwear,
               FResidentConversationFacing& Facing) const;
};
