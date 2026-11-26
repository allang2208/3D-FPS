#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "TemperateHillsCaptureReadiness.h"
#include "TemperateHillsGroundLayers.h"
#include "TemperateLakeCoveOutlet.h"
#include "TemperateVegetationPlacement.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "VillageDefenseSection.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "Components/CapsuleComponent.h"
#include "Containers/Ticker.h"
#include "DynamicRHI.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ProfilingDebugging/MiscTrace.h"
#include "RenderTimer.h"
#include "RenderingThread.h"
#include "UnrealClient.h"
#include "TemperateQuarryYard.h"
#if WITH_EDITOR
#include "StaticMeshAttributes.h"
#endif

namespace HillsRouteWalk
{
struct FStop
{
    FVector2D At, Look;
    const TCHAR* Name;
    bool Photograph;
};
enum class EStage { Boot, Settle, Soak, Walk, Photograph };

struct FWalk
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    TArray<FStop> Stops;
    FString Out, Shot, Frames=TEXT("lap,leg,frame_ms,game_ms,render_ms,gpu_ms,x,y,z,wetness,rain\n");
    FString Events=TEXT("lap,stop,pawn_x,pawn_y,pawn_z,eye_x,eye_y,eye_z,pitch,yaw,wetness,rain\n");
    EStage Stage=EStage::Boot;
    int32 Lap=0,Leg=0;
    bool Requested=false,ForwardHeld=false;
    int32 NextFeederPhoto=0;
    double Began=FPlatformTime::Seconds(),Since=Began,Previous=0.,NextPoll=0.,LastProgress=0.,Best=DBL_MAX,NextStatus=0.;

    void Enter(EStage NewStage,double Now)
    {Stage=NewStage;Since=Now;Previous=0.;NextPoll=0.;}
    void Save()
    {
        FFileHelper::SaveStringToFile(Frames,*(Out/TEXT("frames.csv")));
        FFileHelper::SaveStringToFile(Events,*(Out/TEXT("stops.csv")));
    }
    bool Finish(const TCHAR* Reason,bool OK)
    {
        Save();
        if(OK&&Hills.IsValid()&&!Stops.IsEmpty())
        {
            FString Wildlife=TEXT("actor_class\n");
            for(TActorIterator<ACharacter> It(World.Get());It;++It)
                if(It->ActorHasTag(TEXT("WildlifeSpawned")))Wildlife+=It->GetClass()->GetPathName()+TEXT("\n");
            FFileHelper::SaveStringToFile(Wildlife,*(Out/TEXT("wildlife.csv")));
            const FVector Center(Stops[4].At,0.);
            const FBox Area(Center-FVector(10000.,9500.,100000.),Center+FVector(10000.,9500.,100000.));
            FString Items=TEXT("group,layer,x,y,z,asset\n");
            for(int32 Layer:{3,4})
            {
                TArray<FTemperatePlacement> Plants;
                Hills->GetPlacements(Layer,Area,Plants);
                for(const auto& P:Plants)if((P.CandidateId>>56)==0x72)
                {
                    const auto At=P.Transform.GetLocation();
                    Items+=FString::Printf(TEXT("%d,%d,%.1f,%.1f,%.1f,%s\n"),int32((P.CandidateId>>16)&255),
                        Layer,At.X,At.Y,At.Z,*P.Mesh.GetAssetName());
                }
            }
            FFileHelper::SaveStringToFile(Items,*(Out/TEXT("west-pockets.csv")));
            // Read the accepted placements after the movement samples are saved.
            // Include the actual approach corridor and the outside of the turn.
            FString Margins=TEXT("group,item,x,y,z,asset\n");
            const FBox Corridor=FBox(FVector(Stops[4].At,0.),FVector(Stops[4].At,0.))+
                FVector(Stops[6].At,0.);
            TArray<FTemperatePlacement> Floor;
            Hills->GetPlacements(3,Corridor.ExpandBy(FVector(2100.,2100.,100000.)),Floor);
            for(const auto& P:Floor)if((P.CandidateId>>56)==0x73)
            {
                const auto At=P.Transform.GetLocation();
                Margins+=FString::Printf(TEXT("%d,%d,%.1f,%.1f,%.1f,%s\n"),int32((P.CandidateId>>16)&255),
                    int32(P.CandidateId&65535),At.X,At.Y,At.Z,*P.Mesh.GetAssetName());
            }
            FFileHelper::SaveStringToFile(Margins,*(Out/TEXT("field-margins.csv")));
        }
        const auto Summary=FString::Printf(TEXT("complete=%d\nreason=%s\nlap=%d\nleg=%d\n"),OK,Reason,Lap,Leg);
        FFileHelper::SaveStringToFile(Summary,*(Out/TEXT("walk.txt")));
        UE_LOG(LogTemp,Display,TEXT("HILLS_ROUTE %s"),*Summary);
        if(World.IsValid())
        {
            // This process exits after the walk. Drain pending parallel scene commands
            // before travel releases the landscape and its instanced foliage.
            FlushRenderingCommands();
            if (IConsoleVariable* PipeMode = IConsoleManager::Get().FindConsoleVariable(TEXT("r.RenderCommandPipeMode")))
            {
                if (PipeMode->GetInt() > 1) PipeMode->Set(1, ECVF_SetByCode);
            }
            FlushRenderingCommands();
            UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        }
        const double ExitAt=FPlatformTime::Seconds()+6.;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([ExitAt,OK](float)
        {if(FPlatformTime::Seconds()<ExitAt)return true;FPlatformMisc::RequestExitWithStatus(false,OK?0:1);return false;}));
        return false;
    }
    FVector Ground(FVector2D At,double Up) const
    {return FVector(At,Hills->Height(At.X,At.Y)+Up);}
    void Route()
    {
        const auto& V=Hills->GetVillageSite();
        const auto J=V.Approach(-1.,V.FeederLength,Hills->Seed);
        const auto Incoming=V.Approach(-1.,V.FeederLength+4200.,Hills->Seed);
        const FVector2D Away(0.,V.Ground.Y<J.Y?1.:-1.);
        const auto Wood=Incoming+Away*3600.;
        const auto Wall=V.WallHalfSize();
        Stops={
            {Wood,Incoming+FVector2D(1200.,0.),TEXT("entry_start"),false},
            {Incoming+Away*2400.,Incoming+Away*2830.+FVector2D(1920.,0.),TEXT("forest_edge"),true},
            {Incoming,J,TEXT("valley"),false},
            {J-FVector2D(850.,0.),J+V.Axis*900.,TEXT("first_bend"),true},
            {J,V.Mouth(-1.),TEXT("junction"),false},
            {V.World(-Wall.X-3400.,0.),V.Mouth(-1.),TEXT("feeder"),false},
            {V.World(-Wall.X-1550.,-2250.),V.World(-Wall.X-260.,-3050.),TEXT("west_wall"),true},
            {V.World(-Wall.X-1100.,0.),V.World(-Wall.X+900.,0.),TEXT("gate"),true},
            {V.World(-Wall.X+750.,0.),V.World(-Wall.X+2000.,0.),TEXT("inside"),false}
        };
        UE_LOG(LogTemp,Display,TEXT("HILLS_ROUTE world=%s seed=%d feeder=%.1f start=%s edge=%.3f"),
            *Hills->WorldId.ToString(),Hills->Seed,V.FeederLength,*Wood.ToString(),
            Hills->RainforestWeight(Stops[1].At.X,Stops[1].At.Y));
        FString Contour=TEXT("station_cm,green_10_cm,green_50_cm,green_90_cm\n");
        for(int32 S=-3200;S<=3200;S+=200)
        {
            const double X=Incoming.X+S,Y=TemperateHillsSurface::ValleyY(X,Hills->Seed);
            int32 Low=-1,Mid=-1,High=-1;
            for(int32 D=0;D<=8800;D+=50)
            {
                const double W=Hills->RainforestWeight(X,Y+Away.Y*D);
                if(Low<0&&W>=.1)Low=D;
                if(Mid<0&&W>=.5)Mid=D;
                if(W>=.9){High=D;break;}
            }
            Contour+=FString::Printf(TEXT("%d,%d,%d,%d\n"),S,Low,Mid,High);
        }
        FFileHelper::SaveStringToFile(Contour,*(Out/TEXT("forest-edge.csv")));
    }
    void PlaceAtStart(ACharacter* C,double Now)
    {
        auto* Move=C->GetCharacterMovement();
        Move->StopMovementImmediately();Move->DisableMovement();
        C->SetActorLocation(Ground(Stops[0].At,C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+4.),false,nullptr,ETeleportType::TeleportPhysics);
        Leg=1;Best=DBL_MAX;LastProgress=Now;Enter(EStage::Settle,Now);
    }
    void Aim(APlayerController* PC,FVector Target)
    {
        FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);
        PC->SetControlRotation((Target-Eye).Rotation());
    }
    void Forward(APlayerController* PC,bool Down)
    {
        if(ForwardHeld==Down)return;
        if(auto* P=Cast<AFPSGAMECharacter>(PC->GetPawn()))P->bMPAutoInputActive=Down;
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,Down?IE_Pressed:IE_Released,Down?1.f:0.f));
        ForwardHeld=Down;
    }
    void Advance(ACharacter* C,double Now)
    {
        if(++Leg<Stops.Num()){Best=DBL_MAX;LastProgress=Now;Enter(EStage::Walk,Now);return;}
        Save();
        if(Lap==0)
        {
            ++Lap;Weather->SetWeatherState(EFPSWeatherState::Rain);PlaceAtStart(C,Now);
            Enter(EStage::Soak,Now);
        }
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();
        if(!World.IsValid()||Now-Began>1500.)return Finish(TEXT("world or route timeout"),false);
        auto* PC=World->GetFirstPlayerController();
        auto* C=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
        if(!C)return true;
        if(Stage==EStage::Boot)
        {
            if(Now<NextPoll)return true;NextPoll=Now+.5;
            for(TActorIterator<ATemperateHillsWorld> It(World.Get());It;++It)Hills=*It;
            for(TActorIterator<AFPSWeatherManager> It(World.Get());It;++It)Weather=*It;
            if(!Hills.IsValid()||!Hills->bReady||!Weather.IsValid()||!Hills->GetVillageSite().bPlaced||PC->IsMoveInputIgnored())return true;
            Route();C->SetCanBeDamaged(false);
            Weather->RealSecondsPerGameDay=864000.f;
            Weather->AdvanceGameTime(FMath::Fmod(10.5f-24.f*Weather->NormalizedDayTime+24.f,24.f)+.0001f);
            Weather->SetWeatherState(EFPSWeatherState::Clear);
            PlaceAtStart(C,Now);
            return true;
        }
        if(!Weather.IsValid()||!Hills.IsValid())return Finish(TEXT("route actors unloaded"),false);
        const double Wet=Weather->GetSurfaceWetness(),Rain=Weather->GetEffectiveRainIntensity();
        if(Now>NextStatus)
        {
            NextStatus=Now+15.;
            const auto* M=C->GetCharacterMovement();
            UE_LOG(LogTemp,Display,TEXT("HILLS_ROUTE stage=%d lap=%d leg=%d pos=%s wet=%.3f rain=%.3f mode=%d vmax=%.1f speed=%.1f accel=%.1f ignored=%d floor=%s"),
                int32(Stage),Lap,Leg,*C->GetActorLocation().ToCompactString(),Wet,Rain,int32(M->MovementMode),
                M->GetMaxSpeed(),C->GetVelocity().Size2D(),M->GetCurrentAcceleration().Size2D(),PC->IsMoveInputIgnored(),
                *GetNameSafe(M->CurrentFloor.HitResult.GetComponent()));
        }
        if(Stage==EStage::Soak)
        {
            if(Wet>=.98&&Now>=NextPoll)
            {
                NextPoll=Now+1.;const auto P=C->GetActorLocation();
                if(HillsLandscapeCapture::Readiness(Hills.Get(),P,P).Complete())
                {Weather->SetWeatherState(EFPSWeatherState::Cloudy);Enter(EStage::Settle,Now);}
            }
            return true;
        }
        if(Stage==EStage::Settle)
        {
            if(Now<NextPoll)return true;NextPoll=Now+1.;
            FHitResult Hit;
            if(Now-Since<8.||Rain>.025||(!Lap&&Wet>.035)||
                !HillsLandscapeCapture::GroundHit(Hills.Get(),Stops[0].At,Hit))return true;
            if(!HillsLandscapeCapture::Readiness(Hills.Get(),C->GetActorLocation(),Hit.ImpactPoint).Complete())return true;
            C->SetActorLocation(Hit.ImpactPoint+FVector::UpVector*(C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.));
            C->ClientCheatWalk();C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            PC->SetViewTarget(C);Aim(PC,Ground(Stops[1].At,120.));LastProgress=Now;Enter(EStage::Walk,Now);
            UE_LOG(LogTemp,Display,TEXT("HILLS_ROUTE walking lap=%d wetness=%.3f rain=%.3f"),Lap,Wet,Rain);
            return true;
        }
        const auto& Stop=Stops[Leg];
        const auto P=C->GetActorLocation();
        // Optional art references on the dry pass only. The measured wet walk
        // keeps its original stops and never issues a moving screenshot.
        if(Lap==0&&Leg==5&&NextFeederPhoto<2&&Stage==EStage::Walk)
        {
            const auto& V=Hills->GetVillageSite();
            const double Station=FVector2D::DotProduct(V.Mouth(-1.)-FVector2D(P),V.Axis);
            const double At=V.FeederLength*(NextFeederPhoto==0?.64:.38)+1550.;
            if(Station<=At)
            {
                const TCHAR* Name=NextFeederPhoto==0?TEXT("dry_feeder_stones.png"):TEXT("dry_feeder_wood.png");
                FScreenshotRequest::RequestScreenshot(Out/Name,false,false);
                ++NextFeederPhoto;
            }
        }
        if(Stage==EStage::Photograph)
        {
            Aim(PC,Ground(Stop.Look,70.));
            if(Now-Since<1.)return true;
            if(!Requested)
            {
                FVector Eye;FRotator R;PC->GetPlayerViewPoint(Eye,R);
                Events+=FString::Printf(TEXT("%d,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.4f,%.4f\n"),
                    Lap,Stop.Name,P.X,P.Y,P.Z,Eye.X,Eye.Y,Eye.Z,R.Pitch,R.Yaw,Wet,Rain);
                Shot=Out/FString::Printf(TEXT("%s_%s.png"),Lap?TEXT("wet"):TEXT("dry"),Stop.Name);
                FScreenshotRequest::RequestScreenshot(Shot,false,false);Requested=true;
            }
            if(Now-Since>24.)return Finish(TEXT("screenshot timeout"),false);
            if(Now-Since>2.&&IFileManager::Get().FileSize(*Shot)>0)Advance(C,Now);
            return true;
        }
        if(Previous>0.)Frames+=FString::Printf(TEXT("%d,%s,%.3f,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f,%.4f,%.4f\n"),
            Lap,Stop.Name,1000.*(Now-Previous),FPlatformTime::ToMilliseconds(GGameThreadTime),
            FPlatformTime::ToMilliseconds(GRenderThreadTime),FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)),
            P.X,P.Y,P.Z,Wet,Rain);
        Previous=Now;
        const FVector2D Delta=Stop.At-FVector2D(P);
        const double Distance=Delta.Size();
        if(Distance<Best-15.){Best=Distance;LastProgress=Now;}
        if(Now-LastProgress>18.){Forward(PC,false);return Finish(TEXT("character movement blocked"),false);}
        if(Leg==Stops.Num()-1)
        {
            for(TActorIterator<AVillageDefenseGate> It(World.Get());It;++It)
            {
                if(FVector::DistSquared2D(It->GetActorLocation(),P)>=FMath::Square(1250.))continue;
                if(It->BlocksPassage())
                {
                    // Let the leaves clear the approach before the player's
                    // capsule enters their swing. Retry a stopped, obstructed gate.
                    Forward(PC,false);
                    if(!It->IsActorTickEnabled()&&Now>=NextPoll){It->ToggleDoor();NextPoll=Now+.7;}
                    return true;
                }
                break;
            }
        }
        if(Distance<65.)
        {
            if(Stop.Photograph){Forward(PC,false);Requested=false;Enter(EStage::Photograph,Now);}
            else
            {
                if(Leg==Stops.Num()-1)Forward(PC,false);
                if(Lap&&Leg==Stops.Num()-1)return Finish(TEXT("both walks reached inside west gate"),true);
                Advance(C,Now);
            }
        }
        else
        {
            const auto Direction=Delta.GetSafeNormal();
            Aim(PC,Ground(FVector2D(P)+Direction*1500.,125.));
            Forward(PC,true);
        }
        return true;
    }
};
#include "TemperateHillsShoreWalk.inl"
#include "TemperateHillsQuarryWalk.inl"
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HillsRouteWalk"),TEXT("Walk the west village approach in a copied world."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("HillsRouteWalk")))return;
        auto Walk=MakeShared<FWalk>();Walk->World=W;
        if(!FParse::Param(FCommandLine::Get(),TEXT("HillsFeederPhotos")))Walk->NextFeederPhoto=2;
        if(!FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeOutput="),Walk->Out))return;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Walk](float Dt){return Walk->Tick(Dt);}));
    }));
}
#endif
