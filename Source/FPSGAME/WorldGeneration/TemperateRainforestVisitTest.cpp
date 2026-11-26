#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "../FPSGAMECharacter.h"
#include "TemperateForestHabitat.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputKeyEventArgs.h"
#include "Misc/Paths.h"
#include "PCGComponent.h"
#include "PCGGraphExecutionStateInterface.h"
#include "Subsystems/PCGSubsystem.h"
#include "UnrealClient.h"

namespace
{
struct FBankCheck
{
    TWeakObjectPtr<UWorld> World;
    FVector Arrival=FVector::ZeroVector;
    double Started=FPlatformTime::Seconds(), NextCount=0, StageStart=0;
    int32 Stage=0;
    bool WasGhost=false, Crouched=false, Stood=false, Sprinted=false, Grass=false;
    float WalkSpeed=0, PeakSpeed=0, Travel=0;

    void CountGrass(ATemperateHillsWorld& Hills)
    {
        constexpr int32 Grid=1600;
        const FVector Extent(800,800,1000);
        const FBox Plot(Arrival-Extent,Arrival+Extent);
        TInlineComponentArray<UPCGComponent*> Layers(&Hills);
        auto** Source=Layers.FindByPredicate([](UPCGComponent* C){return C->GetFName()==TEXT("PCGLayer3");});
        if(!Source)return;
        const auto Descriptor=FPCGGridDescriptor().SetGridSize(Grid).SetIs2DGrid(true).SetIsRuntime(true);
        auto& State=(*Source)->GetExecutionState();
        for(int32 Y=FMath::FloorToInt(Plot.Min.Y/Grid);Y<=FMath::FloorToInt(Plot.Max.Y/Grid);++Y)
        for(int32 X=FMath::FloorToInt(Plot.Min.X/Grid);X<=FMath::FloorToInt(Plot.Max.X/Grid);++X)
        {
            auto* Local=State.GetLocalSource(Descriptor,FIntVector(X,Y,0));
            if(!Local||!Local->GetExecutionState().IsGenerated()||Local->GetExecutionState().IsGenerating())return;
        }
        TSet<FIntPoint> Occupied;
        TMap<FName,int32> Counts;
        int32 Tufts=0;
        for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
        {
            if(It->GetWorld()!=World.Get()||!It->IsRegistered()||!It->IsVisible()||!It->Bounds.GetBox().Intersect(Plot))continue;
            UStaticMesh* Mesh=It->GetStaticMesh();
            const auto MatchesMesh=[Mesh](const auto& Ref){return Ref.Get()==Mesh;};
            if(!Mesh||(!Hills.Assets->RainforestGrass.ContainsByPredicate(MatchesMesh)&&
                !Hills.Assets->RainforestCarpetGrass.ContainsByPredicate(MatchesMesh)))continue;
            for(int32 Index:It->GetInstancesOverlappingBox(Plot,true))
            {
                FTransform T;if(!It->GetInstanceTransform(Index,T,true))continue;
                const FVector P=T.GetLocation();if(!Plot.IsInside(P))continue;
                ++Tufts;++Counts.FindOrAdd(Mesh->GetFName());
                Occupied.Add(FIntPoint(FMath::FloorToInt((P.X-Plot.Min.X)/200),FMath::FloorToInt((P.Y-Plot.Min.Y)/200)));
            }
        }
        UE_LOG(LogTemp,Display,TEXT("BANK_PLOT area_m2=256 tufts=%d occupied_2m_squares=%d/64 variants=%d"),Tufts,Occupied.Num(),Counts.Num());
        for(const auto& Entry:Counts)UE_LOG(LogTemp,Display,TEXT("BANK_GRASS mesh=%s count=%d"),*Entry.Key.ToString(),Entry.Value);
        const auto& BankPalette=Hills.Assets->RainforestGrass;
        const UStaticMesh* Sedge=BankPalette.IsValidIndex(2)?BankPalette[2].Get():nullptr;
        Grass=Tufts>=256&&Occupied.Num()>=48&&Counts.Num()>=3&&Sedge&&Counts.Contains(Sedge->GetFName());
        Stage=3;StageStart=Hills.GetWorld()->GetTimeSeconds();
        auto* PC=Hills.GetWorld()->GetFirstPlayerController();
        const float Yaw=PC->GetControlRotation().Yaw;
        PC->SetControlRotation(FRotator(-17,Yaw,0));
        FScreenshotRequest::RequestScreenshot(FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("rainforest-bank.png")),false,false);
    }
    bool Tick(float)
    {
        auto* W=World.Get();if(!W)return false;
        if(FPlatformTime::Seconds()-Started>480)
        {UE_LOG(LogTemp,Error,TEXT("BANK_TEST timeout stage=%d"),Stage);FPlatformMisc::RequestExitWithStatus(false,2);return false;}
        auto* PC=W->GetFirstPlayerController();
        auto* P=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
        TActorIterator<ATemperateHillsWorld> It(W);
        if(!P||!It||!It->bReady||PC->IsMoveInputIgnored())return true;
        auto* M=P->GetCharacterMovement();const double Now=W->GetTimeSeconds();
        auto Key=[PC](FKey K,bool Down){PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,Down?IE_Pressed:IE_Released,Down?1:0));};
        if(Stage==0)
        {
            PC->EnableCheats();PC->ConsoleCommand(TEXT("BugItGo -13600 7600 5830 -6 36 0"));
            WasGhost=M->IsFlying()&&!P->GetActorEnableCollision();
            UE_LOG(LogTemp,Display,TEXT("BANK_OLD_COMMAND ghost=%d collision=%d"),WasGhost,P->GetActorEnableCollision());
            PC->ConsoleCommand(TEXT("fps.Hills.VisitRainforest"));Stage=1;
        }
        else if(Stage==1&&P->GetActorEnableCollision()&&M->IsMovingOnGround()&&
            Cast<UDynamicMeshComponent>(M->CurrentFloor.HitResult.GetComponent())&&M->CurrentFloor.HitResult.GetActor()==*It)
        {
            Arrival=P->GetActorLocation();Stage=2;
            UE_LOG(LogTemp,Display,TEXT("BANK_STANDING pos=%s floor_gap_cm=%.2f support=%s"),*Arrival.ToString(),
                M->CurrentFloor.FloorDist,*M->CurrentFloor.HitResult.GetComponent()->GetName());
        }
        else if(Stage==2&&Now>=NextCount){NextCount=Now+2;CountGrass(**It);}
        else if(Stage==3&&Now-StageStart>.6)
        {Key(EKeys::LeftControl,true);Stage=4;StageStart=Now;}
        else if(Stage==4&&Now-StageStart>.35)
        {Crouched=P->bIsCrouched;Key(EKeys::LeftControl,false);Stage=5;StageStart=Now;}
        else if(Stage==5&&Now-StageStart>.25)
        {Key(EKeys::LeftControl,true);Stage=6;StageStart=Now;}
        else if(Stage==6&&Now-StageStart>.35)
        {
            Key(EKeys::LeftControl,false);Stood=!P->bIsCrouched;
            // Use controller bindings without polling the operator's physical keyboard.
            P->bMPAutoInputActive=true;Key(EKeys::W,true);Stage=7;StageStart=Now;
        }
        else if(Stage==7)
        {
            WalkSpeed=FMath::Max(WalkSpeed,float(P->GetVelocity().Size2D()));
            if(Now-StageStart<.75)return true;
            Key(EKeys::LeftShift,true);Stage=8;StageStart=Now;
        }
        else if(Stage==8)
        {
            if(M->IsMovingOnGround())
            {PeakSpeed=FMath::Max(PeakSpeed,float(P->GetVelocity().Size2D()));Sprinted|=P->IsSprinting();}
            Travel=FMath::Max(Travel,float(FVector::Dist2D(Arrival,P->GetActorLocation())));
            if(Now-StageStart<1.5)return true;
            Key(EKeys::W,false);Key(EKeys::LeftShift,false);P->bMPAutoInputActive=false;
            const bool Passed=WasGhost&&Crouched&&Stood&&Sprinted&&Travel>100&&WalkSpeed>100&&PeakSpeed>WalkSpeed*1.1&&Grass;
            UE_LOG(LogTemp,Display,TEXT("BANK_TEST pass=%d crouch=%d stand=%d sprint=%d travel_cm=%.0f walk_cm_s=%.0f sprint_cm_s=%.0f"),Passed,Crouched,Stood,Sprinted,Travel,WalkSpeed,PeakSpeed);
            FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);return false;
        }
        return true;
    }
};
FAutoConsoleCommandWithWorld CheckRainforest(TEXT("fps.Test.RainforestBank"),TEXT("Measure streamed grass and reproduce walking after a hills visit in an isolated test game."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("RainforestBankCheck")))return;
        auto Test=MakeShared<FBankCheck>();Test->World=W;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Test](float Dt){return Test->Tick(Dt);}));
    }));
}
#endif
