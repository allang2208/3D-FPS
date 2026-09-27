#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

namespace DungeonCatalog
{
    // Expand immutable shell/interior references into a transient catalog, once
    // at generation/bind time. The saved authoring catalog keeps shared recipes.
    bool ResolveRecipes(const TSharedPtr<FJsonObject>& Catalog,FString& Error);
}
