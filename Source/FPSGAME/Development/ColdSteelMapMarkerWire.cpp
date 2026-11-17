#include "ColdSteelMapMarkerWire.h"
#include "../Multiplayer/ColdSteelMapMarkerSharing.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "GameFramework/DefaultPawn.h"
#include "GameFramework/GameStateBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"

namespace MapMarkerWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("MapMarkerWire"));}
const TCHAR* Cases[]={TEXT("private isolation"),TEXT("host share"),TEXT("guest share"),
    TEXT("rename recolor position and read-only"),TEXT("own quota and forged peer id"),
    TEXT("server quota"),TEXT("withdraw to personal"),TEXT("reshare"),
    TEXT("disconnect cleanup"),TEXT("same-profile reconnect and late snapshot"),TEXT("delete shared")};
}

void AColdSteelMapMarkerWireController::ClientStage_Implementation(int32 Value)
{
    if(!MapMarkerWire::Enabled())return;
    Stage=Value;Started=Reported=false;ActionsOK=true;Rejected=false;ProbeId.Invalidate();
    StageAt=FPlatformTime::Seconds();
}
void AColdSteelMapMarkerWireController::ClientExit_Implementation()
{if(MapMarkerWire::Enabled())FPlatformMisc::RequestExit(false);}
void AColdSteelMapMarkerWireController::ServerReport_Implementation(int32 Value,const FString& Json)
{
    if(MapMarkerWire::Enabled()&&Value==Expected)
        if(auto* GM=GetWorld()->GetAuthGameMode<AColdSteelMapMarkerWireGameMode>())GM->Receive(this,Value,Json);
}

bool AColdSteelMapMarkerWireController::Exercise()
{
    const bool Host=HasAuthority();
    auto Create=[&](const FString& Label,EColdSteelMapMarkerVisibility Visibility)
    {
        FColdSteelMapMarker M;M.Region=TEXT("Entry");M.Label=Label;M.Area=TEXT("Wire fixture");
        M.Position=Host?FVector(300,200,0):FVector(400,-200,0);M.ColorIndex=Host?1:2;M.Visibility=Visibility;
        ActionsOK&=Markers.Save(M);return M.Id;
    };
    auto Change=[&](FGuid Id,EColdSteelMapMarkerVisibility Visibility)
    {
        const auto* Found=Markers.Find(Id);if(!Found){ActionsOK=false;return;}
        auto M=*Found;M.Visibility=Visibility;ActionsOK&=Markers.Save(M);
    };
    if(Stage==0)PrivateId=Create(Host?TEXT("HostPrivate"):TEXT("GuestPrivate"),EColdSteelMapMarkerVisibility::Personal);
    if(Stage==1&&Host)SharedId=Create(TEXT("HostShared"),EColdSteelMapMarkerVisibility::Team);
    if(Stage==2&&!Host)SharedId=Create(TEXT("GuestShared"),EColdSteelMapMarkerVisibility::Team);
    if(Stage==3)
    {
        if(Host)
        {
            if(const auto* Found=Markers.Find(SharedId))
            {auto M=*Found;M.Label=TEXT("HostRenamed");M.ColorIndex=4;M.Position=FVector(600,800,0);ActionsOK&=Markers.Save(M);}
            else ActionsOK=false;
        }
        else if(!Markers.Received.IsEmpty())
        {
            auto Copy=Markers.Received[0];const FGuid Id=Copy.Id;
            Copy.Label=TEXT("Unauthorized");ActionsOK&=!Markers.Save(Copy);Markers.Remove(Id);ActionsOK&=Markers.Find(Id)!=nullptr;
        }
        else ActionsOK=false;
    }
    if(Stage==4)
    {
        while(Markers.OwnedCount()<FColdSteelMapMarkers::Limit&&ActionsOK)
            Create(FString::Printf(TEXT("Extra%d"),Markers.OwnedCount()),EColdSteelMapMarkerVisibility::Personal);
        FColdSteelMapMarker Extra;Extra.Region=TEXT("Entry");Extra.Label=TEXT("Overflow");
        ActionsOK&=!Markers.Save(Extra)&&Markers.OwnedCount()==10;
        if(!Host&&!Markers.Received.IsEmpty())
        {
            auto Copy=Markers.Received[0];ProbeId=Copy.Id;Copy.Label=TEXT("ForgedPeer");
            UColdSteelMapMarkerSharing::For(this)->Publish(Copy);
            UColdSteelMapMarkerSharing::For(this)->Withdraw(Copy.Id);
        }
    }
    if(Stage==5)
    {
        const auto Own=Markers.Entries;
        for(const auto& M:Own)Change(M.Id,EColdSteelMapMarkerVisibility::Team);
        FColdSteelMapMarker Extra;Extra.Region=TEXT("Entry");Extra.Label=TEXT("ServerOverflow");
        Extra.Id=FGuid::NewGuid();ProbeId=Extra.Id;
        UColdSteelMapMarkerSharing::For(this)->Publish(Extra);
    }
    if(Stage==6)
    {
        const auto Own=Markers.Entries;
        for(const auto& M:Own)if(M.Id!=PrivateId&&M.Id!=SharedId)Markers.Remove(M.Id);
        Change(PrivateId,EColdSteelMapMarkerVisibility::Personal);
        if(Host)Change(SharedId,EColdSteelMapMarkerVisibility::Personal);
    }
    if(Stage==7&&Host)Change(SharedId,EColdSteelMapMarkerVisibility::Team);
    if(Stage==10&&Host)Markers.Remove(SharedId);
    return ActionsOK;
}

bool AColdSteelMapMarkerWireController::Observe(FString& Detail)
{
    const bool Host=HasAuthority();
    const auto* Network=UColdSteelMapMarkerSharing::For(this);
    int32 Own=2,Incoming=1,Shared=1;
    if(Stage==0){Own=1;Incoming=0;Shared=0;}
    if(Stage==1){Own=Host?2:1;Incoming=Host?0:1;Shared=Host?1:0;}
    if(Stage==4)Own=10;
    if(Stage==5){Own=10;Incoming=10;Shared=10;}
    if(Stage==6){Incoming=Host?1:0;Shared=Host?0:1;}
    if(Stage==8){Incoming=0;}
    if(Stage==9){Own=Host?2:0;Incoming=Host?0:1;Shared=Host?1:0;}
    if(Stage==10){Own=Host?1:0;Incoming=0;Shared=0;}
    bool Good=Markers.OwnedCount()==Own&&Markers.TeammateCount()==Incoming&&Network->Shared().Num()==Shared;
    if(Stage==5||(Stage==4&&!Host))Good&=Rejected;
    for(const auto& M:Markers.Received)
    {
        Good&=M.bReadOnly&&M.Visibility==EColdSteelMapMarkerVisibility::Team&&!M.OwnerName.IsEmpty();
        if(Stage!=5)Good&=!M.Label.Contains(TEXT("Private"))&&!M.Label.Contains(TEXT("Extra"));
        if(!Host&&Stage>=3&&M.Label.StartsWith(TEXT("Host"))&&!M.Label.Contains(TEXT("Private")))
            Good&=M.Label==TEXT("HostRenamed")&&M.ColorIndex==4&&M.Position.Equals(FVector(600,800,0),.1);
    }
    // Every active pin must have a client-local beam with the same color and viewer ownership.
    for(const auto& M:Markers.All())
    {
        const auto* Beam=Markers.Beams.FindRef(M.Id).Get();
        const auto* Mesh=Beam?Cast<UStaticMeshComponent>(Beam->GetRootComponent()):nullptr;
        const auto* MID=Mesh?Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)):nullptr;
        FLinearColor BeamColor;
        Good&=Beam&&!Beam->GetIsReplicated()&&Beam->GetOwner()==GetViewTarget()&&!Beam->IsHidden()&&MID&&
            MID->GetVectorParameterValue(FMaterialParameterInfo(TEXT("LootColor")),BeamColor)&&BeamColor.Equals(FColdSteelMapMarkers::Color(M.ColorIndex),.001f);
    }
    Good&=Markers.Beams.Num()==Markers.All().Num()&&Fog.Layers.IsEmpty();
    Detail=FString::Printf(TEXT("own=%d/%d peer=%d/%d serverSnapshot=%d/%d beams=%d rejected=%d"),
        Markers.OwnedCount(),Own,Markers.TeammateCount(),Incoming,Network->Shared().Num(),Shared,Markers.Beams.Num(),Rejected);
    return Good;
}

void AColdSteelMapMarkerWireController::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!MapMarkerWire::Enabled()||!IsLocalController())return;
    auto* Network=UColdSteelMapMarkerSharing::For(this);
    if(!GetPawn()||!Network)return;
    for(const auto& Result:Network->Results)if(Result.Id==ProbeId&&!Result.bAccepted)Rejected=true;
    Markers.Update(this,Fog,false);
    if(Stage<0||Reported)return;
    if(!Started){Started=true;StageAt=FPlatformTime::Seconds();Exercise();}
    FString Detail;const bool Good=Observe(Detail)&&ActionsOK;
    const double Age=FPlatformTime::Seconds()-StageAt;
    if(Age<1.5||(!Good&&Age<25.))return;
    Reported=true;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("stage"),Stage);
    Row->SetStringField(TEXT("case"),MapMarkerWire::Cases[Stage]);Row->SetStringField(TEXT("role"),HasAuthority()?TEXT("host"):TEXT("client"));
    Row->SetBoolField(TEXT("passed"),Good);Row->SetBoolField(TEXT("actions"),ActionsOK);Row->SetStringField(TEXT("observed"),Detail);
    Row->SetNumberField(TEXT("seconds"),Age);Row->SetNumberField(TEXT("pid"),FPlatformProcess::GetCurrentProcessId());
    if(const auto* Driver=GetWorld()->GetNetDriver())
    {
        Row->SetStringField(TEXT("net_driver"),Driver->GetClass()->GetName());
#if DO_ENABLE_NET_TEST
        Row->SetNumberField(TEXT("packet_lag_ms"),Driver->PacketSimulationSettings.PktLag);
        Row->SetNumberField(TEXT("packet_loss_percent"),Driver->PacketSimulationSettings.PktLoss);
#endif
    }
    FString Json;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Json));
    UE_LOG(LogTemp,Display,TEXT("MAP_MARKER_WIRE_OBSERVED %s"),*Json);ServerReport(Stage,Json);
}

AColdSteelMapMarkerWireGameMode::AColdSteelMapMarkerWireGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AColdSteelMapMarkerWireController::StaticClass();
    PlayerStateClass=AColdSteelPlayerState::StaticClass();DefaultPawnClass=ADefaultPawn::StaticClass();
}
void AColdSteelMapMarkerWireGameMode::BeginPlay()
{
    Super::BeginPlay();if(MapMarkerWire::Enabled())UE_LOG(LogTemp,Display,TEXT("MAP_MARKER_WIRE_HOST_READY"));
}
void AColdSteelMapMarkerWireGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(!MapMarkerWire::Enabled())return;
    auto* PC=CastChecked<AColdSteelMapMarkerWireController>(Player);
    if(PC->IsLocalController())Host=PC;
    else {Guest=PC;++GuestCount;}
    if(auto* State=PC->GetPlayerState<APlayerState>())State->SetPlayerName(PC->IsLocalController()?TEXT("Host"):TEXT("Guest"));
    if(Host&&Guest.IsValid())Dispatch(GuestCount==1?0:9);
}
void AColdSteelMapMarkerWireGameMode::Dispatch(int32 Value)
{
    Phase=Value;Replies=0;Advance=false;PhaseAt=FPlatformTime::Seconds();
    Host->Expected=Value;Host->ClientStage(Value);
    if(auto* PC=Guest.Get()){PC->Expected=Value;PC->ClientStage(Value);}
    UE_LOG(LogTemp,Display,TEXT("MAP_MARKER_WIRE_STAGE %d"),Value);
}
void AColdSteelMapMarkerWireGameMode::Receive(AColdSteelMapMarkerWireController* PC,int32 Value,const FString& Json)
{
    if(Finished||Value!=Phase||PC->Expected!=Value)return;
    PC->Expected=INDEX_NONE;
    TSharedPtr<FJsonObject> Row;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Row)||!Row){Finish(false);return;}
    Passed&=Row->GetBoolField(TEXT("passed"));Rows.Add(MakeShared<FJsonValueObject>(Row));
    ++Replies;Advance=Replies==(Phase==8?1:2);
}
void AColdSteelMapMarkerWireGameMode::Finish(bool Success)
{
    if(Finished)return;Finished=true;Passed&=Success;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Passed);Report->SetArrayField(TEXT("observations"),Rows);
    Report->SetStringField(TEXT("scope"),TEXT("real UDP listen host plus client, same-profile reconnect; production marker model, RPC, snapshots and local beam material data; NullRHI, no visual or mouse-input acceptance"));
    FString Output;FParse::Value(FCommandLine::Get(),TEXT("MapMarkerWireOutput="),Output);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Json,*Output);
    UE_LOG(LogTemp,Display,TEXT("MAP_MARKER_WIRE_RESULT pass=%d observations=%d"),Passed,Rows.Num());
    if(auto* PC=Guest.Get())PC->ClientExit();ExitAt=FPlatformTime::Seconds()+2.;
}
void AColdSteelMapMarkerWireGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!MapMarkerWire::Enabled())return;
    if(ExitAt>0&&FPlatformTime::Seconds()>ExitAt){FPlatformMisc::RequestExit(false);return;}
    if(Finished)return;
    if(AwaitingDisconnect&&!Guest.IsValid()){AwaitingDisconnect=false;Dispatch(8);}
    if(!Advance)
    {if(Phase>=0&&FPlatformTime::Seconds()-PhaseAt>90.&&!AwaitingDisconnect)Finish(false);return;}
    Advance=false;
    if(!Passed){Finish(false);return;}
    if(Phase==7){Guest->ClientExit();AwaitingDisconnect=true;PhaseAt=FPlatformTime::Seconds();}
    else if(Phase==8){Phase=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("MAP_MARKER_WIRE_REJOIN_READY"));}
    else if(Phase==10)Finish(true);
    else Dispatch(Phase+1);
}
