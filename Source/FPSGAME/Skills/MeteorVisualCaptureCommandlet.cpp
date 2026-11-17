#include "MeteorVisualCaptureCommandlet.h"
#if WITH_EDITOR
#include "FPSMeteorStrike.h"
#include "MeteorAssets.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "FXSystem.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/WorldSettings.h"
#include "ImageUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "NiagaraSystem.h"
#include "NiagaraWorldManager.h"
#include "RenderingThread.h"
#endif

int32 UMeteorVisualCaptureCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Out=FPaths::ProjectSavedDir()/TEXT("MeteorVisualReview");
    FParse::Value(*Params,TEXT("Out="),Out);
    IFileManager::Get().MakeDirectory(*Out,true);
    FMath::RandInit(11214);
    TArray<UObject*> Loaded;
    for(const TCHAR* Path:MeteorSpellAssets::Visuals)
    {
        UObject* Asset=FSoftObjectPath(Path).TryLoad();
        if(!Asset){UE_LOG(LogTemp,Error,TEXT("METEOR_CAPTURE missing %s"),Path);return 2;}
        Loaded.Add(Asset);Asset->AddToRoot();
        if(auto* System=Cast<UNiagaraSystem>(Asset))
        {System->RequestCompile(false);System->WaitForCompilationComplete();}
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false)
        .ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("MeteorVisualReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    World->Scene->SetFXSystem(World->FXSystem.Get());
    World->InitializeActorsForPlay(FURL());
    FlushRenderingCommands();
    if(!FNiagaraGpuComputeDispatchInterface::Get(World))return 3;
    auto* Floor=World->SpawnActor<AStaticMeshActor>();
    Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Floor->SetActorLocation(FVector(0,0,-25));Floor->SetActorScale3D(FVector(100,100,.5));
    Floor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
    auto* Owner=World->SpawnActor<AActor>();
    auto* Light=NewObject<UDirectionalLightComponent>(Owner);Owner->AddInstanceComponent(Light);
    Light->SetMobility(EComponentMobility::Movable);
    Light->SetIntensity(12);Light->SetWorldRotation(FRotator(-42,25,0));Light->RegisterComponent();
    auto* Sky=NewObject<USkyLightComponent>(Owner);Owner->AddInstanceComponent(Sky);
    Sky->SourceType=SLS_SpecifiedCubemap;
    Sky->SetCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap")));
    Sky->SetIntensity(.7f);Sky->SetMobility(EComponentMobility::Movable);Sky->RegisterComponent();
    USkyLightComponent::UpdateSkyCaptureContents(World);
    auto* ScaleMarker=World->SpawnActor<AStaticMeshActor>();
    ScaleMarker->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    ScaleMarker->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    ScaleMarker->SetActorLocation(FVector(-600,0,90));ScaleMarker->SetActorScale3D(FVector(.4,.4,1.8));
    ScaleMarker->SetActorEnableCollision(false);
    constexpr int32 W=960,H=540;
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->AddToRoot();RT->RenderTargetFormat=RTF_RGBA8;
    RT->ClearColor=FLinearColor(.025f,.03f,.04f,1);RT->InitAutoFormat(W,H);RT->UpdateResourceImmediate(true);
    auto* Camera=NewObject<USceneCaptureComponent2D>(Owner);Owner->AddInstanceComponent(Camera);Camera->RegisterComponent();
    Camera->TextureTarget=RT;Camera->CaptureSource=SCS_FinalColorLDR;Camera->FOVAngle=62;
    Camera->bCaptureEveryFrame=Camera->bCaptureOnMovement=false;
    FVector Eye(900,-1200,430);FParse::Value(*Params,TEXT("EyeZ="),Eye.Z);
    Camera->SetWorldLocationAndRotation(Eye,(FVector(0,0,260)-Eye).Rotation());
    Camera->ShowFlags.SetTemporalAA(false);Camera->ShowFlags.SetAntiAliasing(false);Camera->ShowFlags.SetMotionBlur(false);
    Camera->ShowFlags.SetAtmosphere(false);Camera->ShowFlags.SetFog(false);
    Camera->PostProcessSettings.bOverride_AutoExposureMethod=true;Camera->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Camera->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Camera->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Camera->PostProcessSettings.bOverride_AutoExposureBias=true;Camera->PostProcessSettings.AutoExposureBias=2.f;
    Camera->PostProcessSettings.bOverride_BloomIntensity=true;Camera->PostProcessSettings.BloomIntensity=.35f;
    Camera->PostProcessSettings.AmbientCubemap=Sky->Cubemap;
    Camera->PostProcessSettings.bOverride_AmbientCubemapIntensity=true;Camera->PostProcessSettings.AmbientCubemapIntensity=.7f;
    FAssetCompilingManager::Get().FinishAllCompilation();
    World->BeginPlay();
    // This preview world deliberately has no game mode/profile. UWorld::BeginPlay
    // alone never dispatches actor BeginPlay without a game mode's StartPlay.
    World->GetWorldSettings()->NotifyBeginPlay();
    World->GetWorldSettings()->NotifyMatchStarted();
    auto Step=[&]()
    {
        ++GFrameCounter;World->Tick(LEVELTICK_All,1.f/60);
        FNiagaraWorldManager::Get(World)->FlushComputeAndDeferredQueues(true);
        World->SendAllEndOfFrameUpdates();
        if(auto* Dispatch=FNiagaraGpuComputeDispatchInterface::Get(World))Dispatch->FlushAndWait_GameThread();
        Camera->CaptureScene();FlushRenderingCommands();
    };
    for(int32 I=0;I<12;++I)Step();
    APawn* Caster=World->SpawnActor<APawn>();
    AFPSMeteorStrike* Meteor=World->SpawnActor<AFPSMeteorStrike>();
    FFireMagicCast Cast;Cast.Radius=652.5f;Cast.AuraRadius=558.f;Cast.Duration=6.f;
    Cast.FallSeconds=.65f;Cast.TickSeconds=.5f;
    // No combatants, game instance, profile or save subsystem. Production actor
    // still owns all presentation timing, rock breakup, impact spawn and low fire.
    Meteor->InitializeStrike(Caster,Cast,FVector::ZeroVector,FVector::UpVector);
    FString Report=FString::Printf(TEXT("actor=AFPSMeteorStrike\nimpact=%s\nwidth=%d\nheight=%d\nfps=60\nfall_seconds=.65\n"),MeteorSpellAssets::Impact,W,H);
    int32 Saved=0;bool SawImpact=false;
    for(int32 Frame=0;Frame<180;++Frame)
    {
        Step();
        TArray<FColor> Pixels;
        if(!RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)||Pixels.Num()!=W*H)return 4;
        for(FColor& Pixel:Pixels)Pixel.A=255;
        TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(W,H,Pixels,PNG);
        const FString File=Out/FString::Printf(TEXT("frame-%04d.png"),Frame);
        if(FFileHelper::SaveArrayToFile(PNG,*File))++Saved;
        if(Frame==44||Frame==59||Frame==89)
        {
            Report+=FString::Printf(TEXT("frame=%d world_time=%.3f begun_play=%d actor_begun_play=%d\n"),Frame,World->GetTimeSeconds(),World->HasBegunPlay(),Meteor->HasActorBegunPlay());
            for(TObjectIterator<UNiagaraComponent> It;It;++It)
                if(It->GetWorld()==World&&It->GetAsset()&&It->GetAsset()->GetName().Contains(TEXT("Meteor")))
                {
                    SawImpact|=It->GetAsset()->GetName()==TEXT("NS_MeteorPressureV7");
                    Report+=FString::Printf(TEXT("frame=%d component=%s system=%s active=%d\n"),Frame,*It->GetName(),*It->GetAsset()->GetName(),It->IsActive());
                }
        }
    }
    Report+=FString::Printf(TEXT("saved_frames=%d\n"),Saved);
    FFileHelper::SaveStringToFile(Report,*(Out/TEXT("capture.txt")));
    UE_LOG(LogTemp,Display,TEXT("METEOR_CAPTURE %s"),*Report);
    Meteor->FinishForRemoval();FlushRenderingCommands();World->DestroyWorld(false);FlushRenderingCommands();
    RT->RemoveFromRoot();for(UObject* Asset:Loaded)Asset->RemoveFromRoot();
    return Saved==180&&SawImpact?0:5;
#else
    return 1;
#endif
}
