#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "TemperateHillsGroundLayers.h"
#include "TemperateForestGroves.h"
#include "TemperateHillsPCG.h"
#include "TemperateHillsCaptureSource.h"
#include "TemperateHillsCaptureReadiness.h"
#include "TemperateHillsBackdrop.h"
#include "Engine/StaticMesh.h"
#include "PCGSubsystem.h"
#include "RuntimeGen/PCGGenSourceManager.h"
#include "../FPSWeatherManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "EngineUtils.h"
#include "Engine/GameViewportClient.h"
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

// Explicit opt-in only. The launcher provides a copied world save and module.
// No authored assets, layout rules, save identity or gameplay settings are edited.
namespace HillsLandscapeCapture
{
TArray<TSharedPtr<FJsonValue>> Array(const FVector& P)
{return {MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)};}
FVector Vector(const TArray<TSharedPtr<FJsonValue>>& A)
{return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());}
struct FShot { FString Name; FVector Eye,Target; float FOV=75.f; };

struct FCapture
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<UTemperateHillsGuestSource> GroundSource;
    TWeakObjectPtr<UGameViewportClient> Viewport;
    bool OriginalRenderingDisabled=false;
    TSharedPtr<FJsonObject> Result=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Records;
    TArray<FShot> Shots;
    FString Out,Input,Pending;
    double Started=FPlatformTime::Seconds(),StageAt=Started,LastChange=Started,NextPoll=0,ReadySince=0.,NextStatus=0.;
    int32 Stage=0,Index=0,Instances=-1;
    double RenderWarmSince=0.;
    uint64 RenderWarmFrame=0;

    bool Finish(const FString& Reason,bool Success)
    {
        if(Viewport.IsValid())Viewport->bDisableWorldRendering=OriginalRenderingDisabled;
        if(World.IsValid()&&GroundSource.IsValid())
            if(auto* PCG=World->GetSubsystem<UPCGSubsystem>())
                if(auto* Sources=PCG->GetGenSourceManager())Sources->UnregisterGenSource(GroundSource.Get());
        Result->SetStringField(TEXT("reason"),Reason);
        Result->SetBoolField(TEXT("capture_complete"),Success);
        Result->SetArrayField(TEXT("shots"),Records);
        Result->SetNumberField(TEXT("elapsed_seconds"),FPlatformTime::Seconds()-Started);
        FString Json;FJsonSerializer::Serialize(Result.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("HILLS_LANDSCAPE_CAPTURE complete=%d shots=%d reason=%s"),Success,Records.Num(),*Reason);
        UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        const double ExitAt=FPlatformTime::Seconds()+8.;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([ExitAt,Success](float)
        {if(FPlatformTime::Seconds()<ExitAt)return true;FPlatformMisc::RequestExitWithStatus(false,Success?0:1);return false;}));
        return false;
    }

    void Compose(const TemperateHillsGround::FMapSource& Map)
    {
        const auto& L=Map.River->Lake;
        const FVector2D Side(-L.Axis.Y,L.Axis.X);
        const auto Ground=[&](FVector2D P,double Up){return FVector(P,Map.Height(P.X,P.Y)+Up);};
        const FVector Target(L.Center,L.WaterZ);
        const FVector2D Outward=L.Center.GetSafeNormal();
        const FVector2D Overview=L.Center+Outward*10000.;
        Shots.Add({TEXT("01_lake_overview"),FVector(Overview,L.WaterZ+17500.),FVector(L.Center-Outward*3000.,L.WaterZ),82.f});
        FVector2D Beach=L.Center,Rock=L.Center;double BestBeach=-1.,BestRock=-1.;
        for(int32 I=0;I<180;++I)
        {
            const double A=I*2.*PI/180.;
            const FVector2D D=L.Axis*(FMath::Cos(A)*L.RadiusX)+Side*(FMath::Sin(A)*L.RadiusY);
            double Lo=.4,Hi=1.6;
            for(int32 J=0;J<20;++J){const double T=(Lo+Hi)*.5;const auto P=L.Center+D*T;if(L.Edge(P.X,P.Y)<0.)Lo=T;else Hi=T;}
            const auto P=L.Center+D*((Lo+Hi)*.5);const auto S=L.Shore(P.X,P.Y);
            if(S.Beach>BestBeach){BestBeach=S.Beach;Beach=P;}
            if(S.Rock>BestRock){BestRock=S.Rock;Rock=P;}
        }
        const auto ShoreView=[&](const TCHAR* Name,FVector2D Shore)
        {
            const FVector2D Outward=(Shore-L.Center).GetSafeNormal(),Tangent(-Outward.Y,Outward.X);
            Shots.Add({Name,Ground(Shore+Outward*1600.+Tangent*1200.,850.),FVector(Shore-Outward*1300.,L.WaterZ+70.),75.f});
        };
        ShoreView(TEXT("02_lake_cove"),Beach);ShoreView(TEXT("03_lake_headland"),Rock);
        if(!L.RiverMouths.IsEmpty())
        {
            const auto Mouth=L.RiverMouths[0],D=(Mouth-L.Center).GetSafeNormal();
            const auto Eye=Mouth+D*4300.+FVector2D(-D.Y,D.X)*2700.;
            Shots.Add({TEXT("04_river_mouth"),Ground(Eye,3000.),FVector(Mouth,L.WaterZ),78.f});
        }
        FVector2D Grove=Beach;double Best=-1.;
        for(double Y=L.Center.Y-24000.;Y<L.Center.Y+24000.;Y+=1600.)
        for(double X=L.Center.X-24000.;X<L.Center.X+24000.;X+=1600.)
        {
            if(!Map.Bounds.IsInside(FVector2D(X,Y))||FMath::Abs(X)>Map.Bounds.Max.X-11000.||FMath::Abs(Y)>Map.Bounds.Max.Y-11000.||
                Map.Village.Clears(X,Y,3000.)||L.Edge(X,Y)<6500.)continue;
            const auto S=Map.River->Sample(X,Y);if(S.Bank>.02||S.CliffWeight>.05)continue;
            if(Map.Water&&Map.Water->Sample(X,Y).Wet)continue;
            const double Score=TemperateForestGroves::Sample(X,Y,Map.Seed).Cover*Map.River->RainforestWeight(X,Y);
            if(Score>Best){Best=Score;Grove=FVector2D(X,Y);}
        }
        TArray<FTemperatePlacement> Trees;
        Hills->GetPlacements(0,FBox(FVector(Grove-FVector2D(3500.),-100000.),FVector(Grove+FVector2D(3500.),100000.)),Trees);
        double Near=DBL_MAX;
        for(const auto& P:Trees){const FVector2D XY(P.Transform.GetLocation());const double D=FVector2D::DistSquared(XY,Grove);if(D<Near){Near=D;Beach=XY;}}
        if(!Trees.IsEmpty())Grove=Beach;
        Shots.Add({TEXT("05_tree_groves"),Ground(Grove+FVector2D(-6600.,-4400.),5900.),Ground(Grove,500.),80.f});
        Shots.Add({TEXT("06_forest_floor"),Ground(Grove+FVector2D(-850.,-450.),175.),Ground(Grove+FVector2D(150.,180.),55.),75.f});
        const auto& Q=Map.River->WhiteCliffs;
        if(Q.Valid)Shots.Add({TEXT("07_white_cliffs_quarry"),Ground(Q.World(-7600.,-6400.),3800.),FVector(Q.Center,Q.FloorZ+800.),80.f});
        if(Map.Village.bPlaced)
        {
            const auto P=Map.Village.Approach(-1.,4500.,Map.Seed);
            Shots.Add({TEXT("08_village_approach"),Ground(P+FVector2D(-Map.Village.Axis.Y,Map.Village.Axis.X)*2200.,1200.),Ground(Map.Village.Mouth(-1.),150.),75.f});
        }
        Result->SetArrayField(TEXT("lake_center"),Array(Target));
        Result->SetArrayField(TEXT("village_origin"),Array(Map.Village.Ground));
        Result->SetArrayField(TEXT("quarry_center"),Array(FVector(Q.Center,Q.FloorZ)));
        Result->SetBoolField(TEXT("natural_shore"),L.bNaturalShore);
        Result->SetNumberField(TEXT("grove_candidate_trees"),Trees.Num());
        if(!Input.IsEmpty())
        {
            FString Text;TSharedPtr<FJsonObject> J;
            if(FFileHelper::LoadFileToString(Text,*Input)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),J))
            {
                for(const auto& V:J->GetArrayField(TEXT("shots")))
                {
                    const auto S=V->AsObject();
                    FShot Shot{S->GetStringField(TEXT("name")),Vector(S->GetArrayField(TEXT("eye"))),Vector(S->GetArrayField(TEXT("target"))),float(S->GetNumberField(TEXT("fov")))};
                    if(auto* Existing=Shots.FindByPredicate([&](const FShot& P){return P.Name==Shot.Name;}))*Existing=Shot;
                    else Shots.Add(Shot);
                }
                const TArray<TSharedPtr<FJsonValue>>* Only=nullptr;
                if(J->TryGetArrayField(TEXT("only"),Only)&&!Only->IsEmpty())
                    Shots.RemoveAll([&](const FShot& S)
                    {return !Only->ContainsByPredicate([&](const TSharedPtr<FJsonValue>& V){return V->AsString()==S.Name;});});
            }
        }
        TArray<TSharedPtr<FJsonValue>> Plan;
        for(const auto& S:Shots){auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("name"),S.Name);J->SetArrayField(TEXT("eye"),Array(S.Eye));J->SetArrayField(TEXT("target"),Array(S.Target));J->SetNumberField(TEXT("fov"),S.FOV);Plan.Add(MakeShared<FJsonValueObject>(J));}
        auto J=MakeShared<FJsonObject>();J->SetArrayField(TEXT("shots"),Plan);
        FString Text;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Out/TEXT("cameras.json")));
    }

    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();
        auto* W=World.Get();if(!W)return false;
        if(!Viewport.IsValid())
        {
            Viewport=W->GetGameViewport();
            if(Viewport.IsValid())
            {OriginalRenderingDisabled=Viewport->bDisableWorldRendering;Viewport->bDisableWorldRendering=true;}
        }
        if(Now-Started>5400.)return Finish(TEXT("capture timeout"),false);
        auto* PC=W->GetFirstPlayerController();auto* C=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
        if(!C)return true;
        if(Stage==0)
        {
            if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
            if(!Hills.IsValid()||!Hills->bReady||PC->IsMoveInputIgnored())return true;
            TemperateHillsGround::FMapSource Map;Hills->CopyMapGround(Map);
            if(!Map.River||!Map.River->Lake.Valid)return Finish(TEXT("current saved world has no terminal lake"),false);
            Result->SetNumberField(TEXT("seed"),Hills->Seed);Result->SetNumberField(TEXT("generator_version"),Hills->GeneratorVersion);
            Result->SetStringField(TEXT("world_id"),Hills->WorldId.ToString());
            Result->SetStringField(TEXT("lighting"),TEXT("isolated clear weather, morning daylight"));
            Compose(Map);
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
            {It->SetWeatherState(EFPSWeatherState::Clear);It->RealSecondsPerGameDay=864000.f;It->AdvanceGameTime(FMath::Fmod(10.5f-It->NormalizedDayTime*24.f+24.f,24.f)+.0001f);}
            C->SetCanBeDamaged(false);C->SetActorEnableCollision(false);C->SetActorHiddenInGame(true);
            C->GetCharacterMovement()->StopMovementImmediately();C->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
            // An aerial review camera must not move the PCG generation source
            // hundreds of metres above the ground-level streaming anchor.
            if(auto* PCG=W->GetSubsystem<UPCGSubsystem>())if(auto* Sources=PCG->GetGenSourceManager())
            {auto* Source=NewObject<UTemperateHillsCaptureSource>(Hills.Get());Source->Controller=PC;if(Sources->RegisterGenSource(Source))GroundSource=Source;}
            Camera=W->SpawnActor<ACameraActor>();PC->SetViewTarget(Camera.Get());Stage=1;
        }
        if(Stage==1)
        {
            if(Index>=Shots.Num())return Finish(TEXT("rendered screenshots saved; visual assessment is separate"),true);
            const auto& S=Shots[Index];
            // Ground-level streaming anchor under the camera, even for aerial views.
            C->SetActorLocation(FVector(S.Eye.X,S.Eye.Y,Hills->Height(S.Eye.X,S.Eye.Y)+200.),false,nullptr,ETeleportType::TeleportPhysics);
            Camera->SetActorLocationAndRotation(S.Eye,(S.Target-S.Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(S.FOV);
            PC->SetViewTarget(Camera.Get());StageAt=LastChange=Now;Instances=-1;NextPoll=Now;ReadySince=0.;NextStatus=0.;Stage=2;
            // Generation is frame-budgeted. Avoid spending those frames drawing
            // an incomplete forest; restore full rendering before warm-up/capture.
            if(Viewport.IsValid())Viewport->bDisableWorldRendering=true;
            RenderWarmSince=0.;
            UE_LOG(LogTemp,Display,TEXT("HILLS_LANDSCAPE_VIEW %s eye=%s target=%s"),*S.Name,*S.Eye.ToString(),*S.Target.ToString());
        }
        if(Stage==2&&Now>=NextPoll)
        {
            NextPoll=Now+1.;int32 Count=0;
            for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
                if(It->GetWorld()==W&&It->IsRegistered()&&FVector::Dist2D(It->Bounds.Origin,C->GetActorLocation())<18000.)Count+=It->GetInstanceCount();
            if(Count!=Instances){Instances=Count;LastChange=Now;}
            const auto Ready=Readiness(Hills.Get(),C->GetActorLocation(),Shots[Index].Target);
            if(Ready.Complete()) {if(ReadySince==0.)ReadySince=Now;} else ReadySince=0.;
            if(Now>=NextStatus)
            {
                NextStatus=Now+10.;
                UE_LOG(LogTemp,Display,TEXT("HILLS_CAPTURE_WAIT view=%s terrain=%d/%d vegetation=%d/%d height_error_cm=%.2f pawn=%s"),
                    *Shots[Index].Name,Ready.TerrainReady,Ready.TerrainRequired,Ready.VegetationReady,Ready.VegetationRequired,Ready.MaxGroundError,*C->GetActorLocation().ToString());
            }
            if(Now-StageAt>900.&&!Ready.Complete())return Finish(TEXT("target ground or visible vegetation did not finish; no incomplete frame accepted"),false);
            if(Now-StageAt<20.||ReadySince==0.||Now-ReadySince<8.||Now-LastChange<5.)return true;
            if(RenderWarmSince==0.)
            {
                if(Viewport.IsValid())Viewport->bDisableWorldRendering=false;
                RenderWarmSince=Now;RenderWarmFrame=GFrameCounter;return true;
            }
            if(Now-RenderWarmSince<12.||GFrameCounter-RenderWarmFrame<40)return true;
            const auto& S=Shots[Index];Pending=Out/(S.Name+TEXT(".png"));
            auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("name"),S.Name);J->SetStringField(TEXT("file"),Pending);
            J->SetArrayField(TEXT("eye"),Array(S.Eye));J->SetArrayField(TEXT("target"),Array(S.Target));J->SetNumberField(TEXT("fov"),S.FOV);
            J->SetNumberField(TEXT("settle_seconds"),Now-StageAt);J->SetNumberField(TEXT("nearby_static_instances"),Instances);
            J->SetBoolField(TEXT("instance_count_stable"),Now-LastChange>=5.);Records.Add(MakeShared<FJsonValueObject>(J));
            J->SetNumberField(TEXT("terrain_ready"),Ready.TerrainReady);J->SetNumberField(TEXT("terrain_required"),Ready.TerrainRequired);
            J->SetNumberField(TEXT("vegetation_ready"),Ready.VegetationReady);J->SetNumberField(TEXT("vegetation_required"),Ready.VegetationRequired);
            J->SetNumberField(TEXT("ground_height_error_cm"),Ready.MaxGroundError);J->SetArrayField(TEXT("pawn"),Array(C->GetActorLocation()));
            J->SetNumberField(TEXT("render_warm_frames"),double(GFrameCounter-RenderWarmFrame));
            if(S.Name.Contains(TEXT("quarry")))
            {
                TemperateHillsGround::FMapSource Map;Hills->CopyMapGround(Map);
                TArray<TSharedPtr<FJsonValue>> Contacts;TInlineComponentArray<UInstancedStaticMeshComponent*> Parts(Hills.Get());
                for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("HillsWhiteCliffs")))
                for(int32 I=0;I<Part->GetInstanceCount();++I)
                {
                    FTransform T;Part->GetInstanceTransform(I,T,true);UStaticMesh* Mesh=Part->GetStaticMesh();if(!Mesh)continue;
                    FBox B=Mesh->GetBoundingBox();B.Min+=Mesh->GetNegativeBoundsExtension();B.Max-=Mesh->GetPositiveBoundsExtension();
                    const FVector Bottom=T.TransformPosition(FVector(B.GetCenter().X,B.GetCenter().Y,B.Min.Z));
                    auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("mesh"),Mesh->GetName());P->SetArrayField(TEXT("bottom"),Array(Bottom));
                    P->SetNumberField(TEXT("field_gap_cm"),Bottom.Z-Hills->Height(Bottom.X,Bottom.Y));
                    FHitResult Hit;const bool Traced=GroundHit(Hills.Get(),FVector2D(Bottom),Hit);P->SetBoolField(TEXT("ground_traced"),Traced);
                    if(Traced)P->SetNumberField(TEXT("visible_ground_gap_cm"),Bottom.Z-Hit.ImpactPoint.Z);
                    P->SetNumberField(TEXT("proxy_gap_cm"),Bottom.Z-TemperateBackdrop::CoreTriangleHeight(Bottom.X,Bottom.Y,Hills->SizeMeters*50.,Hills->Seed,Map.River,Hills->GeneratorVersion,Map.Village));
                    Contacts.Add(MakeShared<FJsonValueObject>(P));
                }
                J->SetArrayField(TEXT("quarry_contacts"),Contacts);
            }
            FScreenshotRequest::RequestScreenshot(Pending,false,false);StageAt=Now;Stage=3;
        }
        if(Stage==3)
        {
            if(Now-StageAt>30.)return Finish(TEXT("screenshot was not written"),false);
            if(Now-StageAt>1.&&IFileManager::Get().FileSize(*Pending)>0)
            {UE_LOG(LogTemp,Display,TEXT("HILLS_LANDSCAPE_SAVED %s"),*Pending);++Index;Stage=1;}
        }
        return true;
    }
};

FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.HillsLandscapeCapture"),TEXT("Opt-in isolated landscape screenshot capture."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("HillsLandscapeCapture")))return;
        auto C=MakeShared<FCapture>();C->World=W;
        if(!FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeOutput="),C->Out)||C->Out.IsEmpty())return;
        FParse::Value(FCommandLine::Get(),TEXT("HillsLandscapeInput="),C->Input);
        IFileManager::Get().MakeDirectory(*C->Out,true);
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([C](float Dt){return C->Tick(Dt);}));
    }));
}
#endif
