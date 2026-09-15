#include "FPSStairAudit.h"
#include "FPSCharacterMovementComponent.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

namespace FPSStairAudit
{
    const FVector Origin(50000, 0, 10000);
    const TCHAR* Names[]={TEXT("step20"),TEXT("step40"),TEXT("reject40_5"),TEXT("reject45"),
        TEXT("stairs_up"),TEXT("stairs_down"),TEXT("diagonal"),TEXT("sprint"),
        TEXT("crouch"),TEXT("ceiling"),TEXT("jump"),TEXT("stop_on_step"),TEXT("ramp"),TEXT("no_step_surface")};
}

UFPSStairAudit::UFPSStairAudit()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
}

void UFPSStairAudit::BeginPlay()
{
    Super::BeginPlay();
    AddTickPrerequisiteActor(GetOwner());
    FString Run(TEXT("stairs"));
    FParse::Value(FCommandLine::Get(), TEXT("StairRun="), Run);
    int32 RequestedCase=0;
    if(FParse::Value(FCommandLine::Get(),TEXT("StairCase="),RequestedCase)) Case=FMath::Clamp(RequestedCase,0,13);
    Output = FPaths::ProjectSavedDir()/TEXT("StairMovement")/Run;
    IFileManager::Get().MakeDirectory(*Output, true);
    Samples=TEXT("case,frame,dt,x,y,capsule_z,camera_z,offset,speed,grounded\n");
}

void UFPSStairAudit::Key(FKey InputKey, bool bDown)
{
    GetWorld()->GetFirstPlayerController()->InputKey(FInputKeyEventArgs::CreateSimulated(InputKey,
        bDown ? IE_Pressed : IE_Released, bDown ? 1.f : 0.f));
}

void UFPSStairAudit::Check(bool bPass, const TCHAR* Message)
{
    ++Checks; if (!bPass) ++Failures;
    UE_LOG(LogTemp, Display, TEXT("STAIR_AUDIT %s case=%s %s"), bPass?TEXT("PASS"):TEXT("FAIL"), FPSStairAudit::Names[Case], Message);
}

void UFPSStairAudit::SetupCase()
{
    using namespace FPSStairAudit;
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* M=CastChecked<UFPSCharacterMovementComponent>(C->GetCharacterMovement());
    for (FKey K:{EKeys::W,EKeys::LeftShift,EKeys::SpaceBar}) Key(K,false);
    C->UnCrouch();
    for (const auto& A:Fixture) if (IsValid(A)) A->Destroy();
    Fixture.Reset();
    const auto Box=[&](FVector Pos,FVector Size)
    {
        auto* A=GetWorld()->SpawnActor<AStaticMeshActor>();
        A->SetMobility(EComponentMobility::Movable);
        A->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        A->SetActorLocation(Origin+Pos); A->SetActorScale3D(Size/100.f);
        A->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
        A->SetMobility(EComponentMobility::Static); Fixture.Add(A); return A;
    };
    Box(FVector(400,0,-10),FVector(2400,2400,20));
    if(Case==4||Case==5||Case==7)
    {
        for(int I=0;I<6;++I) Box(FVector(200+I*60,0,(I+1)*10),FVector(60,400,(I+1)*20));
        Box(FVector(1400,0,60),FVector(1800,400,120));
    }
    else if(Case==12)
    {
        auto* A=Box(FVector(500,0,75),FVector(800,400,20));
        A->SetMobility(EComponentMobility::Movable);
        A->SetActorRotation(FRotator(15,0,0));
        A->SetMobility(EComponentMobility::Static);
    }
    else
    {
        const float H=Case==0?20.f:Case==2?40.5f:Case==3?45.f:40.f;
        auto* A=Box(FVector(550,0,H*.5f),FVector(700,900,H));
        if(Case==13) A->GetStaticMeshComponent()->CanCharacterStepUpOn=ECB_No;
        if(Case==9) Box(FVector(450,0,215),FVector(900,500,20));
    }
    M->StopMovementImmediately();
    const FVector Start=Case==5?FVector(690,0,218.15):FVector(0,0,98.15);
    const float Yaw=Case==5?180.f:Case==6?25.f:0.f;
    C->SetActorLocationAndRotation(Origin+Start,FRotator(0,Yaw,0),false,nullptr,ETeleportType::TeleportPhysics);
    C->Controller->SetControlRotation(FRotator(0,Yaw,0));
    M->SetMovementMode(MOVE_Walking);
    M->OnTeleported();
    C->CameraMotionScale=0.f;
    if(Case==8) C->Crouch();
    Stage=1; Elapsed=0; MaxViewDelta=MaxHorizontalDelta=MaxOffset=0;
    bAirborne=bJumpSent=false; Frame=0;
}

void UFPSStairAudit::TickComponent(float DT,ELevelTick TickType,FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DT,TickType,ThisTickFunction);
    using namespace FPSStairAudit;
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* M=CastChecked<UFPSCharacterMovementComponent>(C->GetCharacterMovement());
    if(GetWorld()->GetTimeSeconds()<5.f) return;
    if(Stage==0) { SetupCase(); return; }
    Elapsed+=DT;
    if(Stage==1)
    {
        if(Elapsed<.5f) return;
        Check(FMath::IsNearlyEqual(M->MaxStepHeight,40.f),TEXT("automatic step limit is 40 cm"));
        StartZ=HighestZ=C->GetActorLocation().Z;
        PreviousPosition=C->GetActorLocation(); PreviousViewZ=C->FirstPersonCamera->GetComponentLocation().Z;
        Key(EKeys::W,true); if(Case==7)Key(EKeys::LeftShift,true);
        Stage=2;Elapsed=0; return;
    }
    if(Stage==2)
    {
        const FVector Pos=C->GetActorLocation();
        const float ViewZ=C->FirstPersonCamera->GetComponentLocation().Z;
        const float DZ=FMath::Abs(ViewZ-PreviousViewZ);
        MaxViewDelta=FMath::Max(MaxViewDelta,DZ/DT);
        MaxHorizontalDelta=FMath::Max(MaxHorizontalDelta,float((Pos-PreviousPosition).Size2D())/DT);
        MaxOffset=FMath::Max(MaxOffset,FMath::Abs(M->GetStairVisualOffset()));
        HighestZ=FMath::Max(HighestZ,float(Pos.Z)); bAirborne|=M->IsFalling();
        Samples+=FString::Printf(TEXT("%s,%d,%.6f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d\n"),
            Names[Case],Frame,DT,Pos.X-Origin.X,Pos.Y,Pos.Z-Origin.Z,ViewZ-Origin.Z,
            M->GetStairVisualOffset(),M->Velocity.Size2D(),M->IsMovingOnGround());
        if ((Case==4||Case==5) && Frame%4==0 && !FParse::Param(FCommandLine::Get(),TEXT("nullrhi")))
            FScreenshotRequest::RequestScreenshot(Output/FString::Printf(TEXT("%s_%04d.png"),Names[Case],Frame),false,false);
        if(Case==10 && !bJumpSent && M->GetStairVisualOffset() < -1.f)
        { Key(EKeys::SpaceBar,true); bJumpSent=true; JumpPressTime=Elapsed; }
        else if(Case==10 && bJumpSent && Elapsed-JumpPressTime>=.06f) Key(EKeys::SpaceBar,false);
        if(Case==11 && HighestZ>StartZ+35) Key(EKeys::W,false);
        PreviousPosition=Pos; PreviousViewZ=ViewZ; ++Frame;
        if(Elapsed<1.75f) return;
        const bool bBlocked=Case==2||Case==3||Case==9||Case==13;
        if(Case==9) Check(Pos.X-Origin.X<200.f && Pos.Z+C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()<=Origin.Z+205.1f,
            TEXT("ceiling blocks ascent without head penetration"));
        else if(bBlocked) Check(Pos.X-Origin.X<200.f && HighestZ<StartZ+5.f,TEXT("unsafe obstacle remains blocked"));
        else if(Case==5) Check(Pos.Z<StartZ-115 && Pos.X-Origin.X<170,TEXT("walks down every stair to ground"));
        else if(Case==10) Check(bJumpSent && bAirborne && HighestZ>StartZ+65,TEXT("space still jumps during active stair smoothing"));
        else if(Case==11) Check(HighestZ>StartZ+35 && M->Velocity.Size2D()<1 && Pos.X-Origin.X<300,
            TEXT("releasing forward mid-step stops without forced travel"));
        else if(Case==12) Check(HighestZ>StartZ+120,TEXT("native slope walking still works"));
        else Check(HighestZ>StartZ+((Case==4||Case==7)?115.f:Case==0?18.f:38.f),TEXT("forward input climbs to the supported top"));
        Check(!C->IsTraversing(),TEXT("walking does not trigger hand traversal"));
        if(Case!=10) Check(!bAirborne,TEXT("no falling or jump mode on the walking route"));
        Check(MaxHorizontalDelta <= (Case==7?900.f:450.f)+5.f,TEXT("no extra horizontal teleport"));
        if(Case!=10&&Case!=12) Check(MaxViewDelta <= (Case==7?680.f:345.f),TEXT("view height obeys linear per-second speed bound"));
        UE_LOG(LogTemp,Display,TEXT("STAIR_METRICS case=%s max_view_cm_s=%.3f max_horizontal_cm_s=%.3f max_offset_cm=%.3f height=%.3f"),
            Names[Case],MaxViewDelta,MaxHorizontalDelta,MaxOffset,HighestZ-StartZ);
        Key(EKeys::W,false);Key(EKeys::LeftShift,false);Stage=3;Elapsed=0;
    }
    if(Stage==3 && Elapsed>.5f)
    {
        Check(FMath::Abs(M->GetStairVisualOffset())<.01f,TEXT("stopping settles exactly without oscillation"));
        int32 RequestedCase=0;
        const bool bSingle=FParse::Value(FCommandLine::Get(),TEXT("StairCase="),RequestedCase);
        if(++Case<UE_ARRAY_COUNT(Names) && !bSingle) { Stage=0;return; }
        FFileHelper::SaveStringToFile(Samples,*(Output/TEXT("trajectory.csv")));
        UE_LOG(LogTemp,Display,TEXT("STAIR_RESULT cases=%d checks=%d failures=%d"),Case,Checks,Failures);
        SetComponentTickEnabled(false);GetWorld()->GetFirstPlayerController()->ConsoleCommand(TEXT("quit"));
    }
}
