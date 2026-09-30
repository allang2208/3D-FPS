#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Seeded selection in authored solid-wall slots; no world scan or tick. */
namespace DungeonWallArt
{
    TArray<TSharedPtr<FJsonValue>> Build(const TSharedPtr<FJsonObject>& Module,int32 Seed,int32 ModuleIndex);
}
