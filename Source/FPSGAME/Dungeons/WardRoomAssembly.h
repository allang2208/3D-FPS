#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class AActor;
class UWorld;

/** Ward components share the generator's lifetime, transform and seed. */
namespace WardRoomAssembly
{
    AActor* Spawn(UWorld* World, AActor* Owner, const TSharedPtr<FJsonObject>& Spec,
        const FTransform& Room, AActor* Frame, FName ReceiverTag,
        TFunctionRef<UObject*(const FString&)> Resolve);
    void Populate(AActor* Actor, int32 Seed);
}
