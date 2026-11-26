#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "TemperateHillsGroundLayers.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraActor.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
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

namespace VillageRuntimeReview
{
FVector Vector(const TArray<TSharedPtr<FJsonValue>>& A)
{return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());}
TArray<TSharedPtr<FJsonValue>> Array(const FVector& P)
{return {MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)};}

struct FReview
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<AFPSGAMECharacter> Player;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<ACameraActor> Camera;
    TSharedPtr<FJsonObject> Input,Result=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> WallResults,RouteResults;
    FTransform Site;
    FString Out;
    double Started=FPlatformTime::Seconds(),StageAt=Started,LastProgress=Started,NextLog=0,NextCapture=0;
    int32 Stage=0,Route=0,Point=0,Capture=0,Errors=0;
    FVector Previous;
    double Walked=0,BestDistance=DBL_MAX;
    int32 WalkFrames=0;
    bool bWalkAirborne=false,bWalkCrouched=false;
    TArray<FVector> Waypoints;

    bool Finish(const FString& Reason)
    {
        if(auto* C=Player.Get())C->GetCharacterMovement()->StopMovementImmediately();
        Result->SetStringField(TEXT("reason"),Reason);
        Result->SetBoolField(TEXT("pass"),Errors==0);
        Result->SetNumberField(TEXT("errors"),Errors);
        Result->SetNumberField(TEXT("elapsed_s"),FPlatformTime::Seconds()-Started);
        Result->SetArrayField(TEXT("walls"),WallResults);
        Result->SetArrayField(TEXT("routes"),RouteResults);
        FString Json;FJsonSerializer::Serialize(Result.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_RUNTIME_RESULT pass=%d walls=%d routes=%d errors=%d reason=%s"),Errors==0,WallResults.Num(),RouteResults.Num(),Errors,*Reason);
        // Drain the streamed hills scene while the engine is still running,
        // separating world cleanup from shutdown of global rendering services.
        const uint8 Status=Errors?1:0;
        UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        const double ExitAt=FPlatformTime::Seconds()+8.;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Status,ExitAt](float)
        {
            if(FPlatformTime::Seconds()<ExitAt)return true;
            UE_LOG(LogTemp,Display,TEXT("VILLAGE_RUNTIME_EXIT_AFTER_WORLD_DRAIN"));
            FPlatformMisc::RequestExitWithStatus(false,Status);return false;
        }));
        return false;
    }

    bool TerrainAt(const FVector& P,FHitResult& Hit) const
    {
        TInlineComponentArray<UDynamicMeshComponent*> Components(Hills.Get());
        FCollisionQueryParams Q(SCENE_QUERY_STAT(VillageReviewTerrain),true);
        for(auto* C:Components)
        {
            if(!C->IsRegistered()||C->GetCollisionEnabled()==ECollisionEnabled::NoCollision)continue;
            if(C->LineTraceComponent(Hit,P+FVector(0,0,300),P-FVector(0,0,300),Q))return true;
        }
        return false;
    }

    bool Walls()
    {
        TArray<UInstancedStaticMeshComponent*> Components;
        int32 LiveCount=0;
        for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
        {
            if(It->GetWorld()!=World.Get()||!It->IsRegistered()||!It->GetStaticMesh())continue;
            if(!It->GetStaticMesh()->GetName().StartsWith(TEXT("SM_H_StoneWall_00A_Piece")))continue;
            Components.Add(*It);
            for(int32 I=0;I<It->GetInstanceCount();++I)
            {FTransform T;It->GetInstanceTransform(I,T,true);if(T.GetScale3D().Equals(FVector(.8),.001))++LiveCount;}
        }
        if(LiveCount<154)return false;
        const auto& Expected=Input->GetArrayField(TEXT("walls"));
        TArray<TSharedPtr<FJsonValue>> Rows;
        int32 Pending=0,Failures=0,Traced=0;
        for(const auto& V:Expected)
        {
            const auto J=V->AsObject();
            const auto R=Vector(J->GetArrayField(TEXT("rot")));
            FTransform Local(FRotator(R.X,R.Y,R.Z),Vector(J->GetArrayField(TEXT("pos"))),Vector(J->GetArrayField(TEXT("scale"))));
            FTransform ExpectedWorld=Local*Site,Actual;
            double Nearest=DBL_MAX;
            UInstancedStaticMeshComponent* Match=nullptr;
            for(auto* C:Components)if(C->GetStaticMesh()->GetPathName()==J->GetStringField(TEXT("mesh")))
                for(int32 I=0;I<C->GetInstanceCount();++I)
                {
                    FTransform T;C->GetInstanceTransform(I,T,true);
                    const double D=FVector::Dist(T.GetLocation(),ExpectedWorld.GetLocation());
                    if(D<Nearest){Nearest=D;Actual=T;Match=C;}
                }
            const bool Pose=Match&&Actual.Equals(ExpectedWorld,.1);
            double Gap=0,Intrusion=0,FormulaError=0;
            int32 Samples=0,Missing=0;
            if(Pose)for(const auto& Contact:J->GetArrayField(TEXT("contacts")))
            {
                const FVector Q=Actual.TransformPosition(Local.InverseTransformPosition(Vector(Contact->AsArray())));
                FHitResult Hit;
                if(!TerrainAt(Q,Hit)){++Missing;continue;}
                ++Samples;++Traced;
                Gap=FMath::Max(Gap,Q.Z-Hit.ImpactPoint.Z);
                Intrusion=FMath::Max(Intrusion,Hit.ImpactPoint.Z-Q.Z);
                FormulaError=FMath::Max(FormulaError,FMath::Abs(Hit.ImpactPoint.Z-Hills->Height(Q.X,Q.Y)));
            }
            if(Missing)++Pending;
            const bool Pass=Pose&&!Missing&&Gap<=1.&&Intrusion<=1.&&FormulaError<=1.;
            if(!Pass)++Failures;
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("index"),J->GetNumberField(TEXT("index")));
            Row->SetBoolField(TEXT("pass"),Pass);Row->SetBoolField(TEXT("runtime_transform_matches_saved"),Pose);
            Row->SetNumberField(TEXT("support_samples"),Samples);Row->SetNumberField(TEXT("missing_terrain_samples"),Missing);
            Row->SetNumberField(TEXT("max_ground_gap_cm"),Gap);Row->SetNumberField(TEXT("max_extra_burial_cm"),Intrusion);
            Row->SetNumberField(TEXT("collision_vs_height_error_cm"),FormulaError);
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        if(Pending&&FPlatformTime::Seconds()-StageAt<90)return false;
        WallResults=MoveTemp(Rows);Errors+=Failures;
        if(LiveCount!=154)++Errors;
        Result->SetNumberField(TEXT("live_boundary_wall_count"),LiveCount);
        Result->SetNumberField(TEXT("terrain_collision_samples"),Traced);
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_RUNTIME_WALLS seed=%d count=%d traced=%d fail=%d pending=%d"),Hills->Seed,LiveCount,Traced,Failures,Pending);
        return true;
    }

    void RecordRoute(bool Pass,const FString& Why)
    {
        auto* C=Player.Get();auto* M=C->GetCharacterMovement();
        const auto R=Input->GetArrayField(TEXT("routes"))[Route]->AsObject();
        auto Row=MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("name"),R->GetStringField(TEXT("name")));
        Row->SetBoolField(TEXT("pass"),Pass);Row->SetStringField(TEXT("reason"),Why);
        Row->SetArrayField(TEXT("end_position"),Array(C->GetActorLocation()));
        Row->SetNumberField(TEXT("walked_cm"),Walked);Row->SetNumberField(TEXT("frames"),WalkFrames);
        Row->SetBoolField(TEXT("crouched"),bWalkCrouched);Row->SetBoolField(TEXT("airborne"),bWalkAirborne);
        Row->SetNumberField(TEXT("capsule_radius_cm"),C->GetCapsuleComponent()->GetScaledCapsuleRadius());
        Row->SetNumberField(TEXT("capsule_half_height_cm"),C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        if(!Pass)
        {
            ++Errors;FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(VillageReviewBlock),false,C);
            const FVector D=(Waypoints[FMath::Clamp(Point,0,Waypoints.Num()-1)]-C->GetActorLocation()).GetSafeNormal2D();
            World->SweepSingleByChannel(Hit,C->GetActorLocation(),C->GetActorLocation()+D*100,FQuat::Identity,ECC_Pawn,C->GetCapsuleComponent()->GetCollisionShape(),Q);
            Row->SetStringField(TEXT("blocking_component"),GetPathNameSafe(Hit.GetComponent()));
            Row->SetNumberField(TEXT("blocking_instance"),Hit.Item);
            FScreenshotRequest::RequestScreenshot(Out/(R->GetStringField(TEXT("name"))+TEXT("_failed.png")),false,false);
        }
        RouteResults.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("VILLAGE_RUNTIME_ROUTE seed=%d route=%s pass=%d walked_cm=%.1f reason=%s"),Hills->Seed,*R->GetStringField(TEXT("name")),Pass,Walked,*Why);
        M->StopMovementImmediately();++Route;Stage=2;StageAt=FPlatformTime::Seconds();
    }

    bool Tick(float Dt)
    {
        const double Now=FPlatformTime::Seconds();
        auto* W=World.Get();if(!W){++Errors;return Finish(TEXT("world lost"));}
        if(Now-Started>900){++Errors;return Finish(TEXT("runtime review timeout"));}
        auto* PC=W->GetFirstPlayerController();
        if(!Player.IsValid()&&PC)Player=Cast<AFPSGAMECharacter>(PC->GetPawn());
        if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
        if(!Player.IsValid()||!Hills.IsValid()||!PC)return true;
        auto* C=Player.Get();auto* M=C->GetCharacterMovement();
        if(Now>NextLog)
        {NextLog=Now+15;UE_LOG(LogTemp,Display,TEXT("VILLAGE_RUNTIME_PROGRESS seed=%d stage=%d route=%d point=%d ready=%d pos=%s"),Hills->Seed,Stage,Route,Point,Hills->bReady,*C->GetActorLocation().ToCompactString());}
        if(Stage==0)
        {
            if(!Hills->bReady||PC->IsMoveInputIgnored())return true;
            TemperateHillsGround::FMapSource Map;Hills->CopyMapGround(Map);
            if(!Map.Village.bPlaced){++Errors;return Finish(TEXT("no village placed"));}
            Site=FTransform(FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Map.Village.Axis.Y,Map.Village.Axis.X)),0),Map.Village.Ground);
            Result->SetNumberField(TEXT("seed"),Hills->Seed);Result->SetNumberField(TEXT("generator_version"),Hills->GeneratorVersion);
            Result->SetStringField(TEXT("map"),W->GetMapName());Result->SetArrayField(TEXT("village_origin"),Array(Site.GetLocation()));
            Result->SetNumberField(TEXT("village_yaw"),Site.Rotator().Yaw);
            Result->SetBoolField(TEXT("side_lane"),Map.Village.bSideLane);
            C->SetCanBeDamaged(false);C->UnCrouch();
            Hills->RequestVillageVisit();Stage=1;StageAt=Now;return true;
        }
        if(Stage==1)
        {
            if(Now-StageAt<5||PC->IsMoveInputIgnored()||FVector::Dist2D(C->GetActorLocation(),Site.GetLocation())>7000)return true;
            if(!Walls())return true;
            Stage=2;StageAt=Now;return true;
        }
        if(Stage==2)
        {
            if(Route>=Input->GetArrayField(TEXT("routes")).Num())
            {
                Camera=W->SpawnActor<ACameraActor>();PC->SetViewTarget(Camera.Get());Stage=4;StageAt=Now;return true;
            }
            const auto R=Input->GetArrayField(TEXT("routes"))[Route]->AsObject();Waypoints.Reset();
            for(const auto& P:R->GetArrayField(TEXT("points")))Waypoints.Add(Site.TransformPosition(Vector(P->AsArray())));
            FHitResult Hit;const FVector P=Waypoints[0];FCollisionQueryParams Q(SCENE_QUERY_STAT(VillageReviewStart),false,C);
            if(!W->LineTraceSingleByChannel(Hit,P+FVector(0,0,220),P-FVector(0,0,100),ECC_Visibility,Q))
            {if(Now-StageAt<20)return true;Point=0;RecordRoute(false,TEXT("route start has no ground"));return true;}
            const FVector Start=Hit.ImpactPoint+FVector(0,0,C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.5);
            C->SetActorLocation(Start,false,nullptr,ETeleportType::TeleportPhysics);M->StopMovementImmediately();
            M->SetMovementMode(MOVE_Walking);M->bForceNextFloorCheck=true;
            PC->SetControlRotation((Waypoints[1]-Waypoints[0]).Rotation());
            Point=1;Walked=0;WalkFrames=0;bWalkAirborne=false;bWalkCrouched=false;Previous=Start;BestDistance=DBL_MAX;LastProgress=Now;
            Stage=3;StageAt=Now;return true;
        }
        if(Stage==3)
        {
            const FVector P=C->GetActorLocation();const double Distance=FVector::Dist2D(P,Waypoints[Point]);
            Walked+=FVector::Dist2D(P,Previous);Previous=P;++WalkFrames;
            bWalkCrouched|=C->bIsCrouched;
            if(Now-StageAt>.5)bWalkAirborne|=!M->IsMovingOnGround();
            if(Distance<18)
            {
                ++Point;BestDistance=DBL_MAX;LastProgress=Now;
                if(Point>=Waypoints.Num()){RecordRoute(!bWalkCrouched&&!bWalkAirborne,TEXT("standing walk completed"));return true;}
            }
            else if(Distance<BestDistance-3){BestDistance=Distance;LastProgress=Now;}
            if(Now-LastProgress>6){RecordRoute(false,TEXT("walking blocked for six seconds"));return true;}
            const FVector D=(Waypoints[Point]-P).GetSafeNormal2D();
            C->AddMovementInput(D,1,true);PC->SetControlRotation(D.Rotation());
            const auto R=Input->GetArrayField(TEXT("routes"))[Route]->AsObject();
            if(R->GetStringField(TEXT("kind"))==TEXT("door")&&Point==3&&Now>NextCapture)
            {NextCapture=Now+2;FScreenshotRequest::RequestScreenshot(Out/(R->GetStringField(TEXT("name"))+TEXT("_inside.png")),false,false);}
            return true;
        }
        if(Stage==4)
        {
            const auto& Indices=Input->GetArrayField(TEXT("capture_wall_indices"));
            if(Capture>=Indices.Num()*2)return Finish(TEXT("real terrain contacts, bidirectional roads, standing door entry/exit and screenshots complete"));
            const int32 Index=int32(Indices[Capture/2]->AsNumber());
            const auto J=Input->GetArrayField(TEXT("walls"))[Index]->AsObject();
            const FVector P=Site.TransformPosition(Vector(J->GetArrayField(TEXT("pos"))));
            const double Yaw=J->GetArrayField(TEXT("rot"))[1]->AsNumber()+Site.Rotator().Yaw;
            const FVector Side=FRotator(0,Yaw,0).RotateVector(FVector(0,Capture%2?-1:1,0));
            const FVector Target(P.X,P.Y,Site.GetLocation().Z+48),Eye=Target+Side*270+FVector(0,0,95);
            Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());
            NextCapture=Now+2;Stage=5;return true;
        }
        if(Stage==5&&Now>=NextCapture)
        {
            const int32 Index=int32(Input->GetArrayField(TEXT("capture_wall_indices"))[Capture/2]->AsNumber());
            FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("wall_%03d_%s.png"),Index,Capture%2?TEXT("b"):TEXT("a")),false,false);
            ++Capture;Stage=6;NextCapture=Now+.4;return true;
        }
        if(Stage==6&&Now>=NextCapture)Stage=4;
        return true;
    }
};

FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.VillageRuntimeReview"),TEXT("Opt-in isolated seeded village ground and standing passage review."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("VillageRuntimeReview")))return;
        auto Review=MakeShared<FReview>();Review->World=W;
        FString InputPath;
        FParse::Value(FCommandLine::Get(),TEXT("VillageReviewInput="),InputPath);
        FParse::Value(FCommandLine::Get(),TEXT("VillageReviewOutput="),Review->Out);
        IFileManager::Get().MakeDirectory(*Review->Out,true);
        FString Text;
        if(!FFileHelper::LoadFileToString(Text,*InputPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Review->Input))
        {++Review->Errors;Review->Finish(TEXT("review input missing"));return;}
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Review](float Dt){return Review->Tick(Dt);}));
    }));
}
#endif
