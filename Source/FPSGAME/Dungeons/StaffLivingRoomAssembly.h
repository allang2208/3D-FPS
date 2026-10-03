#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/** Choose accepted furniture poses once on the decoration seed stream.
 *  Container specs become independent actors in the normal staged assembly. */
namespace StaffLivingRoomAssembly
{
    TSharedPtr<FJsonObject> Compose(const TSharedPtr<FJsonObject>& Module, int32 Seed, int32 Node);
}
