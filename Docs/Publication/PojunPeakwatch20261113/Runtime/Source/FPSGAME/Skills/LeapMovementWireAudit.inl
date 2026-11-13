// Opt-in socket test. Both peers retain production CMC, skill and camera ticks.
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerShockwave.h"
#include "../Production/WarhammerCombat.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "LeapStrikeMotion.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/NetDriver.h"
#include "Serialization/JsonSerializer.h"

namespace LeapWire
{
bool TestingSlam(){return FParse::Param(FCommandLine::Get(),TEXT("ChargedSlamWire"));}
constexpr int32 StaleWeaponCase=7,Count=8;
const TCHAR* Names[]={TEXT("flat"),TEXT("wall_after_commit"),TEXT("roof_30m"),TEXT("roof_200m"),
    TEXT("platform_removed"),TEXT("cancel_descent"),TEXT("cancel_pending"),TEXT("stale_weapon_instance")};
struct FRun
{
    int32 Case=-1,Waves=0;double At=0,ActionAt=-1,DoneAt=-1,LogAt=-1;
    bool Started=false,Air=false,Changed=false,Cancelled=false,Done=false,Pass=true,Finite=true;
    bool PrematureEnd=false;
    float MaxEyeDistance=0,MaxResidual=0;FVector Previous=FVector::ZeroVector,PreviousVelocity=FVector::ZeroVector;
    TArray<TWeakObjectPtr<AActor>> Geometry;TWeakObjectPtr<AActor> Platform;
    TArray<TSharedPtr<FJsonValue>> Rows,Frames;FDelegateHandle SpawnHandle,ObserveHandle;
    TWeakObjectPtr<AFPSGAMECharacter> Player;
    TWeakObjectPtr<ALeapStrikeShockwave> SlamWave;
    float SlamRadius=0.f;
    bool SawImpactSound=false;
} Client,Host;
void TrackWave(FRun& R,AActor* Actor)
{
    if(auto* Wave=Cast<ALeapStrikeShockwave>(Actor))
    {++R.Waves;R.SlamWave=Wave;}
}
void SampleSlam(FRun& R)
{
    if(auto* Wave=R.SlamWave.Get())
    {
        const auto* Radius=FindFProperty<FFloatProperty>(Wave->GetClass(),TEXT("MaxRadius"));
        const auto* Impact=FindFProperty<FObjectPropertyBase>(Wave->GetClass(),TEXT("ImpactSound"));
        if(Radius)R.SlamRadius=Radius->GetPropertyValue_InContainer(Wave);
        const UObject* Sound=Impact?Impact->GetObjectPropertyValue_InContainer(Wave):nullptr;
        R.SawImpactSound|=Sound&&Sound->GetFName()==TEXT("S_Warhammer_GroundImpact");
    }
}
bool RecordSlam(FRun& R,AFPSGAMECharacter* P,bool PeerOK)
{
    const auto* Model=ColdSteelAuthority::ForPawn(P);
    const auto* Item=Model?Model->ActiveProductionTool():nullptr;
    const float Expected=Item?WarhammerCombat::ShockwaveRadius(*Item,Model):0.f;
    const bool Passed=PeerOK&&Expected>0.f&&R.Waves==1&&FMath::IsNearlyEqual(Expected,R.SlamRadius)&&R.SawImpactSound;
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("case"),TEXT("charged_ground_slam"));
    J->SetBoolField(TEXT("passed"),Passed);J->SetNumberField(TEXT("waves"),R.Waves);
    J->SetNumberField(TEXT("radius_cm"),R.SlamRadius);J->SetNumberField(TEXT("expected_radius_cm"),Expected);
    J->SetBoolField(TEXT("hammer_ground_sound"),R.SawImpactSound);R.Rows.Add(MakeShared<FJsonValueObject>(J));R.Pass=Passed;
    return Passed;
}
float Height(int32 C){return C==3?20000.f:C>=2&&C<=5?3000.f:0.f;}
FColdSteelProfile Seed(UColdSteelStatusModel* M)
{
    auto S=M->Snapshot();S.Items.Reset();S.ActiveWeaponSlot=6;S.ActiveProductionTool.Reset();S.DungeonRun={};
    auto I=SkillWireEquipment::MakeWeapon(M,TEXT("ue_steel_warhammer"));I.InstanceId=TEXT("LeapMovementWireHammer");I.Place=1;I.Cell=6;S.Items.Add(I);
    S.Stamina=150;S.bSprintExhausted=false;S.StaminaRecoveryDelay=0;S.UppercutStaminaSpent=0;
    S.LeapStrikeCooldown=S.LeapStrikeCooldownDuration=0;S.Skills.FindOrAdd(TEXT("leapStrike")).Level=1;return S;
}
void Save(const FRun& R,const TCHAR* Role,bool Complete)
{
    auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),Complete&&R.Pass);J->SetBoolField(TEXT("complete"),Complete);
    J->SetStringField(TEXT("role"),Role);J->SetArrayField(TEXT("cases"),R.Rows);J->SetArrayField(TEXT("frames"),R.Frames);
    FString Path,Text;FParse::Value(FCommandLine::Get(),TEXT("SkillWireOutput="),Path);
    FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);
}
AActor* Box(UWorld* W,FRun& R,FVector P,FVector Extent)
{
    auto* A=W->SpawnActor<AActor>();auto* B=NewObject<UBoxComponent>(A);A->SetRootComponent(B);A->AddInstanceComponent(B);
    B->SetBoxExtent(Extent);B->SetCollisionProfileName(TEXT("BlockAll"));B->RegisterComponent();A->SetActorLocation(P);
    B->SetMobility(EComponentMobility::Static);R.Geometry.Add(A);return A;
}
void Prepare(UWorld* W,FRun& R,int32 C,AFPSGAMECharacter* P,bool Owner)
{
    for(auto A:R.Geometry)if(A.IsValid())A->Destroy();R.Geometry.Reset();R.Platform.Reset();
    R.Player=P;R.Case=C;R.At=W->GetRealTimeSeconds();R.ActionAt=R.DoneAt=-1;R.Started=R.Air=R.Changed=R.Cancelled=R.Done=false;
    R.Finite=true;R.PrematureEnd=false;R.PreviousVelocity=FVector::ZeroVector;R.Waves=0;R.MaxEyeDistance=R.MaxResidual=0;
    if(Owner)Box(W,R,FVector(0,0,-20),FVector(5000,5000,20));
    const float Z=Height(C);
    if(Z>0)Box(W,R,FVector(-455,0,Z-20),FVector(500,1500,20));
    if(C==4)R.Platform=Box(W,R,FVector(800,0,Z-20),FVector(180,1500,20));
    auto* Move=P->GetCharacterMovement();Move->StopMovementImmediately();
    P->SetActorLocation(FVector(0,0,Z+P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.4f),false,nullptr,ETeleportType::TeleportPhysics);
    Move->SetMovementMode(MOVE_Walking);R.Previous=P->GetActorLocation();
    P->bMPAutoInputActive=true;
#if DO_ENABLE_NET_TEST
    if(auto* D=W->GetNetDriver())UE_LOG(LogTemp,Display,TEXT("LEAP_WIRE_NETWORK case=%d lag=%d loss=%d"),C,D->PacketSimulationSettings.PktLag,D->PacketSimulationSettings.PktLoss);
#endif
}
void Observe(UWorld* W,FRun& R,AFPSGAMECharacter* P,float Delta,bool Owner)
{
    auto* T=P->FindComponentByClass<UProductionToolComponent>();auto* Move=P->GetCharacterMovement();
    if(T->IsLeapStrikeActive()&&R.ActionAt<0)R.ActionAt=W->GetRealTimeSeconds();
    if(R.ActionAt<0)return;
    R.Air|=Move->IsFalling();
    if(!R.Changed&&T->IsLeapStrikeActive()&&T->GetLeapStrikeAge()>.3f)
    {
        if(R.Case==1){Box(W,R,FVector(220,0,700),FVector(15,1000,700));R.Changed=true;}
        if(R.Case==4&&Move->IsFalling()&&P->GetActorLocation().X>100)
        {if(R.Platform.IsValid())R.Platform->Destroy();R.Changed=true;}
    }
    const FVector Position=P->GetActorLocation(),Eye=P->FirstPersonCamera->GetComponentLocation();
    R.Finite&=!Position.ContainsNaN()&&!Move->Velocity.ContainsNaN()&&!Eye.ContainsNaN();
    R.MaxEyeDistance=FMath::Max(R.MaxEyeDistance,float(FVector::Dist2D(Eye,Position)));
    // This runs after all movement/replay in the frame, with that frame's dt.
    // Controller Tick runs before CMC and can see a correction before its replay.
    const double Allowed=FMath::Max(R.PreviousVelocity.Size(),Move->Velocity.Size())*Delta+FMath::Abs(Move->GetGravityZ())*Delta*Delta;
    R.MaxResidual=FMath::Max(R.MaxResidual,float(FVector::Dist(Position,R.Previous)-Allowed));R.Previous=Position;R.PreviousVelocity=Move->Velocity;
    R.PrematureEnd|=R.Case<5&&R.Air&&!T->IsLeapStrikeActive()&&Move->IsFalling();
    auto F=MakeShared<FJsonObject>();F->SetNumberField(TEXT("case"),R.Case);F->SetNumberField(TEXT("time"),W->GetTimeSeconds());
    F->SetNumberField(TEXT("x"),Position.X);F->SetNumberField(TEXT("z"),Position.Z);F->SetNumberField(TEXT("vx"),Move->Velocity.X);F->SetNumberField(TEXT("vz"),Move->Velocity.Z);
    F->SetNumberField(TEXT("age"),T->GetLeapStrikeAge());F->SetBoolField(TEXT("active"),T->IsLeapStrikeActive());F->SetBoolField(TEXT("grounded"),Move->IsMovingOnGround());
    F->SetBoolField(TEXT("rms"),Move->GetRootMotionSource(LeapStrike::MotionName).IsValid());
    if(const auto* Body=P->FindComponentByClass<UFPSPlayerBodyComponent>())
    {const auto State=Body->GetBodyState();F->SetStringField(TEXT("body_variant"),State.ActionVariant.ToString());F->SetNumberField(TEXT("body_rate"),State.ActionProgressRate);}
    R.Frames.Add(MakeShared<FJsonValueObject>(F));
}
bool Result(FRun& R,AFPSGAMECharacter* P,bool Owner,bool PeerPassed=true)
{
    const auto* T=P->FindComponentByClass<UProductionToolComponent>();auto* Move=P->GetCharacterMovement();
    const int32 Expected=R.Case>=5?0:1;
    const auto* Model=ColdSteelAuthority::ForPawn(P);
    const bool CastOK=R.Case==StaleWeaponCase
        ? (R.Started==Owner&&Model&&Model->Snapshot().UppercutStaminaSpent==0&&Model->LeapStrikeCooldown()==0)
        : R.Started;
    const bool Passed=CastOK&&R.Finite&&!T->IsLeapStrikeActive()&&Move->IsMovingOnGround()
        &&!Move->GetRootMotionSource(LeapStrike::MotionName)&&R.Air==(R.Case<6)&&PeerPassed&&R.Waves==Expected
        &&(!Owner||(R.MaxEyeDistance<85.f&&R.MaxResidual<30.f&&!R.PrematureEnd));
    auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("case"),Names[R.Case]);J->SetBoolField(TEXT("passed"),Passed);
    J->SetBoolField(TEXT("started"),R.Started);J->SetBoolField(TEXT("airborne"),R.Air);J->SetBoolField(TEXT("active"),T->IsLeapStrikeActive());
    J->SetNumberField(TEXT("waves"),R.Waves);J->SetNumberField(TEXT("landing_x"),P->GetActorLocation().X);J->SetNumberField(TEXT("landing_z"),P->GetActorLocation().Z);
    J->SetNumberField(TEXT("max_eye_offset_xy"),R.MaxEyeDistance);J->SetNumberField(TEXT("max_motion_residual_cm"),R.MaxResidual);
    J->SetBoolField(TEXT("premature_end_in_air"),R.PrematureEnd);
    R.Rows.Add(MakeShared<FJsonValueObject>(J));R.Pass&=Passed;
    UE_LOG(LogTemp,Display,TEXT("LEAP_WIRE_CASE %s case=%d owner=%d waves=%d air=%d active=%d pos=%s residual=%.2f"),
        Passed?TEXT("PASS"):TEXT("FAIL"),R.Case,Owner,R.Waves,R.Air,T->IsLeapStrikeActive(),*P->GetActorLocation().ToCompactString(),R.MaxResidual);
    return Passed;
}
void ObserveAfterMovement(UWorld* World,FRun& R,bool Owner)
{
    if(R.ObserveHandle.IsValid())return;
    const TWeakObjectPtr<UWorld> Expected(World);
    R.ObserveHandle=FWorldDelegates::OnWorldPostActorTick.AddLambda([Expected,&R,Owner](UWorld* W,ELevelTick,float Delta)
    {if(W==Expected.Get()&&!R.Done&&R.Player.IsValid())Observe(W,R,R.Player.Get(),Delta,Owner);});
}
}

void ASkillWireAuditController::SetupLeapWire(int32 Case)
{
    using namespace LeapWire;
    if(HasAuthority()||Case==Client.Case||Case>=Count)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    auto* PS=GetPlayerState<AColdSteelPlayerState>();if(!P||!M||!M->IsAudit()||!PS||PS->GetPawn()!=P)return;
    if(Client.Case>=0&&!Client.Done)return;
    P->FindComponentByClass<UProductionToolComponent>()->CancelUse();
    auto Equipment=Seed(M);
    if(Case==StaleWeaponCase)Equipment.Items[0].InstanceId=TEXT("LeapMovementWirePreviousWeapon");
    M->Current=MoveTemp(Equipment);M->CurrentPawn=P;PS->SetActorTickEnabled(false);bShowMouseCursor=false;SetViewTarget(P);
    if(!Client.SpawnHandle.IsValid())
        Client.SpawnHandle=GetWorld()->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([](AActor* A)
        {TrackWave(Client,A);}));
    P->ApplyColdSteelProfile(M);P->FindComponentByClass<UProductionToolComponent>()->RefreshHeldTool();
    Prepare(GetWorld(),Client,Case,P,true);ObserveAfterMovement(GetWorld(),Client,true);P->FirstPersonCamera->Activate(true);
}
void ASkillWireAuditController::TickLeapWire(float Delta)
{
    using namespace LeapWire;if(HasAuthority()||!IsLocalController()||Client.Case<0)return;
    auto* P=Cast<AFPSGAMECharacter>(GetPawn());if(!P)return;auto* T=P->FindComponentByClass<UProductionToolComponent>();
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(TestingSlam())
    {
        if(Client.Done){if(Now-Client.DoneAt>4.)FPlatformMisc::RequestExit(false);return;}
        SampleSlam(Client);
        if(!Client.Started&&Now-Client.At>3.){T->BeginPrimaryAttack();Client.Started=T->IsHeavyCharging();}
        if(Client.Started&&!Client.Changed&&T->HeavyChargeFraction()>=1.f)
        {T->ReleasePrimaryAttack();Client.Changed=true;Client.ActionAt=Now;}
        if((Client.Changed&&Now-Client.ActionAt>4.)||Now-Client.At>24.)
        {
            Client.Done=true;Client.DoneAt=Now;
            const bool Passed=RecordSlam(Client,P,Client.Changed);Save(Client,TEXT("client"),true);
            ServerResult(Passed,true,true,true,true);
        }
        return;
    }
    if(Client.Done){if(Client.Case==Count-1&&Now-Client.DoneAt>4)FPlatformMisc::RequestExit(false);return;}
    if(!Client.Started)
    {
        const FVector Goal(800,0,Client.Case==4?Height(Client.Case):0);
        const FRotator Aim=(Goal-P->GetMeleeAimTransform().GetLocation()).Rotation();SetControlRotation(Aim);P->FirstPersonCamera->SetWorldRotation(Aim);
        if(Now-Client.At>3&&Now-Client.LogAt>5)
        {Client.LogAt=Now;UE_LOG(LogTemp,Display,TEXT("LEAP_WIRE_READY case=%d status=%s position=%s"),Client.Case,*T->LeapStrikeStatusText(false),*P->GetActorLocation().ToCompactString());}
        if(Now-Client.At>3&&T->LeapStrikeStatusText(false).IsEmpty())
        {
            Client.Started=T->BeginLeapStrike();
            if(Client.Started&&Client.Case==6){Client.ActionAt=Now;T->CancelUse();Client.Cancelled=true;}
        }
    }
    if(Client.Case==5&&!Client.Cancelled&&Client.Air&&P->GetVelocity().Z<-100)
    {T->CancelUse();Client.Cancelled=true;}
    const bool Finished=Client.Started&&Client.ActionAt>=0&&!T->IsLeapStrikeActive()&&P->GetCharacterMovement()->IsMovingOnGround()&&Now-Client.ActionAt>1.;
    if(Finished||Now-Client.At>100)
    {
        Client.Done=true;Client.DoneAt=Now;const bool Pass=Result(Client,P,true);Save(Client,TEXT("client"),Client.Case==Count-1);
        if(Client.Case==Count-1)
        {
            GetWorld()->RemoveOnActorSpawnedHandler(Client.SpawnHandle);
            FWorldDelegates::OnWorldPostActorTick.Remove(Client.ObserveHandle);
        }
        ServerResult(Pass,true,true,true,true);
    }
}
void ASkillWireAuditGameMode::TickLeapWire(float Delta)
{
    using namespace LeapWire;
    const double Now=GetWorld()->GetRealTimeSeconds();if(ExitAt>=0){if(Now>=ExitAt)FPlatformMisc::RequestExit(false);return;}
    if(!Guest)return;auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();
    if(!P||!PS)return;
    if(!GuestModel)
    {
        auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
        GuestModel=M->CreateShadowModel(Seed(M));PS->ShadowModel=GuestModel;GuestModel->CurrentPawn=P;P->NetShadowProfile=GuestModel;
        P->ApplyColdSteelProfile(GuestModel);P->FindComponentByClass<UProductionToolComponent>()->RefreshHeldTool();
        PS->SetActorTickEnabled(false);
        for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(auto* PC=It->Get();PC&&PC->IsLocalController()&&PC->GetPawn()&&PC->GetPawn()!=P)
                PC->GetPawn()->SetActorLocation(FVector(0,3000,100));
        Host.SpawnHandle=GetWorld()->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateLambda([](AActor* A)
        {TrackWave(Host,A);}));
        Prepare(GetWorld(),Host,0,P,false);ObserveAfterMovement(GetWorld(),Host,false);P->ForceNetUpdate();
    }
    if(!Host.Started&&Now-LastSetup>1){LastSetup=Now;Guest->ClientSetupConversation(Host.Case,nullptr,nullptr,nullptr);}
    if(TestingSlam())
    {
        SampleSlam(Host);
        if(Guest->bReported||Now-Host.At>60.)
        {
            RecordSlam(Host,P,Guest->bReported&&Guest->bPassed);Save(Host,TEXT("authority"),true);ExitAt=Now+3.;
        }
        return;
    }
    auto* T=P->FindComponentByClass<UProductionToolComponent>();Host.Started|=T->IsLeapStrikeActive()||GuestModel->Snapshot().UppercutStaminaSpent>0;
    if(Guest->bReported||Now-Host.At>120)
    {
        if(Host.DoneAt<0)Host.DoneAt=Now;
        if(Now-Host.DoneAt<1.)return;
        Result(Host,P,false,Guest->bReported&&Guest->bPassed);Save(Host,TEXT("authority"),Host.Case==Count-1);
        if(Host.Case==Count-1){GetWorld()->RemoveOnActorSpawnedHandler(Host.SpawnHandle);FWorldDelegates::OnWorldPostActorTick.Remove(Host.ObserveHandle);ExitAt=Now+3;return;}
        Guest->bReported=Guest->bPassed=false;T->CancelUse();GuestModel->Current=Seed(GuestModel);
        P->ApplyColdSteelProfile(GuestModel);
        Prepare(GetWorld(),Host,Host.Case+1,P,false);P->ForceNetUpdate();LastSetup=-1;
    }
}
