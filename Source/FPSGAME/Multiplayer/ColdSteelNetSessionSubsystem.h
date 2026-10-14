#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelNetSessionSubsystem.generated.h"

/** Disconnected guests retain session keys across maps, but never across rooms. */
UCLASS()
class FPSGAME_API UColdSteelNetSessionSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    void RememberGuestKeys(UWorld* World,FGuid Profile,const TArray<FName>& Keys);
    TArray<FName> RestoreGuestKeys(UWorld* World,FGuid Profile);
    FString TravelOption(UWorld* World);
    void RememberGuestProfile(UWorld* World,FGuid Profile,class UColdSteelStatusModel* Model);
    UColdSteelStatusModel* RestoreGuestProfile(UWorld* World,FGuid Profile);
private:
    bool BindRoom(UWorld* World);
    TWeakObjectPtr<class UNetDriver> RoomDriver;
    FGuid RoomId;
    TMap<FGuid,TArray<FName>> GuestKeys;
    // Keep the latest in-memory guest state through a failed logout save, for this room only.
    UPROPERTY() TMap<FGuid,TObjectPtr<UColdSteelStatusModel>> GuestProfiles;
};
