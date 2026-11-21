// Source/FPSGAME/WorldGeneration/TemperateVillageCheckCommandlet.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 11-16 | class UTemperateVillageCheckCommandlet : public UCommandlet
private:
    int32 CheckDefenseBlocks(const FString& Params);
    void ExerciseDefenseSupport(class AVoxelBuildWorld& Build,FVector Floor,TFunctionRef<bool(bool,const FString&)> Check);
    void ExerciseDefenseUndo(class AVoxelBuildWorld& Build,TFunctionRef<bool(bool,const FString&)> Check);
    void ExerciseDefensePlacement(class AVoxelBuildWorld& Build,class ATemperateHillsWorld& Hills,
        class AHighVillageWall& GeneratedWall,TFunctionRef<bool(bool,const FString&)> Check);
