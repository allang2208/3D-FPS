#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "HillsBlacksmith.h"
#include "../Building/ColdSteelWindow.h"
#include "../Building/BronzeTorch.h"
#include "Components/ChildActorComponent.h"
#include "Components/PointLightComponent.h"
#include "../Movement/FPSDoorPushComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "PhysicsEngine/BodySetup.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "UnrealClient.h"

namespace SmithLoftReview
{
FVector Vec(const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());}
TArray<TSharedPtr<FJsonValue>> Arr(const FVector& P){return {MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)};}
struct FReview
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AHillsBlacksmith> Shop;
    TWeakObjectPtr<AFPSGAMECharacter> Player;
    TWeakObjectPtr<ACameraActor> Camera;
    TSharedPtr<FJsonObject> Input,Result=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Routes,Shots,Trace;
    TArray<FVector> Points;
    FTransform House;
    FString Out;
    int32 Stage=0,Route=0,Point=0,Shot=0,Errors=0,Frames=0;
    double Started=FPlatformTime::Seconds(),At=Started,LastProgress=Started,NextLog=0,Best=DBL_MAX,Walked=0,MinFeet=DBL_MAX,MaxFeet=-DBL_MAX;
    bool Airborne=false,Crouched=false;
    FVector Previous;
    TArray<TWeakObjectPtr<AColdSteelWindow>> Windows;
    TArray<TSharedPtr<FJsonValue>> WindowResults;
    int32 WindowIndex=0,WindowStep=0;

    bool Finish(const FString& Why)
    {
        if(Player.IsValid())Player->GetCharacterMovement()->StopMovementImmediately();
        Result->SetBoolField(TEXT("pass"),Errors==0);Result->SetNumberField(TEXT("errors"),Errors);
        Result->SetStringField(TEXT("reason"),Why);Result->SetArrayField(TEXT("routes"),Routes);Result->SetArrayField(TEXT("captures"),Shots);
        Result->SetNumberField(TEXT("elapsed_s"),FPlatformTime::Seconds()-Started);
        FString Json;FJsonSerializer::Serialize(Result.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("SMITH_LOFT_RESULT pass=%d routes=%d captures=%d reason=%s"),Errors==0,Routes.Num(),Shots.Num(),*Why);
        const uint8 Status=Errors?1:0;
        UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        const double ExitAt=FPlatformTime::Seconds()+8;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Status,ExitAt](float)
        {if(FPlatformTime::Seconds()<ExitAt)return true;FPlatformMisc::RequestExitWithStatus(false,Status);return false;}));
        return false;
    }

    bool Terrain(const FVector& P,FHitResult& Hit)
    {
        TInlineComponentArray<UDynamicMeshComponent*> Parts(Hills.Get());
        for(auto* C:Parts)if(C->IsRegistered()&&C->GetCollisionEnabled()!=ECollisionEnabled::NoCollision)
            if(C->LineTraceComponent(Hit,P+FVector(0,0,160),P-FVector(0,0,160),FCollisionQueryParams(SCENE_QUERY_STAT(SmithSupport),true)))return true;
        return false;
    }

    void InspectStructure()
    {
        int32 RepairVisible=0,RuinVisible=0;
        TArray<TSharedPtr<FJsonValue>> Parts;
        FBox Pad(ForceInit),Shaft(ForceInit);
        for(const auto& A:Shop->ShopAssemblies)if(IsValid(A.Get()))
        {
            TInlineComponentArray<UInstancedStaticMeshComponent*> Comps(A.Get());
            for(auto* C:Comps)
            {
                RepairVisible+=C->ComponentHasTag(TEXT("VillageShop.Repaired"))&&C->IsVisible();
                RuinVisible+=C->ComponentHasTag(TEXT("VillageShop.Ruined"))&&C->IsVisible();
                if(!C->IsVisible()||!C->GetStaticMesh())continue;
                const FString Name=C->GetStaticMesh()->GetName();
                for(int32 I=0;I<C->GetInstanceCount();++I)
                {
                    FTransform T;C->GetInstanceTransform(I,T,true);
                    if(Name.StartsWith(TEXT("SM_SmithLoft_"))||Name==TEXT("SM_VillageTimberBed"))
                    {
                        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("mesh"),Name);
                        Row->SetArrayField(TEXT("house_local_position"),Arr(House.InverseTransformPosition(T.GetLocation())));
                        Row->SetArrayField(TEXT("scale"),Arr(T.GetScale3D()));Parts.Add(MakeShared<FJsonValueObject>(Row));
                    }
                    if(Name.StartsWith(TEXT("SM_SmithLoft_Chimney")))Shaft=C->GetStaticMesh()->GetBoundingBox().TransformBy(T);
                    if(Name.StartsWith(TEXT("SM_SmithLoft_Apron")))
                    {
                        const auto* Body=C->GetStaticMesh()->GetBodySetup();
                        if(Body&&Body->AggGeom.BoxElems.IsValidIndex(4))
                        {
                            const auto& B=Body->AggGeom.BoxElems[4];const FVector Half(B.X*.5,B.Y*.5,B.Z*.5);
                            Pad=FBox(-Half,Half).TransformBy(FTransform(B.Rotation,B.Center)*T);
                        }
                    }
                }
            }
        }
        Result->SetNumberField(TEXT("visible_repaired_groups"),RepairVisible);Result->SetNumberField(TEXT("visible_ruined_groups"),RuinVisible);
        Result->SetArrayField(TEXT("structure"),Parts);
        FHitResult Ground;const bool Contact=Pad.IsValid&&Shaft.IsValid&&Terrain(Pad.GetCenter(),Ground);
        const double Gap=Contact?Shaft.Min.Z-Pad.Max.Z:9999;
        const double Burial=Contact?Ground.ImpactPoint.Z-Pad.Min.Z:-9999;
        // Contact is geometric; material batching changes component-group counts.
        const bool Pass=Contact&&FMath::Abs(Gap)<1.&&Burial>=.5&&Burial<=4.;
        Result->SetBoolField(TEXT("chimney_base_pass"),Pass);Result->SetNumberField(TEXT("shaft_to_pad_gap_cm"),Gap);
        Result->SetNumberField(TEXT("pad_ground_burial_cm"),Burial);if(!Pass)++Errors;
    }

    void Record(bool Pass,const FString& Why)
    {
        auto* C=Player.Get();auto Row=MakeShared<FJsonObject>();
        const FString Name=Input->GetArrayField(TEXT("routes"))[Route]->AsObject()->GetStringField(TEXT("name"));
        Row->SetStringField(TEXT("name"),Name);Row->SetBoolField(TEXT("pass"),Pass);Row->SetStringField(TEXT("reason"),Why);
        Row->SetNumberField(TEXT("walked_cm"),Walked);Row->SetNumberField(TEXT("frames"),Frames);
        Row->SetNumberField(TEXT("min_feet_above_house_floor_cm"),MinFeet);Row->SetNumberField(TEXT("max_feet_above_house_floor_cm"),MaxFeet);
        Row->SetBoolField(TEXT("airborne"),Airborne);Row->SetBoolField(TEXT("crouched"),Crouched);
        Row->SetArrayField(TEXT("trace"),Trace);
        if(!Pass)
        {
            ++Errors;FHitResult Hit;const FVector D=(Points[FMath::Min(Point,Points.Num()-1)]-C->GetActorLocation()).GetSafeNormal2D();
            World->SweepSingleByChannel(Hit,C->GetActorLocation(),C->GetActorLocation()+D*100,FQuat::Identity,ECC_Pawn,C->GetCapsuleComponent()->GetCollisionShape(),FCollisionQueryParams(SCENE_QUERY_STAT(SmithBlocked),false,C));
            Row->SetStringField(TEXT("blocking_component"),GetPathNameSafe(Hit.GetComponent()));Row->SetNumberField(TEXT("blocking_instance"),Hit.Item);
            FScreenshotRequest::RequestScreenshot(Out/(Name+TEXT("_failed.png")),false,false);
        }
        Routes.Add(MakeShared<FJsonValueObject>(Row));UE_LOG(LogTemp,Display,TEXT("SMITH_LOFT_ROUTE %s pass=%d %s"),*Name,Pass,*Why);
        C->GetCharacterMovement()->StopMovementImmediately();++Route;Stage=2;At=FPlatformTime::Seconds();
    }

    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();auto* W=World.Get();
        if(!W){++Errors;return Finish(TEXT("world unavailable"));}
        if(Now-Started>900){++Errors;return Finish(TEXT("review timeout"));}
        auto* PC=W->GetFirstPlayerController();
        if(!Player.IsValid()&&PC)Player=Cast<AFPSGAMECharacter>(PC->GetPawn());
        if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
        if(Now>NextLog){NextLog=Now+15;UE_LOG(LogTemp,Display,TEXT("SMITH_LOFT_PROGRESS stage=%d route=%d point=%d shot=%d"),Stage,Route,Point,Shot);}
        if(!PC||!Player.IsValid()||!Hills.IsValid()||!Hills->bReady)return true;
        auto* C=Player.Get();auto* M=C->GetCharacterMovement();
        if(Stage==0)
        {
            if(PC->IsMoveInputIgnored())return true;
            const auto& V=Hills->GetVillageSite();if(!V.bPlaced){++Errors;return Finish(TEXT("village absent"));}
            const FTransform Site(FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(V.Axis.Y,V.Axis.X)),0),V.Ground);
            House=FTransform(FRotator(0,178,0),FVector(-3200,-900,4))*Site;
            Result->SetNumberField(TEXT("seed"),Hills->Seed);Result->SetNumberField(TEXT("generator_version"),Hills->GeneratorVersion);
            Result->SetArrayField(TEXT("house_origin"),Arr(House.GetLocation()));
            C->SetCanBeDamaged(false);C->UnCrouch();Hills->RequestVillageVisit();Stage=1;At=Now;return true;
        }
        if(Stage==1)
        {
            if(Now-At<8||PC->IsMoveInputIgnored()||FVector::Dist2D(C->GetActorLocation(),House.GetLocation())>6500)return true;
            if(!Shop.IsValid())for(TActorIterator<AHillsBlacksmith> It(W);It;++It){Shop=*It;break;}
            if(!Shop.IsValid()||!Shop->GetOwner())return true;
            auto* P=FindFProperty<FBoolProperty>(Hills->GetClass(),TEXT("bVillageBlacksmithRepaired"));
            if(!P){++Errors;return Finish(TEXT("repair state unavailable"));}
            P->SetPropertyValue_InContainer(Hills.Get(),true);Shop->ApplyVillageState();
            Result->SetBoolField(TEXT("isolated_repaired_state_override"),true);
            bool AllShops=false;Input->TryGetBoolField(TEXT("repaired_street"),AllShops);
            if(AllShops)
            {
                auto* Plans=FindFProperty<FByteProperty>(Hills->GetClass(),TEXT("VillagePlansUnlocked"));
                auto* Notify=Hills->FindFunction(TEXT("OnRep_VillagePlansUnlocked"));
                if(!Plans||!Notify){++Errors;return Finish(TEXT("shop flags unavailable"));}
                uint8 PreviousPlans=Plans->GetPropertyValue_InContainer(Hills.Get());
                Plans->SetPropertyValue_InContainer(Hills.Get(),PreviousPlans|UTemperateHillsSave::CarpenterPlan|UTemperateHillsSave::TavernPlan|UTemperateHillsSave::HerbalistPlan);
                Hills->ProcessEvent(Notify,&PreviousPlans);
                Result->SetBoolField(TEXT("all_shops_repaired"),Hills->IsVillageBlacksmithRepaired()&&Hills->IsVillageCarpenterRepaired()&&Hills->IsHerbalistRepaired()&&Hills->IsTavernRepaired());
            }
            else InspectStructure();
            Result->SetNumberField(TEXT("capsule_radius_cm"),C->GetCapsuleComponent()->GetScaledCapsuleRadius());
            Result->SetNumberField(TEXT("capsule_half_height_cm"),C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            Result->SetNumberField(TEXT("max_step_height_cm"),M->MaxStepHeight);
            PC->ConsoleCommand(TEXT("r.SetRes 1920x1080w"));PC->ConsoleCommand(TEXT("r.ScreenPercentage 100"));
            double Hour=.44*24.;Input->TryGetNumberField(TEXT("capture_hour"),Hour);
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
            {It->SetWeatherState(EFPSWeatherState::Clear);It->RealSecondsPerGameDay=8640000.f;It->AdvanceGameTime(FMath::Fmod(float(Hour/24.)-It->NormalizedDayTime+1.f,1.f)*24.f+.00001f);}
            if(auto* VP=W->GetGameViewport())VP->RemoveAllViewportWidgets();
            Stage=2;At=Now;return true;
        }
        if(Stage==2)
        {
            if(Route>=Input->GetArrayField(TEXT("routes")).Num())
            {
                C->SetActorHiddenInGame(true);M->DisableMovement();Camera=W->SpawnActor<ACameraActor>();PC->SetViewTarget(Camera.Get());Stage=4;
                bool CheckWindows=false;Input->TryGetBoolField(TEXT("check_windows"),CheckWindows);
                if(CheckWindows)
                {
                    for(TActorIterator<AColdSteelWindow> It(W);It;++It)if(It->ActorHasTag(TEXT("VillageShop.WindowR7")))Windows.Add(*It);
                    Result->SetNumberField(TEXT("interactive_window_count"),Windows.Num());
                    if(Windows.Num()!=3)++Errors;
                    Stage=7;
                }
                At=Now;return true;
            }
            Points.Reset();for(const auto& P:Input->GetArrayField(TEXT("routes"))[Route]->AsObject()->GetArrayField(TEXT("points")))Points.Add(House.TransformPosition(Vec(P->AsArray())));
            FHitResult Hit;const FVector P=Points[0];
            if(!W->LineTraceSingleByChannel(Hit,P+FVector(0,0,200),P-FVector(0,0,70),ECC_Visibility,FCollisionQueryParams(SCENE_QUERY_STAT(SmithStart),false,C)))
            {if(Now-At<20)return true;Point=0;Record(false,TEXT("start floor unavailable"));return true;}
            const FVector Start=Hit.ImpactPoint+FVector(0,0,C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.5);
            C->SetActorLocation(Start,false,nullptr,ETeleportType::TeleportPhysics);M->StopMovementImmediately();M->SetMovementMode(MOVE_Walking);M->bForceNextFloorCheck=true;
            Point=1;Walked=0;Frames=0;Airborne=false;Crouched=false;MinFeet=DBL_MAX;MaxFeet=-DBL_MAX;Trace.Reset();Previous=Start;Best=DBL_MAX;LastProgress=Now;
            Stage=3;At=Now;return true;
        }
        if(Stage==3)
        {
            if(Now-At<.5)return true;
            const FVector P=C->GetActorLocation();const double Distance=FVector::Dist2D(P,Points[Point]);
            const double Feet=P.Z-C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
            Walked+=FVector::Dist2D(P,Previous);Previous=P;++Frames;Crouched|=C->bIsCrouched;Airborne|=!M->IsMovingOnGround();
            MinFeet=FMath::Min(MinFeet,Feet-House.GetLocation().Z);MaxFeet=FMath::Max(MaxFeet,Feet-House.GetLocation().Z);
            if(Frames%10==0)Trace.Add(MakeShared<FJsonValueArray>(Arr(House.InverseTransformPosition(FVector(P.X,P.Y,Feet)))));
            if(Distance<16&&FMath::Abs(Feet-Points[Point].Z)<50)
            {++Point;Best=DBL_MAX;LastProgress=Now;if(Point>=Points.Num()){Record(!Airborne&&!Crouched,TEXT("standing walk completed"));return true;}}
            else if(Distance<Best-2){Best=Distance;LastProgress=Now;}
            if(Now-LastProgress>10){Record(false,TEXT("no walking progress for ten seconds"));return true;}
            const FVector D=(Points[Point]-P).GetSafeNormal2D();C->AddMovementInput(D,.35f,true);PC->SetControlRotation(D.Rotation());return true;
        }
        if(Stage==4)
        {
            if(Shot>=Input->GetArrayField(TEXT("views")).Num())return Finish(TEXT("repaired shop movement, ground contact and runtime captures complete"));
            const auto S=Input->GetArrayField(TEXT("views"))[Shot]->AsObject();
            bool Open=false;
            if(S->TryGetBoolField(TEXT("windows_open"),Open))for(const auto& Window:Windows)if(Window.IsValid())
            {if(Open)Window->OpenWindowFrom(C);else Window->CloseWindow();}
            const FVector Eye=House.TransformPosition(Vec(S->GetArrayField(TEXT("eye")))),Target=House.TransformPosition(Vec(S->GetArrayField(TEXT("target"))));
            Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(S->GetNumberField(TEXT("fov")));
            PC->SetViewTarget(Camera.Get());Stage=5;At=Now;return true;
        }
        if(Stage==5&&Now-At>(Shot==0?18.:9.))
        {
            const auto S=Input->GetArrayField(TEXT("views"))[Shot]->AsObject();
            if(Shot==0&&Result->HasField(TEXT("all_shops_repaired")))
            {
                for(TActorIterator<AFPSWeatherManager> It(W);It;++It)Result->SetNumberField(TEXT("photographed_hour"),It->NormalizedDayTime*24.);
                TArray<TSharedPtr<FJsonValue>> Lights;
                for(TActorIterator<ABronzeTorch> It(W);It;++It)
                {
                    const auto* Mount=It->GetParentComponent(); if(!Mount)continue;
                    auto Light=MakeShared<FJsonObject>();
                    Light->SetStringField(TEXT("mount"),GetNameSafe(Mount));Light->SetStringField(TEXT("shop"),GetNameSafe(Mount->GetOwner()));
                    TArray<TSharedPtr<FJsonValue>> Tags;for(FName Tag:Mount->ComponentTags)Tags.Add(MakeShared<FJsonValueString>(Tag.ToString()));
                    Light->SetArrayField(TEXT("tags"),Tags);Light->SetBoolField(TEXT("lit"),It->IsLit());
                    if(auto* PointLight=It->FindComponentByClass<UPointLightComponent>())
                    {
                        const auto& Village=Hills->GetVillageSite();const FVector P3=PointLight->GetComponentLocation();const FVector2D P2=Village.Local(P3.X,P3.Y);
                        Light->SetArrayField(TEXT("village_cm"),Arr(FVector(P2.X,P2.Y,P3.Z-Village.Ground.Z)));
                        Light->SetNumberField(TEXT("radius_cm"),PointLight->AttenuationRadius);Light->SetNumberField(TEXT("intensity"),PointLight->Intensity);
                    }
                    Lights.Add(MakeShared<FJsonValueObject>(Light));
                }
                Result->SetArrayField(TEXT("torch_lights"),Lights);
            }
            FScreenshotRequest::RequestScreenshot(Out/(S->GetStringField(TEXT("name"))+TEXT(".png")),false,false);
            Shots.Add(MakeShared<FJsonValueObject>(S));UE_LOG(LogTemp,Display,TEXT("SMITH_LOFT_CAPTURE %s"),*S->GetStringField(TEXT("name")));
            Stage=6;At=Now;return true;
        }
        if(Stage==6&&Now-At>1){++Shot;Stage=4;}
        if(Stage==7)
        {
            if(WindowIndex>=Windows.Num())
            {Result->SetArrayField(TEXT("window_interactions"),WindowResults);Stage=4;At=Now;return true;}
            auto* Window=Windows[WindowIndex].Get();
            if(!Window){++Errors;++WindowIndex;return true;}
            const auto& T=Window->GetActorTransform();
            const FVector Eye=T.TransformPosition(FVector(-190,0,-15));
            const FVector Target=T.TransformPosition(FVector(-69,0,-69));
            Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());
            PC->SetControlRotation((Target-Eye).Rotation());PC->SetViewTarget(Camera.Get());
            Stage=8;At=Now;return true;
        }
        if(Stage==8&&Now-At>.5)
        {
            auto* Window=Windows[WindowIndex].Get();
            auto* Focus=ColdSteelWorldInteraction::TraceTarget(PC);
            const bool Reach=Focus==Window;
            auto* DoorPush=C->FindComponentByClass<UFPSDoorPushComponent>();
            const bool Requested=Reach&&DoorPush&&DoorPush->RequestDoorInteraction(Window);
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("window"),GetNameSafe(Window));
            Row->SetStringField(TEXT("action"),WindowStep==0?TEXT("E open"):TEXT("E close"));
            Row->SetBoolField(TEXT("trace_and_request"),Requested);Row->SetStringField(TEXT("trace_actor"),GetNameSafe(Focus));
            WindowResults.Add(MakeShared<FJsonValueObject>(Row));Stage=9;At=Now;return true;
        }
        if(Stage==9&&Now-At>1.3)
        {
            auto* Window=Windows[WindowIndex].Get();auto Row=WindowResults.Last()->AsObject();
            const bool Pass=Row->GetBoolField(TEXT("trace_and_request"))&&Window&&Window->IsWindowOpen()==(WindowStep==0);
            Row->SetBoolField(TEXT("pass"),Pass);if(!Pass)++Errors;
            if(Window)Row->SetBoolField(TEXT("idle_tick_disabled"),!Window->IsActorTickEnabled());
            if(WindowStep==0)WindowStep=1;else{WindowStep=0;++WindowIndex;}
            Stage=7;At=Now;return true;
        }
        return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.SmithLoftReview"),TEXT("Opt-in isolated repaired smith loft movement and screenshots."),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{
    if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("SmithLoftReview")))return;
    auto R=MakeShared<FReview>();R->World=W;FString InputPath;
    FParse::Value(FCommandLine::Get(),TEXT("SmithLoftInput="),InputPath);FParse::Value(FCommandLine::Get(),TEXT("SmithLoftOutput="),R->Out);
    FString Text;if(R->Out.IsEmpty()||!FFileHelper::LoadFileToString(Text,*InputPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),R->Input))return;
    IFileManager::Get().MakeDirectory(*R->Out,true);
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float Dt){return R->Tick(Dt);}));
}));
}
#endif
