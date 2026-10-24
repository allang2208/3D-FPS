#include "ApartmentNetworkAudit.h"
#include "ApartmentDeviceControl.h"
#include "ColdSteelSlidingDoor.h"
#include "../UI/ColdSteelSceneContainer.h"
#include "../UI/ColdSteelContainerSearchSubsystem.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../FPSGAMECharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DefaultPawn.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "Net/UnrealNetwork.h"

namespace ApartmentAudit
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("ApartmentNetworkAudit"));}
void RestState(AFPSGAMECharacter* Pawn,uint8 Phase)
{
    auto* Rest=Pawn->FindComponentByClass<UFPSFurnitureRestComponent>();
    auto* Property=FindFProperty<FStructProperty>(Rest->GetClass(),TEXT("State"));
    auto* State=Property->ContainerPtrToValuePtr<FFurnitureRestState>(Rest);
    State->Phase=Phase;State->Kind=TEXT("ApartmentBed");State->Started=Pawn->GetWorld()->GetTimeSeconds();
    State->Root=FTransform(FRotator::ZeroRotator,FVector(1600,0,0));State->Exit=FVector(1800,0,90);
    Rest->ProcessEvent(Rest->FindFunctionChecked(TEXT("OnRep_State")),nullptr);
    Pawn->SetActorLocation(Phase?State->Root.GetLocation()+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()):State->Exit);
    // Fixture has no interactive furniture owner. Only the client continuation is sampled.
    Rest->SetComponentTickEnabled(false);Pawn->ForceNetUpdate();
}
void NearContainer(APlayerController* PC,AColdSteelSceneContainer* Cabinet)
{if(PC&&PC->GetPawn())PC->GetPawn()->SetActorLocation(Cabinet->GetActorLocation()+FVector(-100,0,70));}
}
void AApartmentAuditController::ClientStage_Implementation(int32 Stage,AColdSteelSceneContainer* C,AColdSteelSlidingDoor* D,AApartmentDeviceControl* P,AFPSGAMECharacter* R)
{if(C)Cabinet=C;if(D)Door=D;if(P)Device=P;if(R)RestPawn=R;Current=Stage;Started=GetWorld()->GetRealTimeSeconds();Sent=Reported=false;
 UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_CLIENT_STAGE %d cabinet=%s door=%s device=%s rest=%s"),Stage,*GetNameSafe(C),*GetNameSafe(D),*GetNameSafe(P),*GetNameSafe(R));}
void AApartmentAuditController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AApartmentAuditController,Cabinet);DOREPLIFETIME(AApartmentAuditController,Door);DOREPLIFETIME(AApartmentAuditController,Device);DOREPLIFETIME(AApartmentAuditController,RestPawn);}
void AApartmentAuditController::ServerExercise_Implementation(int32 Stage)
{if(ApartmentAudit::Enabled()&&Stage==Expected)if(auto* GM=GetWorld()->GetAuthGameMode<AApartmentNetworkAuditGameMode>())GM->Exercise(this,Stage);}
void AApartmentAuditController::ServerReport_Implementation(int32 Stage,const FString& Json)
{if(ApartmentAudit::Enabled()&&Stage==Expected)if(auto* GM=GetWorld()->GetAuthGameMode<AApartmentNetworkAuditGameMode>())GM->Receive(this,Stage,Json);}
void AApartmentAuditController::ClientExit_Implementation(){if(ApartmentAudit::Enabled())FPlatformMisc::RequestExit(false);}
void AApartmentAuditController::Tick(float Delta)
{
    Super::Tick(Delta);
    if(!ApartmentAudit::Enabled()||HasAuthority()||Current<0||Reported||!GetPawn()||!GetPlayerState<AColdSteelPlayerState>()||!Cabinet||!Door||!Device||!RestPawn)return;
    if(!Sent)
    {
        Sent=true;Started=GetWorld()->GetRealTimeSeconds();
        UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_CLIENT_READY %d"),Current);
        if(Current==0||Current==3)ServerExercise(Current);
        if(Current==1)if(auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>())Search->CloseLocal(this,Cabinet);
    }
    if(GetWorld()->GetRealTimeSeconds()-Started<2.5)return;
    const auto* Rest=RestPawn->FindComponentByClass<UFPSFurnitureRestComponent>();
    const bool Closed=Current==2||Current==5;
    auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("stage"),Current);
    const float Fraction=Cabinet->GetDoorOpenFraction();
    const bool Pose=Rest&&(Current==5?!Rest->IsResting()&&!Rest->IsComponentTickEnabled():Rest->IsResting()&&Rest->IsComponentTickEnabled()&&!RestPawn->bUseControllerRotationYaw);
    const bool Open=Closed?Fraction<.01f:Fraction>.99f;
    Row->SetNumberField(TEXT("cabinet_fraction"),Fraction);Row->SetBoolField(TEXT("cabinet_expected"),Open);
    Row->SetBoolField(TEXT("rest_initialization"),Pose);Row->SetBoolField(TEXT("door_open"),Door->IsDoorOpen());
    Row->SetBoolField(TEXT("device_power"),Device->IsPowered());Row->SetNumberField(TEXT("device_seconds"),Device->GetPoweredSeconds());
    const auto* GS=GetWorld()->GetGameState();Row->SetNumberField(TEXT("server_clock"),GS?GS->GetServerWorldTimeSeconds():0.);
    Row->SetBoolField(TEXT("passed"),Open&&Pose&&Door->IsDoorOpen()&&Device->IsPowered()&&Device->GetPoweredSeconds()>1.f);
    FString Json;FJsonSerializer::Serialize(Row,TJsonWriterFactory<>::Create(&Json));ServerReport(Current,Json);Reported=true;
}
AApartmentNetworkAuditGameMode::AApartmentNetworkAuditGameMode()
{PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AApartmentAuditController::StaticClass();PlayerStateClass=AApartmentAuditPlayerState::StaticClass();DefaultPawnClass=ADefaultPawn::StaticClass();}
void AApartmentNetworkAuditGameMode::BeginPlay()
{
    Super::BeginPlay();if(!ApartmentAudit::Enabled())return;
    auto* W=GetWorld();
    Cabinet=W->SpawnActorDeferred<AColdSteelSceneContainer>(AColdSteelSceneContainer::StaticClass(),FTransform(FVector(300,0,0)));
    Cabinet->Tags.Add(TEXT("ColdSteel.SceneContainer.Reclosable"));Cabinet->ContainerId=TEXT("IsolatedApartmentCabinet");Cabinet->bAlwaysRelevant=true;
    UGameplayStatics::FinishSpawningActor(Cabinet,FTransform(FVector(300,0,0)));
    Door=W->SpawnActorDeferred<AColdSteelSlidingDoor>(AColdSteelSlidingDoor::StaticClass(),FTransform(FVector(1000,0,0)));
    FindFProperty<FFloatProperty>(Door->GetClass(),TEXT("AutoCloseSeconds"))->SetPropertyValue_InContainer(Door,0.f);Door->bAlwaysRelevant=true;
    UGameplayStatics::FinishSpawningActor(Door,FTransform(FVector(1000,0,0)));
    Device=W->SpawnActor<AApartmentDeviceControl>(FVector(120,-500,0),FRotator::ZeroRotator);Device->bAlwaysRelevant=true;
    RestPawn=W->SpawnActor<AFPSGAMECharacter>(FVector(1600,0,90),FRotator::ZeroRotator);RestPawn->bAlwaysRelevant=true;RestPawn->SetActorTickEnabled(false);
    RestPawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);ApartmentAudit::RestState(RestPawn,3);
    UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_HOST_READY"));
}
void AApartmentNetworkAuditGameMode::PostLogin(APlayerController* Player)
{
    Super::PostLogin(Player);if(!ApartmentAudit::Enabled()||Player->IsLocalController())return;
    auto* PC=CastChecked<AApartmentAuditController>(Player);
    if(++Guests==1){First=PC;Stage(PC,0);}else {Late=PC;Stage(PC,4);}
}
void AApartmentNetworkAuditGameMode::Stage(AApartmentAuditController* Player,int32 Value)
{Player->Expected=Value;Player->Cabinet=Cabinet;Player->Door=Door;Player->Device=Device;Player->RestPawn=RestPawn;Player->ForceNetUpdate();Player->ClientStage(Value,Cabinet,Door,Device,RestPawn);
 UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_DISPATCH %d"),Value);}
void AApartmentNetworkAuditGameMode::Exercise(AApartmentAuditController* Player,int32 Value)
{
    if(Value==0)
    {
        Player->GetPawn()->SetActorLocation(FVector(0,-500,0));Player->SetControlRotation(FRotator::ZeroRotator);
        FVector Eye;FRotator Aim;Player->GetPlayerViewPoint(Eye,Aim);Device->SetActorLocation(Eye+Aim.Vector()*120.f);
        const bool Powered=Device->ToggleFrom(Player),Opened=Door->OpenDoorFrom(Player->GetPawn());Passed&=Powered&&Opened;
        Player->GetPawn()->SetActorLocation(FVector(-2000,-500,0));const bool RejectFar=!Device->ToggleFrom(Player);Passed&=RejectFar;
        UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_AUTHORITY device=%d door=%d reject_far=%d"),Powered,Opened,RejectFar);
    }
    ApartmentAudit::NearContainer(Player,Cabinet);
    if(auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>())Search->Begin(Player,Cabinet);
    Cabinet->OpenSharedVisual();
}
void AApartmentNetworkAuditGameMode::Receive(AApartmentAuditController* Player,int32 Value,const FString& Json)
{
    TSharedPtr<FJsonObject> Row;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Row)||!Row){Passed=false;return;}
    Passed&=Row->GetBoolField(TEXT("passed"));Results.Add(MakeShared<FJsonValueObject>(Row));
    auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>();auto* Host=UGameplayStatics::GetPlayerController(this,0);
    UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_STAGE %d pass=%d"),Value,Row->GetBoolField(TEXT("passed")));
    if(Value==0){ApartmentAudit::NearContainer(Host,Cabinet);Search->Begin(Host,Cabinet);Stage(Player,1);}
    else if(Value==1){Passed&=!Search->IsActive(Player,Cabinet)&&Search->IsActive(Host,Cabinet);Search->Close(Host,Cabinet);Stage(Player,2);}
    else if(Value==2)Stage(Player,3);
    else if(Value==3){Player->Expected=INDEX_NONE;UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_LATE_JOIN_READY"));}
    else if(Value==4){ApartmentAudit::RestState(RestPawn,0);First->ClientExit();WaitingForDisconnect=true;}
    else if(Value==5)
    {
        Passed&=!Search->HasViewers(Cabinet);auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Passed);Report->SetArrayField(TEXT("cases"),Results);
        Report->SetStringField(TEXT("scope"),TEXT("isolated real UDP replication, cabinet viewer lifecycle, late join, device clock and idle-door persistence; no inventory transactions or rendered acceptance"));
        FString Output;FParse::Value(FCommandLine::Get(),TEXT("ApartmentAuditOutput="),Output);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Text,*Output);
        Player->ClientExit();ExitAt=GetWorld()->GetRealTimeSeconds()+2.;UE_LOG(LogTemp,Display,TEXT("APARTMENT_NET_RESULT pass=%d"),Passed);
    }
}
void AApartmentNetworkAuditGameMode::Tick(float Delta)
{Super::Tick(Delta);
 if(WaitingForDisconnect&&!IsValid(First)){WaitingForDisconnect=false;Stage(Late,5);}
 if(ExitAt>=0&&GetWorld()->GetRealTimeSeconds()>=ExitAt)FPlatformMisc::RequestExit(false);}
