#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Pure assembly data. Never changes route cells, doors, navigation masks or shared catalog objects. */
namespace DungeonRoomScenes
{
TSharedPtr<FJsonObject> Compose(const TSharedPtr<FJsonObject>& Module, int32 Seed, int32 PieceIndex,
    TMap<FString, FString>& PreviousRecipes, TMap<FString, FString>& PreviousStates);
}
