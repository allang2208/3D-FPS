#include "SwordFinishWireAudit.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace SwordFinishWire
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("SwordFinishWireAudit"));}
const TCHAR* Names[]={TEXT("late_join_existing_finish"),TEXT("finish_only_change"),TEXT("native_rune_and_guard_change"),
    TEXT("factory_finish_restore"),TEXT("unequip"),TEXT("reequip"),TEXT("reconnect_retained_equipment")};
struct FSelection {const TCHAR* Finish;const TCHAR* Rune;const TCHAR* Guard;uint8 Mode;};
FSelection Selection(int32 Phase,bool Host)
{
    if(Phase==0)return Host?FSelection{TEXT("dark_iron"),TEXT("golden_glow_rune"),TEXT("twin_star_guard"),2}:
        FSelection{TEXT("damascus_steel"),TEXT("silver_glow_rune"),TEXT("starfall_nexus_guard"),4};
    if(Phase==1)return Host?FSelection{TEXT("mithril"),TEXT("golden_glow_rune"),TEXT("twin_star_guard"),3}:
        FSelection{TEXT("folded_steel"),TEXT("silver_glow_rune"),TEXT("starfall_nexus_guard"),1};
    if(Phase==3)return {TEXT("false"),TEXT("false"),Host?TEXT("starfall_nexus_guard"):TEXT("twin_star_guard"),0};
    return Host?FSelection{TEXT("meteoric_iron"),TEXT("silver_glow_rune"),TEXT("starfall_nexus_guard"),5}:
        FSelection{TEXT("dark_iron"),TEXT("golden_glow_rune"),TEXT("twin_star_guard"),2};
}
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {FPacketSimulationSettings Settings;Settings.PktLag=60;Settings.PktLoss=3;Driver->SetPacketSimulationSettings(Settings);
        UE_LOG(LogTemp,Display,TEXT("SWORD_FINISH_WIRE_NETWORK mode=%d lag=%d loss=%d"),int32(World->GetNetMode()),Driver->PacketSimulationSettings.PktLag,Driver->PacketSimulationSettings.PktLoss);}
#endif
}
FString Identity(bool Host){return Host?TEXT("SwordFinishAudit_HostSword"):TEXT("SwordFinishAudit_GuestSword");}
FColdSteelProfile Seed(UColdSteelStatusModel* Model,bool Host)
{
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};
    State.Stamina=150;State.bSprintExhausted=false;
    auto Item=Model->CreateItem(TEXT("ue_rune_sword"));Item.Place=1;Item.Cell=6;Item.InstanceId=Identity(Host);State.Items.Add(Item);
    return State;
}
void Prepare(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Model,int32 Phase,bool Host)
{
    Pawn->SetActorLocation(FVector(0,Host?1000:0,500));Pawn->GetCharacterMovement()->StopMovementImmediately();
    Pawn->GetCharacterMovement()->GravityScale=0;Pawn->GetCharacterMovement()->SetComponentTickEnabled(false);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pawn->SetActorTickEnabled(false);
    auto State=Model->Snapshot();State.ActiveWeaponSlot=Phase==4?9:6;
    const auto Desired=Selection(Phase,Host);
    for(auto& Item:State.Items)if(Item.InstanceId==Identity(Host))
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_material"),Desired.Finish);
        Parts->SetStringField(TEXT("blade_2"),Desired.Rune);Parts->SetStringField(TEXT("guard"),Desired.Guard);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&Item.Data));
    }
    Model->AdoptNetMirror(State);Model->AttachPawn(Pawn);
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->RefreshEquipment();
    Pawn->ForceNetUpdate();
}
bool Check(AFPSGAMECharacter* Pawn,int32 Phase,bool Host,FString& Details)
{
    auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    if(!Body){Details=TEXT("body unavailable");return false;}
    const auto Desired=Selection(Phase,Host);
    const auto* Property=FindFProperty<FArrayProperty>(Body->GetClass(),TEXT("ReplicatedWeapons"));
    const auto* Weapons=Property?Property->ContainerPtrToValuePtr<TArray<FFPSBodyWeapon>>(Body):nullptr;
    TArray<FFPSWeatherWeaponMesh> Meshes;Body->GetWeatherWeaponMeshes(Meshes,true);
    int32 Snapshots=0,WorldParts=0;bool SnapshotOK=Weapons!=nullptr,SurfaceOK=true,InkOK=true;
    if(Weapons)for(const auto& Weapon:*Weapons)if(Weapon.ItemInstance==Identity(Host))
        for(const auto& Part:Weapon.Parts)if(Part.Slot==TEXT("blade_1")||Part.Slot==TEXT("guard"))
        {
            ++Snapshots;SnapshotOK&=Part.BladeFinishMode==Desired.Mode&&Part.bBladeFinishGuardRoot==(Part.Slot==TEXT("guard"));
        }
    for(const auto& Entry:Meshes)
    {
        auto* Mesh=Cast<UStaticMeshComponent>(Entry.Mesh);if(!Mesh||Entry.Instance!=Identity(Host))continue;
        const bool Root=Mesh->ComponentHasTag(TEXT("SwordSlot=guard"));
        if(!Root&&!Mesh->ComponentHasTag(TEXT("SwordSlot=blade_1")))continue;
        ++WorldParts;int32 Surfaces=0;
        for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
        {
            auto* M=Mesh->GetMaterial(Slot);float Mode=0,Scope=0;
            if(!M||!M->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BladeFinishMode")),Mode))continue;
            ++Surfaces;SurfaceOK&=FMath::IsNearlyEqual(Mode,float(Desired.Mode))&&M->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BladeFinishGuardRoot")),Scope)&&Scope==(Root?1.f:0.f);
            if(Phase!=3)
            {
                auto* MID=Cast<UMaterialInstanceDynamic>(M);auto* Mask=MID?MID->K2_GetTextureParameterValue(TEXT("NativeRuneMask")):nullptr;
                InkOK&=Mask&&Mask->GetName()==(Root?TEXT("T_RuneSword_GuardNativeMask"):TEXT("T_RuneSword_NativeMask"));
            }
        }
        SurfaceOK&=Surfaces>0;
    }
    Details=FString::Printf(TEXT("instance=%s mode=%u snapshots=%d snapshot_ok=%d world_parts=%d surface_ok=%d ink_ok=%d local=%d"),
        *Identity(Host),Desired.Mode,Snapshots,SnapshotOK,WorldParts,SurfaceOK,InkOK,Pawn->IsLocallyControlled());
    return Phase==4?Snapshots==0&&WorldParts==0:Snapshots==2&&WorldParts==2&&SnapshotOK&&SurfaceOK&&InkOK;
}
}

void ASwordFinishWireController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(ASwordFinishWireController,Subject);DOREPLIFETIME(ASwordFinishWireController,Phase);}
void ASwordFinishWireController::Tick(float Delta)
{
    Super::Tick(Delta);if(!SwordFinishWire::Enabled()||HasAuthority()||!IsLocalController())return;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* Controlled=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Controlled||!Subject||Phase<0||Phase>6||!Model||!Model->IsAudit())return;
    if(Prepared!=Phase)
    {
        if(Prepared<0){SwordFinishWire::Network(GetWorld());Model->AdoptNetMirror(SwordFinishWire::Seed(Model,false));}
        Prepared=Phase;Started=Now;LastSent=-10;SwordFinishWire::Prepare(Controlled,Model,Phase,false);
    }
    if(Now-Started<1.||Now-LastSent<.5)return;
    FString OwnerDetails,Observer;const bool A=SwordFinishWire::Check(Controlled,Phase,false,OwnerDetails),B=SwordFinishWire::Check(Subject,Phase,true,Observer);
    if((A&&B)||Now-Started>60.){LastSent=Now;ServerResult(Phase,A&&B,OwnerDetails+TEXT(" | host observer: ")+Observer);}
}
void ASwordFinishWireController::ServerResult_Implementation(int32 Case,bool Passed,const FString& Details)
{if(SwordFinishWire::Enabled()&&!Reported&&Case==Phase)if(auto* GM=GetWorld()->GetAuthGameMode<ASwordFinishWireGameMode>())GM->Record(this,Case,Passed,Details);}
void ASwordFinishWireController::ClientFinish_Implementation()
{if(SwordFinishWire::Enabled())ExitAt=GetWorld()->GetRealTimeSeconds()+.5;}
ASwordFinishWireGameMode::ASwordFinishWireGameMode()
{PlayerControllerClass=ASwordFinishWireController::StaticClass();PlayerStateClass=ASwordFinishWireState::StaticClass();DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;}
void ASwordFinishWireGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(!SwordFinishWire::Enabled()||Player->IsLocalController())return;
    Guest=Cast<ASwordFinishWireController>(Player);Prepared=INDEX_NONE;PhaseAt=GetWorld()->GetRealTimeSeconds();
    if(AwaitingReconnect){Reconnected=true;NextPhase=6;AwaitingReconnect=false;}
}
void ASwordFinishWireGameMode::Logout(AController* Player)
{
    const bool Leaving=Player==Guest;Super::Logout(Player);
    if(Leaving){Guest=nullptr;if(AwaitingReconnect)UE_LOG(LogTemp,Display,TEXT("SWORD_FINISH_WIRE_REJOIN_READY"));}
}
void ASwordFinishWireGameMode::Record(ASwordFinishWireController* Sender,int32 Case,bool ClientPassed,const FString& Details)
{
    if(Sender!=Guest||Case!=NextPhase||Case<0||Case>6)return;
    FString HostView,GuestView;const bool A=SwordFinishWire::Check(Host,Case,true,HostView);
    const bool B=SwordFinishWire::Check(Cast<AFPSGAMECharacter>(Guest->GetPawn()),Case,false,GuestView);
    if(ClientPassed&&(!A||!B)&&GetWorld()->GetRealTimeSeconds()-PhaseAt<60.)return;
    const bool OK=ClientPassed&&A&&B&&(Case!=6||Reconnected);
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),SwordFinishWire::Names[Case]);Row->SetBoolField(TEXT("passed"),OK);
    Row->SetStringField(TEXT("client"),Details);Row->SetStringField(TEXT("server_host"),HostView);Row->SetStringField(TEXT("server_guest"),GuestView);
    Rows.Add(MakeShared<FJsonValueObject>(Row));Passed&=OK;Sender->Reported=true;
    UE_LOG(LogTemp,Display,TEXT("SWORD_FINISH_WIRE_CASE %d passed=%d %s | server: %s / %s"),Case,OK,*Details,*HostView,*GuestView);
    if(!OK||Case==6){Finish();return;}
    ++NextPhase;
    if(Case==5){AwaitingReconnect=true;Guest->ClientFinish();}
}
void ASwordFinishWireGameMode::Finish()
{
    if(ExitAt>=0)return;
    auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("passed"),Passed&&Rows.Num()==7&&Reconnected);Result->SetArrayField(TEXT("cases"),Rows);
    Result->SetBoolField(TEXT("actual_network_transport"),GetWorld()->GetNetDriver()!=nullptr);Result->SetBoolField(TEXT("rendered"),false);
    Result->SetBoolField(TEXT("reconnected"),Reconnected);Result->SetStringField(TEXT("scope"),TEXT("production body equipment capture/replication/OnRep reconstruction over UDP; same retained server-side item instances after reconnect; fixture-seeded inventory, no attack RPC or inventory upload"));
#if DO_ENABLE_NET_TEST
    if(const auto* Driver=GetWorld()->GetNetDriver()){Result->SetNumberField(TEXT("lag_ms_per_peer"),Driver->PacketSimulationSettings.PktLag);Result->SetNumberField(TEXT("loss_percent_per_peer"),Driver->PacketSimulationSettings.PktLoss);}
#endif
    FString Json,Path;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    if(FParse::Value(FCommandLine::Get(),TEXT("SwordFinishWireOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("SWORD_FINISH_WIRE_FINISHED passed=%d"),Passed&&Rows.Num()==7&&Reconnected);
    if(Guest)Guest->ClientFinish();ExitAt=GetWorld()->GetRealTimeSeconds()+3.;
}
void ASwordFinishWireGameMode::Tick(float Delta)
{
    Super::Tick(Delta);if(!SwordFinishWire::Enabled())return;const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Host)for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(It->IsValid()&&It->Get()->IsLocalController())Host=Cast<AFPSGAMECharacter>(It->Get()->GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Host||!Model||!Model->IsAudit())return;
    if(!Seeded){SwordFinishWire::Network(GetWorld());Model->AdoptNetMirror(SwordFinishWire::Seed(Model,true));SwordFinishWire::Prepare(Host,Model,0,true);Seeded=true;PhaseAt=Now;}
    if(!Guest)
    {
        FString Details;if(NextPhase==0&&SwordFinishWire::Check(Host,0,true,Details))
        {if(Prepared!=0){Prepared=0;UE_LOG(LogTemp,Display,TEXT("SWORD_FINISH_WIRE_HOST_READY"));}}
        if(Now-PhaseAt>240.){Passed=false;Finish();}return;
    }
    if(AwaitingReconnect)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();if(!Pawn||!PS)return;
    if(!GuestModel){GuestModel=Model->CreateShadowModel(SwordFinishWire::Seed(Model,false));if(!GuestModel){Passed=false;Finish();return;}}
    if(Prepared!=NextPhase)
    {
        Prepared=NextPhase;PhaseAt=Now;PS->ShadowModel=GuestModel;Pawn->NetShadowProfile=GuestModel;
        if(NextPhase!=6)SwordFinishWire::Prepare(Host,Model,NextPhase,true);
        // Reconnect reattaches the retained authority profile without replacing its items.
        if(NextPhase==6){GuestModel->AttachPawn(Pawn);Pawn->SetActorTickEnabled(false);Pawn->GetCharacterMovement()->DisableMovement();}
        else SwordFinishWire::Prepare(Pawn,GuestModel,NextPhase,false);
        Guest->Subject=Host;Guest->Phase=NextPhase;Guest->Reported=false;Guest->ForceNetUpdate();
    }
    if(Now-PhaseAt>100.){Passed=false;Finish();}
}
