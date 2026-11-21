// Source/FPSGAME/WorldGeneration/TemperateHillsWorld.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 224-224 | class FPSGAME_API UTemperateHillsSave : public USaveGame
    UPROPERTY() FGuid VillageDefenseGeneration;

// Lines 286-287 | class FPSGAME_API ATemperateHillsWorld : public AActor
    UFUNCTION(BlueprintPure, Category="Hills|Village") bool IsVillageWallRepaired() const { return bVillageWallRepaired; }
    bool HasVillageHighWall() const { return bVillageWallRepaired && (VillagePlansUnlocked & UTemperateHillsSave::HighWallPlan) != 0; }

// Lines 291-292 | class FPSGAME_API ATemperateHillsWorld : public AActor
    bool CompleteVillageWallRepair(FText& FailureReason);
    bool CompleteVillageHighWallUpgrade(FText& FailureReason);

// Lines 518-523 | class FPSGAME_API ATemperateHillsWorld : public AActor
    UFUNCTION() void OnRep_VillageWall();
    void BuildVillagePerimeter();
    friend class AVillageDefenseStairs;
    void RefreshVillageGateStairs(const class AVillageDefenseStairs* Arriving=nullptr);
    FTimerHandle VillageGateStairRetry;
    void ClearVillagePerimeter();
