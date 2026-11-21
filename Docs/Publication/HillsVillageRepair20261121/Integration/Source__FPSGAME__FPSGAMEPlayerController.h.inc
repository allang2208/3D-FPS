// Source/FPSGAME/FPSGAMEPlayerController.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 29-32 | class FPSGAME_API AFPSGAMEPlayerController : public APlayerController
    UFUNCTION(Server,Reliable) void ServerRepairVillageDefense(class AVillageDefenseSection* Section,APawn* RequestPawn,uint32 RequestId);
    UFUNCTION(Client,Reliable) void ClientVillageRepairResult(uint32 RequestId,bool bRepaired,const FText& Message);
    void RequestVillageRepair(class AVillageDefenseSection* Section);
    bool IsInBuildMode() const;

// Lines 88-92 | class FPSGAME_API AFPSGAMEPlayerController : public APlayerController
    uint32 VillageRepairRequestId=0;
    TWeakObjectPtr<APawn> VillageRepairPawn;
    TMap<uint32,TWeakObjectPtr<AVillageDefenseSection>> PendingVillageRepairs;
    TWeakObjectPtr<AVillageDefenseSection> RecentlyRepairedSection;
    double RepairedSectionRetryTime=0.;
