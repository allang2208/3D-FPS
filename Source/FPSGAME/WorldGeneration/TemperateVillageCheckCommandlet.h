#pragma once
#include "Commandlets/Commandlet.h"
#include "TemperateVillageCheckCommandlet.generated.h"

UCLASS()
class UTemperateVillageCheckCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
private:
    int32 CheckDefenseBlocks(const FString& Params);
    void ExerciseDefenseSupport(class AVoxelBuildWorld& Build,FVector Floor,TFunctionRef<bool(bool,const FString&)> Check);
    void ExerciseDefenseUndo(class AVoxelBuildWorld& Build,TFunctionRef<bool(bool,const FString&)> Check);
    void ExerciseDefensePlacement(class AVoxelBuildWorld& Build,class ATemperateHillsWorld& Hills,
        class AHighVillageWall& GeneratedWall,TFunctionRef<bool(bool,const FString&)> Check);
};
