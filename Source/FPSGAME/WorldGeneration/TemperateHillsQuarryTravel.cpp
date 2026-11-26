#include "TemperateHillsQuarryTravel.h"
#include "TemperateQuarryYard.h"
#include "ForestVillageRegion.h"
#include "Components/CapsuleComponent.h"
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
    if(IsForestVillage())
    {
        auto* Region=Streaming->ForestRegion.Get();
        if(!Region || Region->QuarryLevel.IsNull()){Reason=TEXT("林道采石场尚未接入。");return false;}
        const FVector Origin=Region->QuarryOrigin;
        const double X=Origin.X-TemperateQuarry::EntryY;
        const double Y=Origin.Y+TemperateQuarry::RoadX(TemperateQuarry::EntryY);
        const FVector Entry(X,Y,Region->GroundHeight(X,Y)+Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3.);
        const FVector Look(Origin.X-TemperateQuarry::EntryLook.Y,Origin.Y+TemperateQuarry::EntryLook.X,Entry.Z);
        const FRotator Facing(TemperateQuarry::EntryPitch,(Look-Entry).Rotation().Yaw,0.);
        if(!Player->TeleportTo(Entry,FRotator(0.,Facing.Yaw,0.))){Reason=TEXT("采石场入口被占用。");return false;}
        if(auto* PC=Cast<APlayerController>(Player->GetController())) { PC->SetControlRotation(Facing); PC->ClientSetRotation(Facing); }
        Reason=TEXT("已到达白崖采石场入口。");
        return true;
    }
    if(!RiverPlan||!RiverPlan->WhiteCliffs.Valid)
    {Reason=TEXT("当前丘陵尚未生成白崖采石场。");return false;}
    auto& State=*Streaming;
    if(State.Quarry.Stage==FTemperateHillsStreamingState::EQuarryStage::Failed)
    {Reason=TEXT("白崖采石场地标资源载入失败。");return false;}
    if(State.Visitor.IsValid()){Reason=TEXT("另一位玩家正在传送，请稍后重试。");return false;}
    const auto& Quarry=RiverPlan->WhiteCliffs;
    constexpr double RoadY=TemperateQuarry::EntryY;const double RoadX=TemperateQuarry::RoadX(RoadY);
    State.bVillageVisit=false;State.bWhiteCliffsVisit=true;
    State.StageVisit(Player,Quarry.World(RoadX,RoadY),Quarry.World(TemperateQuarry::EntryLook.X,TemperateQuarry::EntryLook.Y),SizeMeters*50.);
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
void ATemperateHillsWorld::PrefetchQuarryVisit()
{
#if !UE_BUILD_SHIPPING
    if(bReady&&Streaming&&RiverPlan&&RiverPlan->WhiteCliffs.Valid)Streaming->Quarry.Requested=true;
#endif
}
void TemperateHillsQuarryTravel::Request(UWorld* World)
{
#if !UE_BUILD_SHIPPING
    if(!World||!World->IsGameWorld())return;
    auto* PC=World->GetFirstPlayerController();if(!PC||!PC->IsLocalController())return;
    if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())
    {
        if(World->GetNetMode()==NM_Client)
            for(TActorIterator<ATemperateHillsWorld> It(World);It;++It){It->PrefetchQuarryVisit();break;}
        PS->ServerVisitHillsQuarry();
    }
#endif
}
