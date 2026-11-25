#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "../Movement/StableRidingHorse.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Containers/Ticker.h"
#include "DynamicRHI.h"
#include "RenderTimer.h"
#include "Engine/DirectionalLight.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "UnrealClient.h"

namespace HorseSceneCost
{
struct FCapture
{
    FString Dir,Rows=TEXT("pass,visible,sample,wall_ms,game_ms,render_ms,gpu_ms\n");
    TArray<TWeakObjectPtr<AStableRidingHorse>> Horses;
    TWeakObjectPtr<ACameraActor> Camera;
    int Index=0,Frame=0;double Last=0,Started=FPlatformTime::Seconds();
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();
        UWorld* W=nullptr;for(const auto& C:GEngine->GetWorldContexts())
            if(C.World()&&C.World()->IsGameWorld()&&C.World()->HasBegunPlay()){W=C.World();break;}
        if(Now-Started>230.){FPlatformMisc::RequestExit(false);return false;}
        auto* PC=W?W->GetFirstPlayerController():nullptr;if(!PC)return true;
        if(!Camera.IsValid())
        {
            FVector Centre=FVector::ZeroVector;
            for(TActorIterator<AStableRidingHorse> It(W);It;++It){Horses.Add(*It);Centre+=It->GetActorLocation();}
            if(Horses.Num()<2){Horses.Reset();return true;}
            Centre/=Horses.Num();
            // Bring both residents into the yard for an unobstructed comparison in this transient test world.
            Centre.Y-=510.;
            for(int32 I=0;I<Horses.Num();++I)
            {
                auto* H=Horses[I].Get();
                const FVector Spot(Centre.X+310.*(I-.5*(Horses.Num()-1)),Centre.Y,H->GetActorLocation().Z);
                H->SetActorLocationAndRotation(Spot,FRotator(0.,I%2?26.:-22.,0.),false,nullptr,ETeleportType::TeleportPhysics);
            }
            Centre.Z+=12.;
            const FVector Eye=Centre+FVector(0,-575.,58.);
            Camera=W->SpawnActor<ACameraActor>(Eye,(Centre-Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(72.f);
            PC->bAutoManageActiveCameraTarget=false;PC->SetViewTarget(Camera.Get());
            bool AddedSun=false;
            if(!TActorIterator<ADirectionalLight>(W))
            {
                W->SpawnActor<ADirectionalLight>(Eye,FRotator(-48,68,0));AddedSun=true;
            }
            FFileHelper::SaveStringToFile(FString::Printf(TEXT("horses=%d addedSun=%d eye=%s target=%s"),Horses.Num(),int(AddedSun),*Eye.ToString(),*Centre.ToString()),*(Dir/TEXT("view.txt")));
            Last=Now;return true;
        }
        const bool Visible=Index==0||Index==3;
        if(Index==0 && Now-Started<18.){Last=Now;return true;}
        if(Frame==0)for(auto& H:Horses)if(H.IsValid())H->SetActorHiddenInGame(!Visible);
        const int Warmup=Index==0?240:75;
        if(Frame==Warmup && Index==0)FScreenshotRequest::RequestScreenshot(Dir/TEXT("stable-view.png"),false,false);
        if(Frame>Warmup+5)
            Rows+=FString::Printf(TEXT("%d,%d,%d,%.4f,%.4f,%.4f,%.4f\n"),Index,int(Visible),Frame-Warmup-6,1000.*(Now-Last),
                FPlatformTime::ToMilliseconds(GGameThreadTime),FPlatformTime::ToMilliseconds(GRenderThreadTime),FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)));
        Last=Now;
        if(++Frame==Warmup+186)
        {
            Frame=0;if(++Index==4){FFileHelper::SaveStringToFile(Rows,*(Dir/TEXT("gpu.csv")));FPlatformMisc::RequestExit(false);return false;}
        }
        return true;
    }
};
static FAutoConsoleCommand Cmd(TEXT("fps.Test.HorseSceneCost"),TEXT("Sample visible stable horses at a fixed camera."),
 FConsoleCommandDelegate::CreateLambda([]{auto C=MakeShared<FCapture>();
    if(!FParse::Value(FCommandLine::Get(),TEXT("HorseSceneOut="),C->Dir))return;
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([C](float D){return C->Tick(D);}));
 }));
}
#endif
