#include "ColdSteelMapMarkerSharing.h"
#include "../UI/ColdSteelMapMarkers.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

UColdSteelMapMarkerSharing::UColdSteelMapMarkerSharing()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickInterval=.5f;
}

UColdSteelMapMarkerSharing* UColdSteelMapMarkerSharing::For(const APlayerController* Player)
{
    const auto* State=Player?Player->GetPlayerState<APlayerState>():nullptr;
    return State?State->FindComponentByClass<UColdSteelMapMarkerSharing>():nullptr;
}

void UColdSteelMapMarkerSharing::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UColdSteelMapMarkerSharing,SharedMarkers);
}

void UColdSteelMapMarkerSharing::BeginPlay()
{
    Super::BeginPlay();
    BindWorld();
    SetComponentTickEnabled(GetOwner()->HasAuthority());
}

void UColdSteelMapMarkerSharing::BindWorld()
{
    if(BoundWorld.Get()==GetWorld())return;
    BoundWorld=GetWorld();Hills.Reset();bSearchedHills=false;
    if(GetOwner()->HasAuthority()&&!SharedMarkers.IsEmpty()){SharedMarkers.Reset();Changed();}
}

void UColdSteelMapMarkerSharing::EndPlay(const EEndPlayReason::Type Reason)
{
    SharedMarkers.Reset();Results.Reset();++ChangeSerial;
    Super::EndPlay(Reason);
}

void UColdSteelMapMarkerSharing::Changed(){++ChangeSerial;GetOwner()->ForceNetUpdate();}
void UColdSteelMapMarkerSharing::OnRep_SharedMarkers(){++ChangeSerial;}

uint32 UColdSteelMapMarkerSharing::Publish(const FColdSteelMapMarker& Marker)
{
    FColdSteelSharedMapMarker Wire;
    Wire.Id=Marker.Id;Wire.Region=Marker.Region;Wire.Area=Marker.Area;Wire.Label=Marker.Label;
    Wire.AbsolutePosition=Marker.Position+FVector(GetWorld()->OriginLocation);
    Wire.Floor=Marker.Floor;Wire.ColorIndex=uint8(Marker.ColorIndex);Wire.bDungeon=Marker.bDungeon;
    const uint32 Request=++NextRequest;
    ServerPublish(Wire,Request);
    return Request;
}

uint32 UColdSteelMapMarkerSharing::Withdraw(FGuid Id)
{
    const uint32 Request=++NextRequest;
    ServerWithdraw(Id,Request);
    return Request;
}

void UColdSteelMapMarkerSharing::TakeResults(TArray<FColdSteelMapShareResult>& Out)
{
    Out=MoveTemp(Results);Results.Reset();
}

FString UColdSteelMapMarkerSharing::NonDungeonRegion()
{
    FString Region=UGameplayStatics::GetCurrentLevelName(GetWorld(),true);
    if(!bSearchedHills)
    {
        bSearchedHills=true;
        for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){Hills=*It;break;}
    }
    if(const auto* Terrain=Hills.Get())Region+=FString::Printf(TEXT("/%d/%s"),Terrain->Seed,*Terrain->WorldId.ToString());
    return Region;
}

bool UColdSteelMapMarkerSharing::RegionIsCurrent(const FColdSteelSharedMapMarker& Marker)
{
    if(Marker.bDungeon)
    {
        const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
        return Run&&Run->MapLevel()&&Marker.Region==TEXT("L_Dungeon_Randomized/")+Run->RunId();
    }
    return Marker.Region==NonDungeonRegion();
}

bool UColdSteelMapMarkerSharing::Validate(const FColdSteelSharedMapMarker& Marker,FString& Reason)
{
    const auto* State=Cast<APlayerState>(GetOwner());
    if(!State||!Cast<APlayerController>(State->GetOwner())){Reason=TEXT("玩家连接尚未就绪");return false;}
    if(!Marker.Id.IsValid()||Marker.Region.Len()>256||Marker.Area.Len()>64||Marker.Label.IsEmpty()||
        Marker.Label.Len()>FColdSteelMapMarkers::LabelLimit||FColdSteelMapMarkers::CleanLabel(Marker.Label)!=Marker.Label||
        Marker.ColorIndex>=FColdSteelMapMarkers::ColorCount||Marker.AbsolutePosition.ContainsNaN()||
        Marker.AbsolutePosition.GetAbsMax()>1.e9||Marker.Floor < -128||Marker.Floor > 128||(!Marker.bDungeon&&Marker.Floor!=0))
    {Reason=TEXT("标记内容无效");return false;}
    if(!RegionIsCurrent(Marker)){Reason=TEXT("所在场景或地牢已改变");return false;}
    if(Marker.bDungeon)
    {
        const auto* Run=UDungeonRunSubsystem::Get(GetWorld());
        const FVector Position=Marker.AbsolutePosition-FVector(GetWorld()->OriginLocation);
        bool bInside=Run->StartRoomBounds().IsValid&&Run->StartRoomBounds().ExpandBy(150.).IsInsideOrOn(Position);
        for(const auto& Node:Run->AllNodes())bInside|=Node.Volume.IsValid&&Node.Volume.ExpandBy(150.).IsInsideOrOn(Position);
        if(!bInside){Reason=TEXT("标记不在当前地牢范围");return false;}
    }
    const bool bExisting=SharedMarkers.ContainsByPredicate([&](const auto& Item){return Item.Id==Marker.Id;});
    if(!bExisting&&SharedMarkers.Num()>=FColdSteelMapMarkers::Limit){Reason=TEXT("共享标记已达上限");return false;}
    if(const auto* GameState=GetWorld()->GetGameState())for(const auto& Peer:GameState->PlayerArray)
    {
        if(!Peer||Peer==State)continue;
        const auto* Shared=Peer->FindComponentByClass<UColdSteelMapMarkerSharing>();
        if(Shared&&Shared->SharedMarkers.ContainsByPredicate([&](const auto& Item){return Item.Id==Marker.Id;}))
        {Reason=TEXT("不能修改队友的标记");return false;}
    }
    return true;
}

void UColdSteelMapMarkerSharing::ServerPublish_Implementation(FColdSteelSharedMapMarker Marker,uint32 Request)
{
    if(Request==0||Request<=LastRequest)return;
    LastRequest=Request;BindWorld();
    FString Reason;
    if(!Validate(Marker,Reason))
    {
        // An unsuccessful latest share leaves an owner-only marker, never an older public version.
        if(SharedMarkers.RemoveAll([&](const auto& Item){return Item.Id==Marker.Id;}))Changed();
        ClientResult(Marker.Id,Request,false,Reason);
        return;
    }
    if(auto* Existing=SharedMarkers.FindByPredicate([&](const auto& Item){return Item.Id==Marker.Id;}))*Existing=Marker;
    else SharedMarkers.Add(Marker);
    Changed();ClientResult(Marker.Id,Request,true,FString());
}

void UColdSteelMapMarkerSharing::ServerWithdraw_Implementation(FGuid Id,uint32 Request)
{
    if(Request==0||Request<=LastRequest)return;
    LastRequest=Request;BindWorld();
    if(SharedMarkers.RemoveAll([&](const auto& Item){return Item.Id==Id;}))Changed();
    ClientResult(Id,Request,true,FString());
}

void UColdSteelMapMarkerSharing::ClientResult_Implementation(FGuid Id,uint32 Request,bool bAccepted,const FString& Reason)
{
    Results.Add({Id,Request,bAccepted,Reason});
}

void UColdSteelMapMarkerSharing::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(DeltaTime,TickType,Tick);
    if(!GetOwner()->HasAuthority())return;
    BindWorld();
    if(SharedMarkers.RemoveAll([this](const auto& Marker){return !RegionIsCurrent(Marker);}))Changed();
}
