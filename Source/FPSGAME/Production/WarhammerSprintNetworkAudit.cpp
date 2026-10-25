#include "WarhammerNetworkAuditCommandlet.h"
#include "WarhammerModificationAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/BitReader.h"
#include "Serialization/BitWriter.h"
#include "Serialization/JsonSerializer.h"

int32 UWarhammerNetworkAuditCommandlet::AuditSprint(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_HammerSprint_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("HammerSprintAudit"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("HAMMER_SPRINT_NETWORK %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=100;Seed.bSprintExhausted=false;Seed.SwordUppercutCooldown=Seed.WhirlwindCooldown=0.f;
    for(auto& Entry:Seed.Skills)Entry.Value.Level=1;
    auto Hammer=Host->CreateItem(TEXT("ue_steel_warhammer"));Hammer.Place=1;Hammer.Cell=6;Seed.Items={Hammer};
    auto* Shadow=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->AttachPawn(Pawn);
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;
    auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* FloorActor=World->SpawnActor<AActor>();auto* Floor=NewObject<UBoxComponent>(FloorActor);
    FloorActor->AddInstanceComponent(Floor);FloorActor->SetRootComponent(Floor);
    Floor->SetBoxExtent(FVector(2000,2000,10));Floor->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Floor->SetCollisionObjectType(ECC_WorldStatic);Floor->SetCollisionResponseToAllChannels(ECR_Block);Floor->RegisterComponent();
    const FVector Origin(0,0,10+Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2);
    const float HostStamina=Host->Stamina();
    const auto Reset=[&]()
    {
        Tool->CancelUse();Shadow->AdoptNetMirror(Seed);Health->Health=Health->MaxHealth;
        Tool->Kind=TEXT("warhammer");Tool->EquippedId=Hammer.InstanceId;
        Tool->BluntServerReadyAt=0.;Tool->BluntServerAttackId=Tool->BluntLastServerRequestId=0;
        Pawn->SetActorLocationAndRotation(Origin,FRotator::ZeroRotator);PC->SetControlRotation(FRotator::ZeroRotator);
        Move->SetMovementMode(MOVE_Walking);Move->Velocity=FVector(600,0,0);Move->PendingLaunchVelocity=FVector::ZeroVector;
        Move->FindFloor(Origin,Move->CurrentFloor,false);Move->bWantsToSprint=true;
        Move->LastServerMeleeSequence=Move->ServerHammerAttackId=0;Move->ServerMeleeDistance=0.f;
        Move->ServerMeleeRecoveryUntil=0.;Move->bServerMeleeBlocked=false;Move->bMeleeDashMomentum=false;
        Move->MeleeRequest={};Move->RejectedMeleeSequence=0;
    };
    const auto Ready=[&]() {for(int32 I=0;I<240;++I)Tool->AdvanceBluntSprintReadiness(1.f/60.f);};
    const auto Commit=[&](uint32 Id) {Ready();Tool->ServerBeginBluntAttack_Implementation(Id,false,true);};
    const auto Packet=[](uint32 Sequence,uint32 Id,float Distance,EFPSMeleeMove Kind=EFPSMeleeMove::HammerDash)
    {FFPSNetworkMoveData Data;Data.MeleeRequest.Sequence=Sequence;Data.MeleeRequest.HammerAttackId=Id;
     Data.MeleeRequest.Kind=Kind;Data.MeleeRequest.Direction=FVector::ForwardVector;Data.MeleeRequest.Distance=Distance;return Data;};
    Reset();
    Check(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()&&ColdSteelAuthority::ForPawn(Pawn)==Shadow,TEXT("remote pawn uses its shadow profile"));
    Check(Move->CurrentFloor.IsWalkableFloor(),TEXT("fixture has real walkable collision floor"));
    Ready();
    Check(!Pawn->IsSprinting()&&Tool->BluntSprintSeconds>0.f&&Tool->BluntSprintReadyAt>=0.,TEXT("server readiness uses transmitted sprint intent instead of local key state"));
    Move->bWantsToSprint=false;Tool->AdvanceBluntSprintReadiness(.1f);
    Check(Tool->BluntSprintSeconds==0.f,TEXT("stopping ground sprint clears preparation"));
    Move->bWantsToSprint=true;Ready();Move->SetMovementMode(MOVE_Falling);Move->bWantsToSprint=false;
    Tool->AdvanceBluntSprintReadiness(.1f);
    Check(Tool->BluntSprintSeconds>0.f,TEXT("earned preparation survives airborne intent clearing"));
    Reset();auto Data=Packet(1,101,40.f);Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->LastServerMeleeSequence==0&&Pawn->GetActorLocation().Equals(Origin),TEXT("movement preceding reliable cast remains pending without displacement"));
    Commit(101);const float Spent=Shadow->Stamina();
    Check(Tool->bBluntServerSprintAttack&&Tool->BluntServerAttackId==101&&Spent<100.f,TEXT("remote prepared sprint commits with authority stamina cost"));
    Tool->ServerBeginBluntAttack_Implementation(101,false,true);
    Check(Shadow->Stamina()==Spent&&Tool->bBluntServerSprintAttack,TEXT("duplicate sprint RPC cannot spend twice or cancel pose"));
    Tool->BluntServerSprintStartedAt=World->GetTimeSeconds()-.125;
    Data.MeleeRequest.Direction=FVector::RightVector;Move->ProcessMeleeNetworkMove(Data,true);
    Check(FMath::IsNearlyEqual(Pawn->GetActorLocation().X-Origin.X,40.f,.2f)&&FMath::Abs(Pawn->GetActorLocation().Y-Origin.Y)<.1f,
        TEXT("pending request retries and follows committed server direction"));
    const FVector After=Pawn->GetActorLocation();Move->ProcessMeleeNetworkMove(Data,true);
    Check(Pawn->GetActorLocation().Equals(After,.01f),TEXT("duplicate cumulative move adds no displacement"));
    Data.MeleeRequest.Distance=90.f;Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->ServerMeleeDistance<90.f&&Move->ServerMeleeDistance>40.f,TEXT("server time envelope caps an early cumulative stride"));
    Tool->BluntServerSprintStartedAt=World->GetTimeSeconds()-.26;Data.MeleeRequest.Distance=Tool->BluntSprintLungeDistance;Move->ProcessMeleeNetworkMove(Data,true);
    Check(FMath::IsNearlyEqual(Pawn->GetActorLocation().X-Origin.X,Tool->BluntSprintLungeDistance,.2f),TEXT("later cumulative packet recovers omitted steps once within total budget"));
    Tool->ServerCancelBluntAttack_Implementation(101);Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->bServerMeleeBlocked&&!Tool->bBluntServerSprintAttack,TEXT("cancel retires committed authority movement"));
    Move->bWantsToSprint=true;Move->Velocity=FVector(600,0,0);Commit(102);
    const FVector BeforeOld=Pawn->GetActorLocation();Data=Packet(2,101,40.f);Move->ProcessMeleeNetworkMove(Data,true);
    Check(Pawn->GetActorLocation().Equals(BeforeOld)&&Move->bServerMeleeBlocked,TEXT("old attack cannot borrow a newer committed sprint"));
    Reset();Commit(201);Tool->BluntServerSprintMoveUntil=World->GetTimeSeconds()-.01;Data=Packet(1,201,20.f);Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->bServerMeleeBlocked&&Pawn->GetActorLocation().Equals(Origin),TEXT("expired stride cannot be replayed late"));
    Reset();Commit(251);Tool->BluntServerSprintStartedAt=World->GetTimeSeconds()-.26;
    auto* WallActor=World->SpawnActor<AActor>();auto* Wall=NewObject<UBoxComponent>(WallActor);
    WallActor->AddInstanceComponent(Wall);WallActor->SetRootComponent(Wall);Wall->SetBoxExtent(FVector(10,100,150));
    Wall->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Wall->SetCollisionObjectType(ECC_WorldStatic);
    Wall->SetCollisionResponseToAllChannels(ECR_Block);Wall->RegisterComponent();Wall->SetWorldLocation(FVector(90,0,150));
    Data=Packet(1,251,Tool->BluntSprintLungeDistance);Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->bServerMeleeBlocked&&Pawn->GetActorLocation().X<80.f-Pawn->GetCapsuleComponent()->GetScaledCapsuleRadius()+.5f,
        TEXT("authority capsule sweep stops stride at wall without tunnelling"));
    WallActor->Destroy();
    Reset();Commit(301);Move->SetMovementMode(MOVE_Falling);Move->Velocity=FVector(500,0,-120);
    Data=Packet(1,301,0.f,EFPSMeleeMove::HammerAirMomentum);Data.MeleeRequest.Momentum=FVector(2000,0,0);
    Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->HasMeleeDashMomentum()&&Move->Velocity.Size2D()<=501.f&&Move->Velocity.Z==-120.f&&Move->ServerMeleeDistance==0.f,
        TEXT("air carry keeps gravity and clamps to server earned speed without fixed stride"));
    Tool->CancelUse();
    Check(!Move->HasMeleeDashMomentum()&&Move->bServerMeleeBlocked,TEXT("remote equipment cancellation retires server attack identity"));
    Reset();Commit(401);Data=Packet(1,401,1.f,EFPSMeleeMove::HammerAirMomentum);Data.MeleeRequest.Momentum=FVector(500,0,0);
    Move->ProcessMeleeNetworkMove(Data,true);
    Check(Move->bServerMeleeBlocked&&!Move->HasMeleeDashMomentum(),TEXT("ground cannot request air carry or add fixed distance to it"));
    Reset();Commit(501);Health->Health=0.f;Tool->TickAuthorityBluntCharge();
    Check(!Tool->bBluntServerSprintAttack,TEXT("death interrupts server sprint before contact"));
    Reset();Commit(601);auto Unequipped=Seed;Unequipped.Items.Reset();Shadow->AdoptNetMirror(Unequipped);Tool->TickAuthorityBluntCharge();
    Check(!Tool->bBluntServerSprintAttack,TEXT("weapon removal interrupts server sprint before contact"));
    Reset();Move->MeleeRequest=Packet(77,701,0.f,EFPSMeleeMove::HammerAirMomentum).MeleeRequest;
    Move->RestoreMeleeDashMomentum(true);Tool->Elapsed=-1.f;
    Tool->ClientBluntAttackResult_Implementation(701,0,false,false,false,false);
    Check(Move->IsMeleeMoveRejected(77)&&!Move->HasMeleeDashMomentum(),TEXT("late rejection retires movement even after pose end"));
    FSavedMove_FPSCharacter Saved;Saved.MeleeRequest=Move->MeleeRequest;Saved.bSavedMeleeMomentum=true;Saved.PrepMoveFor(Pawn);
    Check(!Move->HasMeleeDashMomentum(),TEXT("saved move replay cannot revive rejected momentum"));
    for(const auto Kind:{EFPSMeleeMove::HammerDash,EFPSMeleeMove::HammerAirMomentum,EFPSMeleeMove::Dash,EFPSMeleeMove::AirMomentum})
    {
        auto Sent=Packet(42,IsHammerSprintMove(Kind)?123456u:0u,IsMeleeMomentumMove(Kind)?0.f:42.5f,Kind);
        Sent.MeleeRequest.Momentum=FVector(567.8,12.3,0);FBitWriter Writer(4096,true);
        const bool Wrote=Sent.Serialize(*Move,Writer,nullptr,FCharacterNetworkMoveData::ENetworkMoveType::NewMove);
        FFPSNetworkMoveData Read;FBitReader Reader(Writer.GetData(),Writer.GetNumBits());
        const bool ReadOK=Read.Serialize(*Move,Reader,nullptr,FCharacterNetworkMoveData::ENetworkMoveType::NewMove);
        const bool OK=Wrote&&ReadOK&&Read.MeleeRequest.Sequence==42&&Read.MeleeRequest.Kind==Kind&&
            Read.MeleeRequest.HammerAttackId==Sent.MeleeRequest.HammerAttackId&&Read.MeleeRequest.Distance==Sent.MeleeRequest.Distance&&
            (!IsMeleeMomentumMove(Kind)||FVector(Read.MeleeRequest.Momentum).Equals(FVector(Sent.MeleeRequest.Momentum),.11f));
        Check(OK,*FString::Printf(TEXT("native packed movement serialization kind %d"),int32(Kind)));
    }
    Check(Host->Stamina()==HostStamina,TEXT("guest sprint and cancellations leave host stamina unchanged"));
    Tool->CancelUse();auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);
    Report->SetNumberField(TEXT("count"),Rows.Num());Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetBoolField(TEXT("authority_runtime_executed"),true);Report->SetBoolField(TEXT("native_movement_serialization_tested"),true);
    Report->SetBoolField(TEXT("real_network_transport_tested"),false);Report->SetBoolField(TEXT("user_profile_modified"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("WarhammerSprintNetworkAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
