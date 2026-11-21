// Source/FPSGAME/NPC/ChapelDialogueComponent.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 302-303 | bool UChapelDialogueComponent::BuildingRepaired(FName Plan) const
    if(Plan==TEXT("wall"))return Hills->IsVillageWallRepaired();
    if(Plan==TEXT("high_wall"))return Hills->HasVillageHighWall();

// Lines 369-380 | const FString& UChapelDialogueComponent::NunActionMessage(FName Action) const
const FString& UChapelDialogueComponent::NunActionMessage(FName Action) const
{
    static const FString Empty;
    if (LastNunAction!=Action) return Empty;
    if (!bPending && Action!=TEXT("holyLight"))
    {
        // The controller's reliable reply and the village's replicated state can arrive in either order.
        const bool bComplete=Action==TEXT("village_construction") ? PlanUnlocked(Action) : BuildingRepaired(Action);
        if (bLastNunActionSucceeded!=bComplete) return Empty;
    }
    return Message;
}

// Lines 390-390 | void UChapelDialogueComponent::ServerAction_Implementation(uint32 Session,FName Action)
        Action==TEXT("herbalist")||Action==TEXT("village_construction")||Action==TEXT("high_wall")||Action==TEXT("windmill")||

// Lines 396-397 | void UChapelDialogueComponent::ServerAction_Implementation(uint32 Session,FName Action)
        else if(Action==TEXT("wall"))Result=TEXT("围墙已整体修复，村庄建设进度已保存。");
        else if(Action==TEXT("high_wall"))Result=TEXT("石砌高墙已落成，东西村门已换用升降铁闸。");

// Lines 404-404 | void UChapelDialogueComponent::ServerAction_Implementation(uint32 Session,FName Action)
        else if(Action==TEXT("village_construction"))Result=TEXT("村庄修建已解锁。按 B 打开「村庄建筑」，可放置围墙、大门、带城垛的高墙、石城门和登墙石阶。");
