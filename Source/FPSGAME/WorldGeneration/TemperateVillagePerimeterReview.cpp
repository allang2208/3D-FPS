#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "../FPSWeatherManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/DynamicMeshComponent.h"
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
#include "UObject/UnrealType.h"
#include "UnrealClient.h"

namespace VillagePerimeterReview
{
struct FShot { FString Name;FVector Eye,Target; };
struct FReview
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<ACameraActor> Camera;
    TSharedPtr<FJsonObject> Result=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Audits;
    TArray<FShot> Shots;
    FString Out;
    double Started=FPlatformTime::Seconds(),StageAt=Started,NextLog=0.;
    int32 Stage=0,Shot=0,Style=0,Errors=0;

    bool Finish(const FString& Why)
    {
        Result->SetBoolField(TEXT("pass"),Errors==0);Result->SetStringField(TEXT("reason"),Why);
        Result->SetArrayField(TEXT("styles"),Audits);Result->SetNumberField(TEXT("elapsed_s"),FPlatformTime::Seconds()-Started);
        FString Json;FJsonSerializer::Serialize(Result.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("PERIMETER_REVIEW_RESULT pass=%d errors=%d reason=%s"),Errors==0,Errors,*Why);
        if(World.IsValid())UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        const uint8 Status=Errors?1:0;const double ExitAt=FPlatformTime::Seconds()+8.;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Status,ExitAt](float)
        {if(FPlatformTime::Seconds()<ExitAt)return true;FPlatformMisc::RequestExitWithStatus(false,Status);return false;}));
        return false;
    }
    TArray<UInstancedStaticMeshComponent*> Parts() const
    {
        TArray<UInstancedStaticMeshComponent*> Found;
        TInlineComponentArray<UInstancedStaticMeshComponent*> Components(Hills.Get());
        for(auto* C:Components)if(C->ComponentHasTag(TEXT("HillsVillagePerimeter"))&&C->GetStaticMesh())Found.Add(C);
        return Found;
    }
    FVector At(double X,double Y,double Z=0.) const
    {const auto P=Hills->GetVillageSite().World(X,Y);return FVector(P,Hills->Height(P.X,P.Y)+Z);}

    void MakeShots()
    {
        const auto& V=Hills->GetVillageSite();const double X=V.PadHalfX-500.,Y=V.PadHalfY-500.;
        FTransform Detail;double Best=DBL_MAX;
        for(auto* C:Parts())
        {
            if(!C->GetStaticMesh()->GetName().StartsWith(TEXT("SM_VillageWallRuined")))continue;
            for(int32 I=0;I<C->GetInstanceCount();++I)
            {
                FTransform T;C->GetInstanceTransform(I,T,true);
                const double D=FVector::DistSquared2D(T.GetLocation(),At(-X,-1500));
                if(D<Best){Best=D;Detail=T;}
            }
        }
        if(Best==DBL_MAX){++Errors;return;}
        const FVector P=Detail.GetLocation(),Outward=-Detail.GetUnitAxis(EAxis::Y),Along=Detail.GetUnitAxis(EAxis::X);
        const FVector Target=V.Ground+FVector(0,0,350);
        Shots.Add({TEXT("overview"),Target+FVector(10000,-13000,13000),Target});
        Shots.Add({TEXT("wall-detail"),P+Outward*350.+Along*150.+FVector(0,0,190),P+FVector(0,0,67)});
        Shots.Add({TEXT("ground-contact"),P+Outward*210.+Along*125.+FVector(0,0,48),P+Outward*24.+FVector(0,0,14)});
        Shots.Add({TEXT("west-gate"),At(-X-1000,750,320),At(-X,0,75)});
        Shots.Add({TEXT("east-gate"),At(X+1000,-250,320),At(X,500,75)});
        Shots.Add({TEXT("corner"),At(-X-350,-Y+300,160),At(-X,-Y+600,65)});
    }

    void Audit()
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("style"),Style?TEXT("repaired"):TEXT("ruined"));
        int32 Instances=0,Samples=0,Missing=0,Decals=0,RubbleSamples=0;double MaxRootError=0.,MinBurial=DBL_MAX,MinRubbleBurial=DBL_MAX;
        TInlineComponentArray<UDynamicMeshComponent*> Terrain(Hills.Get());
        TArray<TSharedPtr<FJsonValue>> Meshes;
        for(auto* C:Parts())
        {
            Instances+=C->GetInstanceCount();if(C->bReceivesDecals)++Decals;
            auto M=MakeShared<FJsonObject>();M->SetStringField(TEXT("mesh"),C->GetStaticMesh()->GetPathName());
            M->SetNumberField(TEXT("instances"),C->GetInstanceCount());
            TArray<TSharedPtr<FJsonValue>> Materials;
            for(int32 K=0;K<C->GetNumMaterials();++K)Materials.Add(MakeShared<FJsonValueString>(GetPathNameSafe(C->GetMaterial(K))));
            M->SetArrayField(TEXT("materials"),Materials);Meshes.Add(MakeShared<FJsonValueObject>(M));
            const bool Rubble=C->GetCollisionEnabled()==ECollisionEnabled::NoCollision;
            const FBox Bounds=C->GetStaticMesh()->GetBoundingBox();
            for(int32 I=0;I<C->GetInstanceCount();++I)
            {
                FTransform T;C->GetInstanceTransform(I,T,true);
                for(double F:{.15,.5,.85})
                {
                    const FVector P=T.TransformPosition(FVector(FMath::Lerp(Bounds.Min.X,Bounds.Max.X,F),0,0));
                    FHitResult Hit;bool Found=false;
                    for(auto* Ground:Terrain)
                    {
                        if(!Ground->IsRegistered()||Ground->GetCollisionEnabled()==ECollisionEnabled::NoCollision)continue;
                        if(Ground->LineTraceComponent(Hit,P+FVector(0,0,120),P-FVector(0,0,120),FCollisionQueryParams(SCENE_QUERY_STAT(PerimeterGround),true)))
                        {Found=true;break;}
                    }
                    if(!Found){++Missing;continue;}
                    ++Samples;MaxRootError=FMath::Max(MaxRootError,FMath::Abs(P.Z-Hit.ImpactPoint.Z));
                    const double Burial=Hit.ImpactPoint.Z-T.TransformPosition(FVector(0,0,Bounds.Min.Z)).Z;
                    if(Rubble){++RubbleSamples;MinRubbleBurial=FMath::Min(MinRubbleBurial,Burial);}
                    else MinBurial=FMath::Min(MinBurial,Burial);
                }
            }
        }
        const auto& V=Hills->GetVillageSite();const double X=V.PadHalfX-500.;
        int32 GateBlocked=0;TArray<TSharedPtr<FJsonValue>> Gates;
        for(double Side:{-1.,1.})
        {
            const double Y=Side<0?0.:500.;TArray<FHitResult> Hits;
            World->SweepMultiByChannel(Hits,At(Side*X-220,Y,94),At(Side*X+220,Y,94),FQuat::Identity,
                ECC_Pawn,FCollisionShape::MakeCapsule(34,88),FCollisionQueryParams(SCENE_QUERY_STAT(PerimeterGate),false));
            bool Blocked=false;for(const auto& Hit:Hits)if(Hit.Component.IsValid()&&Hit.Component->ComponentHasTag(TEXT("HillsVillagePerimeter")))Blocked=true;
            GateBlocked+=Blocked;auto G=MakeShared<FJsonObject>();G->SetStringField(TEXT("gate"),Side<0?TEXT("west"):TEXT("east"));G->SetBoolField(TEXT("clear"),!Blocked);Gates.Add(MakeShared<FJsonValueObject>(G));
        }
        const bool Pass=Instances>100&&Samples>250&&Missing==0&&MaxRootError<3.&&MinBurial>20.&&Decals==0&&GateBlocked==0
            &&Meshes.Num()==(Style?3:7)&&(Style||(RubbleSamples>100&&MinRubbleBurial>2.));
        if(!Pass)++Errors;
        Row->SetBoolField(TEXT("pass"),Pass);Row->SetNumberField(TEXT("instances"),Instances);Row->SetNumberField(TEXT("terrain_contact_samples"),Samples);
        Row->SetNumberField(TEXT("missing_terrain_samples"),Missing);Row->SetNumberField(TEXT("max_root_to_actual_ground_cm"),MaxRootError);
        Row->SetNumberField(TEXT("minimum_mesh_base_burial_cm"),MinBurial==DBL_MAX?0:MinBurial);Row->SetNumberField(TEXT("receives_decals_components"),Decals);
        Row->SetNumberField(TEXT("rubble_contact_samples"),RubbleSamples);Row->SetNumberField(TEXT("minimum_rubble_base_burial_cm"),MinRubbleBurial==DBL_MAX?0:MinRubbleBurial);
        Row->SetArrayField(TEXT("gates"),Gates);Row->SetArrayField(TEXT("meshes"),Meshes);Audits.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp,Display,TEXT("PERIMETER_REVIEW_AUDIT style=%d pass=%d samples=%d missing=%d root_error=%.3f burial=%.3f gates_blocked=%d"),Style,Pass,Samples,Missing,MaxRootError,MinBurial,GateBlocked);
    }

    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();auto* W=World.Get();
        if(!W){++Errors;return Finish(TEXT("world unavailable"));}
        if(Now-Started>900.){++Errors;return Finish(TEXT("review timeout"));}
        auto* PC=W->GetFirstPlayerController();APawn* Pawn=PC?PC->GetPawn():nullptr;
        if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
        if(Now>NextLog){NextLog=Now+20.;UE_LOG(LogTemp,Display,TEXT("PERIMETER_REVIEW_PROGRESS stage=%d style=%d shot=%d"),Stage,Style,Shot);}
        if(!PC||!Pawn||!Hills.IsValid()||!Hills->bReady)return true;
        if(Stage==0)
        {
            Result->SetNumberField(TEXT("seed"),Hills->Seed);Result->SetBoolField(TEXT("initial_repaired"),Hills->IsVillageWallRepaired());
            if(Hills->IsVillageWallRepaired()||Parts().IsEmpty()){++Errors;return Finish(TEXT("expected a generated ruined perimeter"));}
            MakeShots();if(Shots.IsEmpty())return Finish(TEXT("detail station missing"));
            PC->ConsoleCommand(TEXT("r.SetRes 1920x1080w"));PC->ConsoleCommand(TEXT("r.ScreenPercentage 100"));
            PC->ConsoleCommand(TEXT("foliage.CullDistanceScale 3"));PC->ConsoleCommand(TEXT("r.ViewDistanceScale 3"));
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
            {It->SetWeatherState(EFPSWeatherState::Clear);It->RealSecondsPerGameDay=8640000.f;It->AdvanceGameTime(FMath::Fmod(.42f-It->NormalizedDayTime+1.f,1.f)*24.f+.00001f);}
            Pawn->SetActorLocation(Hills->GetVillageSite().Ground+FVector(0,0,110),false,nullptr,ETeleportType::TeleportPhysics);
            Pawn->SetCanBeDamaged(false);Pawn->SetActorHiddenInGame(true);
            if(auto* C=Cast<ACharacter>(Pawn))C->GetCharacterMovement()->DisableMovement();
            if(auto* VP=W->GetGameViewport())VP->RemoveAllViewportWidgets();
            Camera=W->SpawnActor<ACameraActor>();Camera->GetCameraComponent()->SetFieldOfView(70.f);PC->SetViewTarget(Camera.Get());
            Stage=1;
        }
        if(Stage==1)
        {
            if(Shot==Shots.Num())
            {
                Audit();
                if(Style==1)return Finish(TEXT("both perimeter layouts, actual terrain contacts, gate clearance and twelve captures complete"));
                // Presentation inspection only: no task completion or formal save mutation.
                auto* Property=FindFProperty<FBoolProperty>(Hills->GetClass(),TEXT("bVillageWallRepaired"));
                auto* Apply=Hills->FindFunction(TEXT("OnRep_VillageWall"));
                if(!Property||!Apply){++Errors;return Finish(TEXT("style preview unavailable"));}
                Property->SetPropertyValue_InContainer(Hills.Get(),true);Hills->ProcessEvent(Apply,nullptr);
                Style=1;Shot=0;Result->SetBoolField(TEXT("isolated_visual_state_override"),true);
            }
            const auto& S=Shots[Shot];Camera->SetActorLocationAndRotation(S.Eye,(S.Target-S.Eye).Rotation());
            PC->SetViewTarget(Camera.Get());Stage=2;StageAt=Now;return true;
        }
        if(Stage==2&&Now-StageAt>(Shot==0?40.:12.))
        {
            const FString Name=(Style?TEXT("repaired-"):TEXT("ruined-"))+Shots[Shot].Name+TEXT(".png");
            FScreenshotRequest::RequestScreenshot(Out/Name,false,false);
            UE_LOG(LogTemp,Display,TEXT("PERIMETER_REVIEW_CAPTURE %s"),*Name);Stage=3;StageAt=Now;
        }
        if(Stage==3&&Now-StageAt>2.){++Shot;Stage=1;}
        return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.VillagePerimeterReview"),TEXT("Opt-in isolated wall layout/detail/support inspection."),
FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{
    if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("VillagePerimeterReview")))return;
    auto R=MakeShared<FReview>();R->World=W;
    FParse::Value(FCommandLine::Get(),TEXT("VillagePerimeterOutput="),R->Out);if(R->Out.IsEmpty())return;
    IFileManager::Get().MakeDirectory(*R->Out,true);
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float Dt){return R->Tick(Dt);}));
}));
}
#endif
