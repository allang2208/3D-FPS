#if !UE_BUILD_SHIPPING
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace ForgedWorkbenchWire
{
const FString Definition=TEXT("ue_forged_steel_greatsword");
const FString Instance=TEXT("TransportAudit_Forged_Sword");
const TCHAR* Blades[]={TEXT("hollow_blade"),TEXT("executioner_blade")};
struct FRun
{
    bool Seeded=false,Hooked=false,Finished=false,Applied=false;
    int32 Phase=0;
    TSet<uint32> Uploads,Mirrors;
    TArray<TSharedPtr<FJsonValue>> Rows;
    double StartedAt=0.;
};
FRun Run;

// Observe the last received chunk at the engine's normal dispatch boundary.
// Returning false always delegates to the unmodified production implementation.
bool Observe(AActor* Actor,UFunction* Function,void* Parameters)
{
    const FName Name=Function->GetFName();
    const bool Upload=Name==GET_FUNCTION_NAME_CHECKED(AColdSteelPlayerState,ServerSubmitProfileChunk);
    if(!Upload&&Name!=GET_FUNCTION_NAME_CHECKED(AColdSteelPlayerState,ClientReceiveProfileChunk))return false;
    const auto* PS=Cast<AColdSteelPlayerState>(Actor);
    if(!PS||!(Upload?PS->GetNetMode()==NM_ListenServer:PS->GetNetMode()==NM_Client))return false;
    const auto* PC=Cast<APlayerController>(PS->GetOwner());
    if(!PC||PC->IsLocalController()==Upload)return false;
    const auto* Index=FindFProperty<FIntProperty>(Function,TEXT("ChunkIndex"));
    const auto* Count=FindFProperty<FIntProperty>(Function,TEXT("TotalChunks"));
    const auto* Sequence=FindFProperty<FUInt32Property>(Function,TEXT("GunsmithSequence"));
    if(Index&&Count&&Sequence&&Index->GetPropertyValue_InContainer(Parameters)+1==Count->GetPropertyValue_InContainer(Parameters))
        (Upload?Run.Uploads:Run.Mirrors).Add(Sequence->GetPropertyValue_InContainer(Parameters));
    return false;
}
void Finish(bool Passed,const TCHAR* Reason,UWorld* World)
{
    if(Run.Finished)return;
    Run.Finished=true;
    if(Run.Hooked)AActor::ProcessEventDelegate.Unbind();
    auto Root=MakeShared<FJsonObject>();
    Root->SetBoolField(TEXT("passed"),Passed);Root->SetStringField(TEXT("detail"),Reason);
    Root->SetStringField(TEXT("role"),World->GetNetMode()==NM_Client?TEXT("client"):TEXT("host"));
    Root->SetStringField(TEXT("instance"),Instance);Root->SetArrayField(TEXT("cases"),Run.Rows);
    Root->SetNumberField(TEXT("completed_phases"),Run.Phase);
    Root->SetBoolField(TEXT("actual_network_transport"),World->GetNetDriver()!=nullptr);
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {
        Root->SetNumberField(TEXT("latency_ms"),Driver->PacketSimulationSettings.PktLag);
        Root->SetNumberField(TEXT("packet_loss_percent"),Driver->PacketSimulationSettings.PktLoss);
    }
#endif
    FString Path,Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("WorkbenchWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("FORGED_WORKBENCH_WIRE %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Reason);
}
bool Matches(const UColdSteelStatusModel* Model,const UGunsmithSystem* Smith,int32 Phase)
{
    const auto* Item=Model?Model->FindItem(Instance):nullptr;
    if(!Item||Item->Definition!=Definition||Item->Place!=1||Item->Cell!=6)return false;
    const auto Parts=Smith->Installed(*Item);
    return Parts.FindRef(TEXT("blade_1"))==Blades[Phase]&&Parts.FindRef(TEXT("pommel"))==TEXT("ring_chain_pommel");
}
void Tick(UWorld* World,ELevelTick,float)
{
    if(Run.Finished||!World||World->WorldType!=EWorldType::Game||
        (World->GetNetMode()!=NM_ListenServer&&World->GetNetMode()!=NM_Client)||!World->GetNetDriver())return;
    const bool Host=World->GetNetMode()==NM_ListenServer;
    if(!Run.Hooked)
    {
        if(AActor::ProcessEventDelegate.IsBound()){Finish(false,TEXT("another ProcessEvent observer is installed"),World);return;}
        AActor::ProcessEventDelegate.BindStatic(&Observe);
        Run.Hooked=true;Run.StartedAt=FPlatformTime::Seconds();
#if DO_ENABLE_NET_TEST
        FPacketSimulationSettings Settings;Settings.PktLag=50;Settings.PktLoss=2;World->GetNetDriver()->SetPacketSimulationSettings(Settings);
#endif
    }
    if(FPlatformTime::Seconds()-Run.StartedAt>150.){Finish(false,TEXT("timed out before both revisions were received"),World);return;}
    auto* GI=World->GetGameInstance();auto* Smith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    auto* OwnerModel=GI?GI->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Smith||!OwnerModel||!OwnerModel->IsAudit())return;
    for(auto It=World->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();
        if(!PC||PC->IsLocalController()==Host)continue;
        auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn());auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();
        if(!Pawn||!PS)return;
        const uint32 Sequence=Run.Phase+1;
        if(!Host&&!Run.Seeded)
        {
            auto State=OwnerModel->Snapshot();State.Items.Reset();State.ActiveProductionTool.Reset();State.ActiveWeaponSlot=6;
            auto Item=OwnerModel->CreateItem(Definition);Item.InstanceId=Instance;Item.Place=1;Item.Cell=6;State.Items.Add(Item);
            if(!OwnerModel->CommitState(MoveTemp(State))){Finish(false,TEXT("isolated guest inventory rejected sword"),World);return;}
            OwnerModel->AttachPawn(Pawn);Run.Seeded=true;return;
        }
        if(!Host&&!Run.Applied)
        {
            if(OwnerModel->RuntimePawn()!=Pawn||!OwnerModel->FindItem(Instance))return;
            if(!Smith->Begin(Instance)||!Smith->Select(TEXT("blade_1"),Blades[Run.Phase])||
                !Smith->Select(TEXT("pommel"),TEXT("ring_chain_pommel"))){Finish(false,TEXT("workbench selection failed"),World);return;}
            FString Reason;if(!Smith->CanApply(Reason))return;
            if(!Smith->Apply()){Finish(false,TEXT("workbench Apply failed"),World);return;}
            Smith->Close();Run.Applied=true;
            UE_LOG(LogTemp,Display,TEXT("FORGED_WORKBENCH_APPLIED %u %s"),Sequence,Blades[Run.Phase]);return;
        }
        if(!(Host?Run.Uploads:Run.Mirrors).Contains(Sequence)||(!Host&&!PS->MirrorBlob.IsEmpty())||
            !Matches(Host?PS->GetShadowModel():OwnerModel,Smith,Run.Phase))return;
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("blade"),Blades[Run.Phase]);
        Row->SetStringField(TEXT("pommel"),TEXT("ring_chain_pommel"));Row->SetNumberField(TEXT("received_sequence"),Sequence);
        Row->SetStringField(TEXT("received_rpc"),Host?TEXT("ServerSubmitProfileChunk"):TEXT("ClientReceiveProfileChunk"));
        Row->SetBoolField(TEXT("equipped_parts_match"),true);
        Run.Rows.Add(MakeShared<FJsonValueObject>(Row));Run.Applied=false;
        if(++Run.Phase==UE_ARRAY_COUNT(Blades))Finish(true,TEXT("both workbench revisions received and equipped"),World);
        return;
    }
}
struct FRegister
{
    FRegister(){FCoreDelegates::GetOnPostEngineInit().AddLambda([](){
        if(FParse::Param(FCommandLine::Get(),TEXT("ForgedWorkbenchWireAudit")))
            FWorldDelegates::OnWorldPostActorTick.AddStatic(&Tick);
    });}
} Registration;
}
#endif
