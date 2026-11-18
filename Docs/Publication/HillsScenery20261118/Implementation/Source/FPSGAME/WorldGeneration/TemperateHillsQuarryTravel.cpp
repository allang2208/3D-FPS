#include "TemperateHillsQuarryTravel.h"
#include "TemperateHillsPCG.h"
#include "TemperateHillsStreamingPrivate.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"

bool ATemperateHillsWorld::RequestQuarryVisit(ACharacter* Player,FString& Reason)
{
#if !UE_BUILD_SHIPPING
    if(!HasAuthority()||!Player||Player->GetWorld()!=GetWorld()||!bReady||!Streaming||Streaming->Failed)
    {Reason=TEXT("请等待丘陵加载完成后再传送。");return false;}
    if(!RiverPlan||!RiverPlan->WhiteCliffs.Valid)
    {Reason=TEXT("当前丘陵尚未生成白崖采石场。");return false;}
    auto& State=*Streaming;
    if(!State.WhiteCliffsBuilt){Reason=TEXT("白崖采石场地标资源仍在准备。");return false;}
    if(State.Visitor.IsValid()){Reason=TEXT("另一位玩家正在传送，请稍后重试。");return false;}
    const auto& Quarry=RiverPlan->WhiteCliffs;
    constexpr double RoadY=-3600.;const double RoadX=2200.*FMath::Sin(RoadY/2600.);
    State.bVillageVisit=false;State.bWhiteCliffsVisit=true;
    State.StageVisit(Player,Quarry.World(RoadX,RoadY),Quarry.World(0.,2500.),SizeMeters*50.);
    Reason=TEXT("正在准备白崖采石场入口的地面碰撞…");return true;
#else
    return false;
#endif
}
void AColdSteelPlayerState::ServerVisitHillsQuarry_Implementation()
{
#if !UE_BUILD_SHIPPING
    auto* PC=Cast<APlayerController>(GetOwner());auto* Player=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
    if(!HasAuthority()||!Player||Player->GetPlayerState()!=this)return;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
    {FString Reason;It->RequestQuarryVisit(Player,Reason);PC->ClientMessage(Reason);return;}
    PC->ClientMessage(TEXT("请先进入丘陵场景。"));
#endif
}
void TemperateHillsQuarryTravel::Request(UWorld* World)
{
#if !UE_BUILD_SHIPPING
    if(!World||!World->IsGameWorld())return;
    auto* PC=World->GetFirstPlayerController();if(!PC||!PC->IsLocalController())return;
    if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())PS->ServerVisitHillsQuarry();
#endif
}
