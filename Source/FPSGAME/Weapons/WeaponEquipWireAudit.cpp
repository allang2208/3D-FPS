#include "WeaponEquipWireAudit.h"
#include "LMGGripReview.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace EquipWire
{
const TCHAR* Guns[]={TEXT("ue_lmg201"),TEXT("ue_pkm_lowpoly"),TEXT("ue_m249")};
void Save(const TArray<TSharedPtr<FJsonValue>>& Rows,bool Passed)
{
    auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),Passed);J->SetArrayField(TEXT("cases"),Rows);
    J->SetStringField(TEXT("scope"),FParse::Param(FCommandLine::Get(),TEXT("M249WristCapture"))
        ?TEXT("Local UDP listen host/client; production profile upload/mirror and body replication; rendered owner viewport and remote body captures. Visual judgement is separate from numeric pass.")
        :TEXT("Local UDP listen host/client; production profile upload/mirror and body replication; native owner POV, no rendering."));
    FString Text;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));
    FString Out;if(FParse::Value(FCommandLine::Get(),TEXT("EquipWireOutput="),Out))FFileHelper::SaveStringToFile(Text,*Out);
    UE_LOG(LogTemp,Display,TEXT("EQUIP_WIRE_RESULT passed=%d cases=%d"),Passed,Rows.Num());
}
void Network(UWorld* World)
{
#if DO_ENABLE_NET_TEST
    if(auto* Driver=World->GetNetDriver())
    {FPacketSimulationSettings S;S.PktLag=80;S.PktLoss=2;Driver->SetPacketSimulationSettings(S);}
#endif
}
}

void AWeaponEquipWireController::Tick(float Dt)
{
    Super::Tick(Dt);
    if(FParse::Param(FCommandLine::Get(),TEXT("M249PartsWire"))){TickM249Parts();return;}
    if(FParse::Param(FCommandLine::Get(),TEXT("M249WristWire"))){TickM249WristVisual();TickM249Wrist(Dt);return;}
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());if(!Subject||!Subject->HasActorBegunPlay())return;
    auto* Body=Subject->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!IsLocalController())
    {
        if(PendingCase<0)return;
        const auto* PS=GetPlayerState<AColdSteelPlayerState>();
        const auto* Item=PS&&PS->ShadowModel?PS->ShadowModel->ActiveFirearm():nullptr;
        const auto State=Body->GetBodyState();
        FTransform Offset;float FOV;Subject->FirstPersonCamera->GetAdditiveOffset(Offset,FOV);
        const bool Synced=Item&&Item->InstanceId==PendingExpected&&State.WeaponInstance==PendingExpected&&State.Action==EFPSBodyAction::None;
        if(!Synced&&Now-PendingAt<8.)return;
        TSharedPtr<FJsonObject> J;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(PendingJson),J);if(!J)J=MakeShared<FJsonObject>();
        const bool OwnerPassed=J->HasField(TEXT("passed"))&&J->GetBoolField(TEXT("passed"));
        const bool LocalOnly=Offset.Equals(FTransform::Identity,.0001f)&&FMath::IsNearlyZero(FOV);
        const bool Passed=OwnerPassed&&Synced&&LocalOnly;
        J->SetBoolField(TEXT("authority_equipment_and_body_settled"),Synced);J->SetBoolField(TEXT("remote_camera_untouched"),LocalOnly);
        J->SetBoolField(TEXT("passed"),Passed);Results.Add(MakeShared<FJsonValueObject>(J));bPassed&=Passed;
        UE_LOG(LogTemp,Display,TEXT("EQUIP_WIRE_SERVER case=%d passed=%d synced=%d local_only=%d"),PendingCase,Passed,Synced,LocalOnly);
        ClientCaseAck(PendingCase,Passed);PendingCase=-1;bFinished=Results.Num()==9;return;
    }
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit()||bWaiting||bFinished)return;
    if(StageAt<0){StageAt=Now;EquipWire::Network(GetWorld());}
    if(Stage==0)
    {
        if(Now-StageAt<3.)return;
        Subject->bMPAutoInputActive=true;Subject->MoveInput=FVector2D::ZeroVector;Subject->bSprintHeld=false;Subject->AimReleased();
        auto S=M->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.Stamina=150;S.bSprintExhausted=false;
        const int32 From=CaseIndex%3,To=(From+1)%3;
        for(int32 Slot=0;Slot<2;++Slot)
        {auto I=M->CreateItem(EquipWire::Guns[Slot?To:From]);I.Place=1;I.Cell=Slot?9:6;I.Magazine=30;S.Items.Add(I);}
        bCasePassed=M->CommitState(S);M->AttachPawn(Subject);ExpectedInstance=Subject->ActiveInventoryWeapon;
        JumpFOV=JumpAngle=JumpPosition=0;UnexpectedEquipment=0;SwitchCount=0;Stage=1;StageAt=Now;return;
    }
    if(Subject->ActiveInventoryWeapon!=ExpectedInstance)++UnexpectedEquipment;
    if(Stage==1&&Now-StageAt>5.)
    {
        const int32 Mode=CaseIndex/3;
        if(Mode==1){Subject->bSprintHeld=true;Subject->MoveInput.Y=1.f;}
        if(Mode==2)Subject->AimPressed();
        Stage=2;StageAt=Now;NextSwitch=Now+1.;return;
    }
    if(Stage==2&&Now>=NextSwitch)
    {
        FMinimalViewInfo Before,After;Subject->CalcCamera(0,Before);
        const FString Old=Subject->ActiveInventoryWeapon;bCasePassed&=M->CycleWeapon();ExpectedInstance=Subject->ActiveInventoryWeapon;
        bCasePassed&=Old!=ExpectedInstance;Subject->RefreshQuickCombatCamera();Subject->CalcCamera(0,After);
        JumpFOV=FMath::Max(JumpFOV,double(FMath::Abs(After.FOV-Before.FOV)));
        JumpAngle=FMath::Max(JumpAngle,FMath::RadiansToDegrees(After.Rotation.Quaternion().AngularDistance(Before.Rotation.Quaternion())));
        JumpPosition=FMath::Max(JumpPosition,FVector::Dist(After.Location,Before.Location));
        if(++SwitchCount<3)NextSwitch=Now+.13;
        else {Subject->MoveInput=FVector2D::ZeroVector;Subject->bSprintHeld=false;Subject->AimReleased();Stage=3;StageAt=Now;}
        return;
    }
    if(Stage==3&&Now-StageAt>4.)
    {
        FTransform Offset;float FOV;Subject->FirstPersonCamera->GetAdditiveOffset(Offset,FOV);
        const bool Settled=Subject->WeaponState==EAKMWeaponState::Idle&&Offset.Equals(FTransform::Identity,.002f)&&FMath::IsNearlyEqual(Subject->FirstPersonCamera->FieldOfView,Subject->BaseLookHorizontalFOV(),.02f);
        const bool Passed=bCasePassed&&UnexpectedEquipment==0&&Settled&&JumpFOV<.01&&JumpAngle<.05&&JumpPosition<.1;
        auto J=MakeShared<FJsonObject>();J->SetNumberField(TEXT("case"),CaseIndex);J->SetBoolField(TEXT("passed"),Passed);
        J->SetStringField(TEXT("owner"),HasAuthority()?TEXT("listen_host"):TEXT("client"));J->SetBoolField(TEXT("settled"),Settled);
        J->SetNumberField(TEXT("unexpected_equipment_frames"),UnexpectedEquipment);J->SetNumberField(TEXT("event_fov_jump_deg"),JumpFOV);
        J->SetNumberField(TEXT("event_angle_jump_deg"),JumpAngle);J->SetNumberField(TEXT("event_position_jump_cm"),JumpPosition);
        UE_LOG(LogTemp,Display,TEXT("EQUIP_WIRE_OWNER case=%d pass=%d settled=%d unexpected=%d jump=%.5f/%.5f/%.5f"),CaseIndex,Passed,Settled,UnexpectedEquipment,JumpFOV,JumpAngle,JumpPosition);
        if(HasAuthority()){Results.Add(MakeShared<FJsonValueObject>(J));bPassed&=Passed;ClientCaseAck_Implementation(CaseIndex,Passed);}
        else
        {
            Results.Add(MakeShared<FJsonValueObject>(J));FString Text;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));
            bWaiting=true;ServerCaseReport(CaseIndex,ExpectedInstance,Text);
        }
    }
}
void AWeaponEquipWireController::ServerCaseReport_Implementation(int32 Case,const FString& Expected,const FString& Json)
{PendingCase=Case;PendingExpected=Expected;PendingJson=Json;PendingAt=GetWorld()->GetRealTimeSeconds();}
void AWeaponEquipWireController::ClientCaseAck_Implementation(int32 Case,bool Accepted)
{
    if(Case!=CaseIndex)return;bPassed&=Accepted;bWaiting=false;
    ++CaseIndex;Stage=0;StageAt=GetWorld()->GetRealTimeSeconds();
    bFinished=CaseIndex==(FParse::Param(FCommandLine::Get(),TEXT("M249WristWire"))
        ?(FParse::Param(FCommandLine::Get(),TEXT("M249WristBaseOnly"))?2:LMGGripReview::Count())
        :FParse::Param(FCommandLine::Get(),TEXT("M249PartsWire"))?3:9);
    if(bFinished&&!HasAuthority())EquipWire::Save(Results,bPassed);
}
void AWeaponEquipWireController::ClientFinish_Implementation(){ExitAt=GetWorld()->GetRealTimeSeconds()+2.;}

AWeaponEquipWireFloor::AWeaponEquipWireFloor()
{
    bReplicates=true;bAlwaysRelevant=true;
    auto* Box=CreateDefaultSubobject<UBoxComponent>(TEXT("FloorCollision"));
    SetRootComponent(Box);Box->SetBoxExtent(FVector(50000,50000,20));Box->SetCollisionProfileName(TEXT("BlockAll"));
}

AWeaponEquipWireGameMode::AWeaponEquipWireGameMode()
{
    PlayerControllerClass=AWeaponEquipWireController::StaticClass();PlayerStateClass=AColdSteelPlayerState::StaticClass();
    DefaultPawnClass=AFPSGAMECharacter::StaticClass();PrimaryActorTick.bCanEverTick=true;
}
void AWeaponEquipWireGameMode::BeginPlay()
{
    Super::BeginPlay();Started=GetWorld()->GetRealTimeSeconds();EquipWire::Network(GetWorld());
    GetWorld()->SpawnActor<AWeaponEquipWireFloor>(FVector(0,0,-20),FRotator::ZeroRotator);
    UE_LOG(LogTemp,Display,TEXT("EQUIP_WIRE_HOST_READY"));
}
void AWeaponEquipWireGameMode::PostLogin(APlayerController* PC)
{
    Super::PostLogin(PC);if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())
    {if(PC->IsLocalController())PS->InitializeHostSession();else PS->InitializeGuest(TEXT("EquipWireAuditGuest"));}
    if(FParse::Param(FCommandLine::Get(),TEXT("M249WristCapture")))
        if(APawn* Pawn=PC->GetPawn())Pawn->SetActorLocation(FVector(0,PC->IsLocalController()?0:500,100));
}
void AWeaponEquipWireGameMode::Tick(float Dt)
{
    Super::Tick(Dt);const double Now=GetWorld()->GetRealTimeSeconds();
    if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    TArray<TSharedPtr<FJsonValue>> Rows;bool Passed=true;int32 Completed=0;
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=Cast<AWeaponEquipWireController>(It->Get())){if(PC->bFinished)++Completed;Passed&=PC->bPassed;Rows.Append(PC->Results);}
    if(Completed>=2||Now-Started>(FParse::Param(FCommandLine::Get(),TEXT("M249WristWire"))?480.:240.))
    {
        EquipWire::Save(Rows,Passed&&Completed>=2);
        for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(auto* PC=Cast<AWeaponEquipWireController>(It->Get());PC&&!PC->IsLocalController())PC->ClientFinish();
        ExitAt=Now+4.;
    }
}
