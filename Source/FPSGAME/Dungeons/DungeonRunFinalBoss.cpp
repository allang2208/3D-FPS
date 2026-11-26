#include "DungeonRunSubsystem.h"
#include "DungeonRoomSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "GameFramework/PlayerController.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "Engine/World.h"

void UDungeonRunSubsystem::BindFinalBossTheme(AAuthoredDungeonGenerator* InGenerator)
{
    TArray<int32> Rooms;TArray<FDungeonRunDoor> Boundaries;
    for(const auto& Node:Nodes)if(AFacilityHallEncounter::IsFinalBossRoom(Node.Module))
    {Rooms.Add(Node.Id);Boundaries.Append(Node.Doors);}
    if(Rooms.IsEmpty())return;
    if(Rooms.Num()==1&&!Boundaries.IsEmpty())
    {
        FActorSpawnParameters Params;Params.Owner=InGenerator;Params.ObjectFlags|=RF_Transient;
        auto* Area=GetWorld()->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(),FTransform::Identity,Params);
        if(Area&&Area->Configure(this,InGenerator,Rooms,Boundaries,EDungeonThemeObjective::FinalBoss))FinalBossTheme=Area;
        else if(Area)Area->Destroy();
    }
    if(!FinalBossTheme.IsValid())UE_LOG(LogTemp,Error,TEXT("[FinalBoss] Expected one terminal room with authored entry; rooms=%d doors=%d"),Rooms.Num(),Boundaries.Num());
}

bool UDungeonRunSubsystem::IsFinalBossDefeated() const
{
    if(!bActive||!Generator.IsValid())return false;
    if(GetWorld()->GetNetMode()==NM_Client)return bNetworkFinalBossDefeated;
    for(const auto& Encounter:HallEncounters)
        if(Encounter.IsValid()&&Encounter->IsFinalBossDefeated())return true;
    return false;
}

void UDungeonRunSubsystem::MarkFinalTreasureLooted(AActor* Chest,APlayerController* Player)
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client||!IsFinalBossDefeated()
        ||!IsValid(Chest)||Chest->GetOwner()!=Generator.Get()||!Chest->ActorHasTag(TEXT("DungeonFinalTreasure")))return;
    if(UDungeonRoomSubsystem::Supports(GetWorld())&&Player)
        if(auto* PS=Player->GetPlayerState<AColdSteelPlayerState>();PS&&PS->bInDungeonRoom)
        {
            PS->bClaimedFinalDungeonTreasure=true;PS->ForceNetUpdate();
            if(auto* Model=ColdSteelAuthority::ForPawn(Player->GetPawn()))
            {
                auto Profile=Model->Snapshot();
                if(Profile.DungeonRun.RunId==CurrentRunId&&!Profile.DungeonRun.Claimed.Contains(TEXT("FinalTreasure.Taken")))
                {Profile.DungeonRun.Claimed.Add(TEXT("FinalTreasure.Taken"));Model->CommitState(MoveTemp(Profile));}
            }
        }
    if(!bFinalTreasureLooted){bFinalTreasureLooted=true;PublishSharedProgress();}
}

void UDungeonRunSubsystem::MarkFinalReturnUsed(AActor* Portal)
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client||!CanUseFinalReturn()||!IsValid(Portal)
        ||Portal->GetOwner()!=Generator.Get()||!Portal->ActorHasTag(TEXT("DungeonFinalReturn")))return;
    MarkRunCompleted();
}

void UDungeonRunSubsystem::CancelFinalReturn(AActor* Portal)
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client||!bActive||!bCompleted||!IsValid(Portal)
        ||Portal->GetOwner()!=Generator.Get()||!Portal->ActorHasTag(TEXT("DungeonFinalReturn")))return;
    bCompleted=false;CommitProfileRunState();
}

void UDungeonRunSubsystem::AppendFinalBossObjectives(FTrackedTaskView& Out) const
{
    const bool Defeated=IsFinalBossDefeated();
    Out.Area=FText::FromString(TEXT("废弃设施 · 终末泵机大厅"));
    Out.Stage=FText::FromString(bCompleted?TEXT("地牢完成"):Defeated?TEXT("收取战利品并撤离"):TEXT("最终首领 · 合阙 M-36"));
    auto Add=[&Out](FName Id,const TCHAR* Text,bool Complete,bool Counted)
    {
        auto& Goal=Out.Objectives.AddDefaulted_GetRef();Goal.Id=Id;Goal.Text=FText::FromString(Text);
        Goal.Current=Complete?1:0;Goal.Target=Counted?1:0;
        Goal.State=Complete?ETrackedObjectiveState::Completed:ETrackedObjectiveState::Active;
    };
    Add(TEXT("final.heque"),TEXT("击败最终首领：合阙 M-36"),Defeated,true);
    if(Defeated)
    {
        // Keep the completed kill row so the tracker can show its strike-through.
        Add(TEXT("final.treasure"),TEXT("搜刮宝箱（可选）"),bFinalTreasureLooted,false);
        Add(TEXT("final.return"),TEXT("进入传送门离开"),bCompleted,false);
    }
    Out.Hint=FText::FromString(bCompleted?TEXT("正在返回主神空间"):
        !Defeated?TEXT("引合阙到侧台下方 · 登台按 E 泄压，失衡后攻击悬心"):
        !bFinalTreasureLooted?TEXT("奖励室可搜刮宝箱 · 也可在返程门确认放弃领取并离开"):
        TEXT("返程门已开启 · 靠近传送门按 E 离开"));
}


bool UDungeonRunSubsystem::CompletePlayerReturn(UColdSteelStatusModel* Model)
{
    if(!Model||GetWorld()->GetNetMode()==NM_Client||!CanUseFinalReturn()||Model->Snapshot().DungeonRun.RunId!=CurrentRunId)return false;
    auto Profile=Model->Snapshot();Profile.DungeonRun.bCompleted=true;
    return Model->CommitState(MoveTemp(Profile));
}
