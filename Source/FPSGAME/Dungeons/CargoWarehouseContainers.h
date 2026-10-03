#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

namespace CargoWarehouseContainers
{
    TSharedPtr<FJsonObject> Compose(const TSharedPtr<FJsonObject>& Module,int32 Seed,int32 Node);
}
