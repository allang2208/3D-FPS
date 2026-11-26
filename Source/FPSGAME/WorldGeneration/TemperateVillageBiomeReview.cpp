#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "TemperateHillsGroundLayers.h"
#include "../FPSWeatherManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace VillageBiomeReview
{
struct FShot { FString Name; FVector Focus,Eye,Target; };
struct FReview
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<ACameraActor> Camera;
    TemperateHillsGround::FMapSource Map;
    TSharedPtr<FJsonObject> Result=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Checks,Captures,Boundary;
    TArray<FShot> Shots;
    FString Out;
    double Started=FPlatformTime::Seconds(),StageAt=Started,NextLog=0;
    int32 Stage=0,Shot=0,Errors=0,LastInstances=-1,Stable=0;

    void Check(const FString& Name,bool Pass,double Value)
    {
        auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("name"),Name);
        J->SetBoolField(TEXT("pass"),Pass);J->SetNumberField(TEXT("value"),Value);
        Checks.Add(MakeShared<FJsonValueObject>(J));if(!Pass)++Errors;
    }
    FVector Ground(const FVector2D& P) const { return FVector(P, Hills->Height(P.X,P.Y)); }
    bool Finish(const FString& Reason)
    {
        Result->SetBoolField(TEXT("pass"),Errors==0);Result->SetStringField(TEXT("reason"),Reason);
        Result->SetArrayField(TEXT("checks"),Checks);Result->SetArrayField(TEXT("captures"),Captures);
        Result->SetArrayField(TEXT("boundary"),Boundary);
        Result->SetNumberField(TEXT("elapsed_s"),FPlatformTime::Seconds()-Started);
        FString Json;FJsonSerializer::Serialize(Result.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_BIOME_RESULT pass=%d checks=%d shots=%d reason=%s"),Errors==0,Checks.Num(),Shot,*Reason);
        const uint8 Status=Errors?1:0;
        if(World.IsValid())UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        const double ExitAt=FPlatformTime::Seconds()+8.;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Status,ExitAt](float)
        {if(FPlatformTime::Seconds()<ExitAt)return true;FPlatformMisc::RequestExitWithStatus(false,Status);return false;}));
        return false;
    }
    void Survey()
    {
        Hills->CopyMapGround(Map);
        const auto& V=Map.Village;const auto& R=*Map.River;
        Result->SetNumberField(TEXT("seed"),Hills->Seed);Result->SetNumberField(TEXT("generator_version"),Hills->GeneratorVersion);
        Result->SetStringField(TEXT("world_id"),Hills->WorldId.ToString());
        Result->SetStringField(TEXT("village"),V.Ground.ToString());
        Result->SetNumberField(TEXT("shoulder_m"),V.Shoulder/100.);
        Check(TEXT("current_hilltop_village"),Hills->GeneratorVersion==3&&V.bPlaced&&V.bHilltop,Hills->GeneratorVersion);
        Check(TEXT("runtime_shared_village_rainforest_mask"),R.bVillageRainforest,R.ForestGridSize);
        double CoreMax=0.;int32 CoreSamples=0;
        for(double Y=-V.PadHalfY;Y<=V.PadHalfY;Y+=500.)for(double X=-V.PadHalfX;X<=V.PadHalfX;X+=500.)
        {const auto P=V.World(X,Y);CoreMax=FMath::Max(CoreMax,R.RainforestWeight(P.X,P.Y));++CoreSamples;}
        Check(TEXT("village_pad_yellow"),CoreMax<.01,CoreMax);Result->SetNumberField(TEXT("pad_samples"),CoreSamples);
        const auto Gate=V.Mouth(-1.),Junction=Gate-V.Axis*V.FeederLength;
        const FVector2D Entry(Hills->GetGenerationAnchor());
        double RouteMax=0.;int32 RouteSamples=0;
        auto Road=[&](const FVector2D& P,const FVector2D& Side)
        {for(double Offset:{-1000.,0.,1000.}){const auto Q=P+Side*Offset;RouteMax=FMath::Max(RouteMax,R.RainforestWeight(Q.X,Q.Y));++RouteSamples;}};
        for(int32 I=0;I<=100;++I)Road(FMath::Lerp(Gate,Junction,I/100.),FVector2D(-V.Axis.Y,V.Axis.X));
        for(int32 I=0;I<=150;++I)
        {const double X=FMath::Lerp(Entry.X,Junction.X,I/150.);Road(FVector2D(X,TemperateHillsSurface::ValleyY(X,Hills->Seed)),FVector2D(0,1));}
        Check(TEXT("approach_continuous_yellow_20m_core"),RouteMax<.01,RouteMax);Result->SetNumberField(TEXT("route_samples"),RouteSamples);
        int32 Yellow=0,Transition=0,Forest=0;
        for(uint8 W:R.RainforestMask){if(W==0)++Yellow;else if(W==255)++Forest;else ++Transition;}
        Result->SetNumberField(TEXT("yellow_grid_cells"),Yellow);Result->SetNumberField(TEXT("transition_grid_cells"),Transition);
        Result->SetNumberField(TEXT("rainforest_grid_cells"),Forest);
        Check(TEXT("surrounding_rainforest_present"),Forest>R.RainforestMask.Num()*.5,Forest/double(R.RainforestMask.Num()));
        // Survey actual final runtime weights, including the lower slope outside the pad.
        for(int32 I=0;I<16;++I)
        {
            const double A=2.*UE_PI*I/16.;const FVector2D D(FMath::Cos(A),FMath::Sin(A));
            double Radius=0.;FVector2D P(V.Ground);
            for(Radius=500.;Radius<45000.;Radius+=200.)
            {P=FVector2D(V.Ground)+D*Radius;if(R.RainforestWeight(P.X,P.Y)>=.5)break;}
            auto J=MakeShared<FJsonObject>();J->SetNumberField(TEXT("angle_deg"),I*22.5);
            J->SetNumberField(TEXT("radius_m"),Radius/100.);J->SetNumberField(TEXT("x"),P.X);J->SetNumberField(TEXT("y"),P.Y);
            const auto Outside=P+D*3000.;J->SetNumberField(TEXT("outside_weight"),R.RainforestWeight(Outside.X,Outside.Y));
            Boundary.Add(MakeShared<FJsonValueObject>(J));
        }
        const FVector2D Side(-V.Axis.Y,V.Axis.X),Center(V.Ground);
        const FVector Target=V.Ground+FVector(0,0,600);
        Shots.Add({TEXT("01-village-overview"),V.Ground,Target+FVector(12000.,-15000.,18000.),Target});
        auto AddBoundary=[&](const FString& Name,FVector2D D)
        {
            FVector2D P=Center;
            for(double Radius=500.;Radius<40000.;Radius+=100.)
            {P=Center+D*Radius;if(R.RainforestWeight(P.X,P.Y)>=.5)break;}
            const FVector Q=Ground(P);
            Shots.Add({Name,Q,Ground(P-D*4500.)+FVector(0,0,2600),Ground(P+D*3500.)+FVector(0,0,600)});
        };
        AddBoundary(TEXT("02-hill-rainforest-transition"),Side);
        AddBoundary(TEXT("03-opposite-rainforest-transition"),-Side);
        const FVector P=Ground(Junction);
        Shots.Add({TEXT("04-yellow-village-approach"),P,P+FVector(-V.Axis*6000.+Side*3500.,4200.),V.Ground+FVector(0,0,350)});
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();auto* W=World.Get();
        if(!W){++Errors;return Finish(TEXT("world unavailable"));}
        if(Now-Started>780.){++Errors;return Finish(TEXT("runtime timeout"));}
        auto* PC=W->GetFirstPlayerController();APawn* Pawn=PC?PC->GetPawn():nullptr;
        if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
        if(Now>NextLog){NextLog=Now+15.;UE_LOG(LogTemp,Display,TEXT("VILLAGE_BIOME_PROGRESS stage=%d shot=%d ready=%d"),Stage,Shot,Hills.IsValid()&&Hills->bReady);}
        if(!Hills.IsValid()||!PC||!Pawn||!Hills->bReady)return true;
        if(Stage==0)
        {
            Hills->CopyMapGround(Map);
            if(!Map.River||!Map.Village.bPlaced){++Errors;return Finish(TEXT("hilltop village missing"));}
            Survey();
            // Aerial evidence needs the same generated vegetation visible beyond
            // gameplay's 230 m tree fade. These overrides live only in this host.
            PC->ConsoleCommand(TEXT("r.SetRes 1920x1080w"));
            PC->ConsoleCommand(TEXT("r.ScreenPercentage 100"));
            PC->ConsoleCommand(TEXT("foliage.CullDistanceScale 3"));
            PC->ConsoleCommand(TEXT("r.ViewDistanceScale 3"));
            PC->ConsoleCommand(TEXT("pcg.RuntimeGeneration.GlobalRadiusMultiplier 2"));
            Hills->DetailRadiusMeters=256.f;Hills->ViewRadiusMeters=512.f;
            Result->SetStringField(TEXT("capture_view_overrides"),TEXT("1920x1080; foliage fade x3; PCG load radius x2; terrain detail 256m/view 512m; seed and biome formulas unchanged"));
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
            {It->SetWeatherState(EFPSWeatherState::Clear);It->RealSecondsPerGameDay=8640000.f;It->AdvanceGameTime(FMath::Fmod(.42f-It->NormalizedDayTime+1.f,1.f)*24.f+.00001f);}
            Pawn->SetCanBeDamaged(false);Pawn->SetActorHiddenInGame(true);
            if(auto* C=Cast<ACharacter>(Pawn))C->GetCharacterMovement()->DisableMovement();
            if(auto* VP=W->GetGameViewport())VP->RemoveAllViewportWidgets();
            Camera=W->SpawnActor<ACameraActor>();Camera->GetCameraComponent()->SetFieldOfView(75.f);
            PC->SetViewTarget(Camera.Get());Stage=1;
        }
        if(Stage==1)
        {
            if(Shot>=Shots.Num())return Finish(TEXT("current-seed runtime biome survey and four scene captures complete"));
            const auto& S=Shots[Shot];Pawn->SetActorLocation(S.Focus+FVector(0,0,110),false,nullptr,ETeleportType::TeleportPhysics);
            Camera->SetActorLocationAndRotation(S.Eye,(S.Target-S.Eye).Rotation());
            PC->SetViewTarget(Camera.Get());LastInstances=-1;Stable=0;StageAt=Now;Stage=2;return true;
        }
        if(Stage==2&&Now-StageAt>=50.)
        {
            int32 Instances=0,Components=0,ForestInstances=0;
            TSet<FString> Names;
            for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
            {
                if(It->GetWorld()!=W||!It->IsRegistered()||!It->GetStaticMesh())continue;
                Instances+=It->GetInstanceCount();++Components;
                const FString Name=It->GetStaticMesh()->GetPathName();Names.Add(Name);
                if(Name.Contains(TEXT("Rainforest"))||Name.Contains(TEXT("Forest")))ForestInstances+=It->GetInstanceCount();
            }
            if(Instances==LastInstances)++Stable;else Stable=0;
            LastInstances=Instances;if(Stable<60&&Now-StageAt<100.)return true;
            auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("file"),Shots[Shot].Name+TEXT(".png"));
            J->SetStringField(TEXT("eye"),Shots[Shot].Eye.ToString());J->SetStringField(TEXT("focus"),Shots[Shot].Focus.ToString());
            J->SetNumberField(TEXT("streaming_wait_s"),Now-StageAt);J->SetNumberField(TEXT("instanced_components"),Components);
            J->SetNumberField(TEXT("instances"),Instances);J->SetNumberField(TEXT("forest_named_instances"),ForestInstances);
            TArray<TSharedPtr<FJsonValue>> Meshes;for(const auto& N:Names)Meshes.Add(MakeShared<FJsonValueString>(N));
            J->SetArrayField(TEXT("live_meshes"),Meshes);Captures.Add(MakeShared<FJsonValueObject>(J));
            FScreenshotRequest::RequestScreenshot(Out/(Shots[Shot].Name+TEXT(".png")),false,false);
            UE_LOG(LogTemp,Display,TEXT("VILLAGE_BIOME_CAPTURE %s instances=%d"),*Shots[Shot].Name,Instances);
            Stage=3;StageAt=Now;return true;
        }
        if(Stage==3&&Now-StageAt>3.){++Shot;Stage=1;}
        return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.VillageBiomeReview"),TEXT("Opt-in isolated current-seed biome survey and screenshots."),
FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{
    if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("VillageBiomeReview")))return;
    auto R=MakeShared<FReview>();R->World=W;
    FParse::Value(FCommandLine::Get(),TEXT("VillageBiomeOutput="),R->Out);
    if(R->Out.IsEmpty())return;
    IFileManager::Get().MakeDirectory(*R->Out,true);
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float Dt){return R->Tick(Dt);}));
}));
}
#endif
