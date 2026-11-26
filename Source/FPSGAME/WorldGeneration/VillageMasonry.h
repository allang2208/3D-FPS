#pragma once

#include "Math/Transform.h"
#include "UObject/SoftObjectPath.h"

class UPrimitiveComponent;

namespace VillageMasonry
{
    inline constexpr TCHAR CastleFolder[] = TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/ChapelGatehouse/");

    inline FSoftObjectPath CastleMesh(const FString& Name)
    {
        return FSoftObjectPath(CastleFolder + Name + TEXT(".") + Name);
    }

    void ApplyWallPhase(UPrimitiveComponent& Surface, int32 SectionId);
    void ApplyCurtainPhase(UPrimitiveComponent& Surface, const FTransform& IntactWallPose);

    inline FSoftObjectPath Mesh(const FString& Name)
    {
        return FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageMasonry/ReliefMeshes/") + Name + TEXT(".") + Name);
    }
}
