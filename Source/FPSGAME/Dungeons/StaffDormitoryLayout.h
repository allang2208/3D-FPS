#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "StaffDormitoryLayout.generated.h"

/** One bounded layout selection at level entry. Beds and architecture are never
 *  in LayoutActors; authored variants already reserve walls and door sweeps. */
UCLASS()
class FPSGAME_API AStaffDormitoryLayout : public AActor
{
    GENERATED_BODY()
public:
    AStaffDormitoryLayout();
    virtual void BeginPlay() override;
    UPROPERTY(EditAnywhere, Category="Dormitory") TArray<TObjectPtr<AActor>> LayoutActors;
    /** Serialized into the map, with no gameplay disk read or per-frame parse. */
    UPROPERTY(EditAnywhere, Category="Dormitory", meta=(MultiLine="true")) FString LayoutJson;
    /** -1 chooses a fresh layout on entering; nonnegative seeds reproduce it. */
    UPROPERTY(EditAnywhere, Category="Dormitory") int32 RandomSeed=-1;
};
