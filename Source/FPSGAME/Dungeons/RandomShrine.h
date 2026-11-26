#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Shared pool exported from the production dungeon's start_shrine catalog. */
namespace RandomShrine
{
    const TSharedPtr<FJsonObject>& Catalog();
    TSharedPtr<FJsonObject> Choose(FRandomStream& Random,const TSharedPtr<FJsonObject>& Fallback=nullptr);
    void AddMeshPaths(TArray<FSoftObjectPath>& Paths);
}
