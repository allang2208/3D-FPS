#include "TemperateHillsWorld.h"

#if WITH_DEV_AUTOMATION_TESTS && !UE_BUILD_SHIPPING
#include "TemperateHillsGroundLayers.h"
#include "../Building/BuildingDaylight.h"
#include "../Building/ColdSteelDoor.h"
#include "../FPSWeatherManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace ChapelLightingReview
{
struct FObservedView : FSceneViewExtensionBase
{
    FObservedView(const FAutoRegister& R):FSceneViewExtensionBase(R){}
    TArray<TSharedPtr<FJsonValue>> Samples;
    FTransform Chapel;
    TWeakObjectPtr<UWorld> World;
    TSet<FString> Inspected;
    FString Label;
    double Next=0.;
    virtual void SetupView(FSceneViewFamily&,FSceneView& V) override
    {
        const double Now=FPlatformTime::Seconds();
        if(Label.IsEmpty()||V.bIsSceneCapture||Now<Next)return;
        Next=Now+.1;
        const FVector P=Chapel.InverseTransformPosition(V.ViewMatrices.GetViewOrigin());
        const auto& S=V.FinalPostProcessSettings;
        auto Row=MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("view"),Label);Row->SetNumberField(TEXT("time"),Now);
        Row->SetNumberField(TEXT("local_x"),P.X);Row->SetNumberField(TEXT("local_y"),P.Y);
        Row->SetNumberField(TEXT("bias"),S.AutoExposureBias);
        Row->SetNumberField(TEXT("min_ev"),S.AutoExposureMinBrightness);
        Row->SetNumberField(TEXT("max_ev"),S.AutoExposureMaxBrightness);
        Row->SetNumberField(TEXT("shadow_contrast"),S.LocalExposureShadowContrastScale);
        Row->SetNumberField(TEXT("highlight_contrast"),S.LocalExposureHighlightContrastScale);
        if(!Inspected.Contains(Label)&&World.IsValid())
        {
            Inspected.Add(Label);
            TArray<TSharedPtr<FJsonValue>> Rooms;
            for(TActorIterator<ABuildingDaylight> It(World.Get());It;++It)
            {
                const FVector Local=It->GetActorTransform().InverseTransformPosition(V.ViewMatrices.GetViewOrigin());
                if(!FBox(It->RoomMinimum,It->RoomMaximum).IsInsideOrOn(Local))continue;
                auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("actor"),It->GetName());
                R->SetStringField(TEXT("transform"),It->GetActorTransform().ToHumanReadableString());
                auto* PP=It->FindComponentByClass<UPostProcessComponent>();float Distance=0.;
                R->SetBoolField(TEXT("encompasses"),PP->EncompassesPoint(V.ViewMatrices.GetViewOrigin(),0.,&Distance));
                R->SetNumberField(TEXT("volume_distance"),Distance);R->SetNumberField(TEXT("priority"),PP->Priority);
                const bool Unbound=PP->bUnbound;PP->bUnbound=false;
                R->SetBoolField(TEXT("legacy_bounded_encompasses"),PP->EncompassesPoint(V.ViewMatrices.GetViewOrigin(),0.,&Distance));
                R->SetNumberField(TEXT("legacy_bounded_distance"),Distance);PP->bUnbound=Unbound;
                R->SetBoolField(TEXT("enabled"),PP->bEnabled);R->SetNumberField(TEXT("blendables"),PP->Settings.WeightedBlendables.Array.Num());
                auto Saved=V.FinalPostProcessSettings;
                It->OverrideBlendableSettings(V,1.f);
                R->SetNumberField(TEXT("manual_bias_delta"),V.FinalPostProcessSettings.AutoExposureBias-Saved.AutoExposureBias);
                V.FinalPostProcessSettings=Saved;
                Rooms.Add(MakeShared<FJsonValueObject>(R));
            }
            Row->SetArrayField(TEXT("room_diagnostics"),Rooms);
        }
        Samples.Add(MakeShared<FJsonValueObject>(Row));
    }
};

struct FReview
{
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<ACameraActor> Camera;
    TSharedPtr<FObservedView,ESPMode::ThreadSafe> Observe;
    FTransform Chapel,Village;
    FString Out;
    TSharedPtr<FJsonObject> Result=MakeShared<FJsonObject>();
    double Began=FPlatformTime::Seconds(),Next=0.,MotionStart=0.,NextFrame=0.;
    int32 Phase=0,View=0,Frame=0;
    bool bPrepared=false;

    bool Finish(bool Success)
    {
        Result->SetBoolField(TEXT("capture_completed"),Success);
        if(Observe){Result->SetArrayField(TEXT("exposure_samples"),Observe->Samples);Observe->Label.Empty();}
        FString Json;FJsonSerializer::Serialize(Result.ToSharedRef(),TJsonWriterFactory<>::Create(&Json));
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("CHAPEL_LIGHTING_CAPTURE_COMPLETE success=%d"),Success);
        UGameplayStatics::OpenLevel(World.Get(),TEXT("/Engine/Maps/Entry"));
        const double ExitAt=FPlatformTime::Seconds()+8.;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Success,ExitAt](float)
        {if(FPlatformTime::Seconds()<ExitAt)return true;FPlatformMisc::RequestExitWithStatus(false,Success?0:1);return false;}));
        return false;
    }
    void Place(FVector Eye,FVector Target,bool IsVillage=false)
    {
        const auto& T=IsVillage?Village:Chapel;
        FVector E=T.TransformPosition(FVector(Eye.X,Eye.Y,0));
        E.Z=(IsVillage?Hills->Height(E.X,E.Y):Chapel.GetLocation().Z)+Eye.Z;
        const FVector Aim=T.TransformPosition(Target);
        Camera->SetActorLocationAndRotation(E,(Aim-E).Rotation());
        APawn* Pawn=World->GetFirstPlayerController()->GetPawn();
        Pawn->SetActorLocation(E+FVector(0,0,160),false,nullptr,ETeleportType::TeleportPhysics);
    }
    bool Tick(float)
    {
        auto* W=World.Get();if(!W)return false;
        const double Now=FPlatformTime::Seconds();
        if(Now-Began>600)return Finish(false);
        if(Now<Next)return true;
        auto* PC=W->GetFirstPlayerController();if(!PC||!PC->GetPawn())return true;
        if(!Hills.IsValid())for(TActorIterator<ATemperateHillsWorld> It(W);It;++It){Hills=*It;break;}
        if(!Hills.IsValid()||!Hills->bReady||PC->IsMoveInputIgnored())return true;
        if(Phase==0)
        {
            TemperateHillsGround::FMapSource Map;Hills->CopyMapGround(Map);
            Village=FTransform(FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Map.Village.Axis.Y,Map.Village.Axis.X)),0),Map.Village.Ground);
            Hills->RequestVillageVisit();Phase=1;Next=Now+10.;return true;
        }
        if(Phase==1)
        {
            bool Found=false;
            for(auto* C:TInlineComponentArray<UInstancedStaticMeshComponent*>(Hills.Get()))
                if(C->GetName()==TEXT("OldChapel_Foundation"))Found=C->GetInstanceTransform(0,Chapel,true);
            if(!Found)return true;
            Result->SetNumberField(TEXT("seed"),Hills->Seed);
            Result->SetStringField(TEXT("world"),W->GetMapName());
            Result->SetStringField(TEXT("chapel_transform"),Chapel.ToHumanReadableString());
            Result->SetNumberField(TEXT("chapel_rect_lights"),TInlineComponentArray<URectLightComponent*>(Hills.Get()).Num());
            int32 Rooms=0;for(TActorIterator<ABuildingDaylight> It(W);It;++It)++Rooms;
            Result->SetNumberField(TEXT("interior_vision_rooms"),Rooms);
            for(TActorIterator<AFPSWeatherManager> It(W);It;++It)
            {
                It->SetWeatherState(EFPSWeatherState::Clear);
                It->RealSecondsPerGameDay=8640000.f;
                // AdvanceGameTime also resynchronizes its private clock to the
                // new period. It accepts positive hours only.
                It->AdvanceGameTime(FMath::Fmod(.375f-It->NormalizedDayTime+1.f,1.f)*24.f+.00001f);
                Result->SetNumberField(TEXT("day_time"),It->NormalizedDayTime);
            }
            PC->GetPawn()->SetCanBeDamaged(false);PC->GetPawn()->SetActorHiddenInGame(true);
            if(auto* C=Cast<ACharacter>(PC->GetPawn()))C->GetCharacterMovement()->DisableMovement();
            for(TActorIterator<AColdSteelDoor> It(W);It;++It)if(It->GetOwner()==Hills.Get())It->OpenDoorFrom(PC->GetPawn());
            if(auto* VP=W->GetGameViewport())VP->RemoveAllViewportWidgets();
            Camera=W->SpawnActor<ACameraActor>();Camera->GetCameraComponent()->SetFieldOfView(76.f);PC->SetViewTarget(Camera.Get());
            Observe=FSceneViewExtensions::NewExtension<FObservedView>();Observe->Chapel=Chapel;Observe->World=W;
            Phase=2;Next=Now+2.;
        }
        static const TCHAR* Names[]={TEXT("window_south"),TEXT("window_north"),TEXT("window_east"),TEXT("interior_nave"),TEXT("interior_window"),TEXT("road_entry"),TEXT("road_square"),TEXT("road_verge")};
        static const FVector Eyes[]={FVector(-40,1000,210),FVector(90,-1000,210),FVector(1250,120,240),FVector(-450,0,165),FVector(0,30,165),FVector(-3900,50,165),FVector(-100,630,165),FVector(-2750,200,160)};
        static const FVector Aims[]={FVector(140,375,265),FVector(140,-375,265),FVector(775,0,354),FVector(550,30,185),FVector(200,375,240),FVector(-2900,-50,0),FVector(1400,800,0),FVector(-2650,-80,0)};
        if(Phase==2)
        {
            if(View==UE_ARRAY_COUNT(Names)){Phase=3;Next=Now+2.;return true;}
            if(!bPrepared)
            {
                Observe->Label=Names[View];Place(Eyes[View],Aims[View],View>=5);bPrepared=true;Next=Now+(View==0?55.:12.);return true;
            }
            FScreenshotRequest::RequestScreenshot(Out/(FString(Names[View])+TEXT(".png")),false,false);
            UE_LOG(LogTemp,Display,TEXT("CHAPEL_LIGHTING_VIEW %s"),Names[View]);
            ++View;bPrepared=false;Next=Now+2.;return true;
        }
        if(Phase==3)
        {
            Observe->Label=TEXT("enter");Place(FVector(-980,0,165),FVector(600,0,165));
            Phase=4;MotionStart=Now+10.;Next=MotionStart;Frame=0;NextFrame=MotionStart;return true;
        }
        if(Phase==4||Phase==6)
        {
            // Cross the 6.25 m approach at a walking pace, not a slow dolly.
            const double T=FMath::Clamp((Now-MotionStart)/4.,0.,1.);
            const double X=Phase==4?FMath::Lerp(-980.,-480.,T):FMath::Lerp(-480.,-980.,T);
            Place(FVector(X,0,165),FVector(600,0,165));
            if(Now>=NextFrame)
            {
                FScreenshotRequest::RequestScreenshot(Out/FString::Printf(TEXT("%s_%03d.png"),Phase==4?TEXT("enter"):TEXT("exit"),Frame++),false,false);
                NextFrame=Now+.2;
            }
            if(T>=1.){++Phase;Next=Now+10.;}
            return true;
        }
        if(Phase==5){Observe->Label=TEXT("exit");Phase=6;MotionStart=Now;NextFrame=Now;Frame=0;return true;}
        if(Phase==7)return Finish(true);
        return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.ChapelLighting"),TEXT("Opt-in actual hills lighting and road captures."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
    {
        if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("ChapelLightingReview")))return;
        auto R=MakeShared<FReview>();R->World=W;
        if(!FParse::Value(FCommandLine::Get(),TEXT("ChapelLightingOutput="),R->Out))return;
        IFileManager::Get().MakeDirectory(*R->Out,true);
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float Dt){return R->Tick(Dt);}),.02f);
    }));
}
#endif
