#include "BlizzardVisualCaptureCommandlet.h"
#if WITH_EDITOR
#include "FPSBlizzardZone.h"
#include "BlizzardEnvironment.h"
#include "ColdSteelSkillRules.h"
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
#include "Materials/Material.h"
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Materials/MaterialExpression.h"
#include "Materials/MaterialExpressionSubstrate.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "NiagaraSystem.h"
#include "NiagaraWorldManager.h"
#include "RenderingThread.h"
#endif

int32 UBlizzardVisualCaptureCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Out=FPaths::ProjectSavedDir()/TEXT("BlizzardVisualReview");
    FParse::Value(*Params,TEXT("Out="),Out);
    IFileManager::Get().MakeDirectory(*Out,true);
    FString CloudVersion=TEXT("RollingV1");
    FParse::Value(*Params,TEXT("CloudVersion="),CloudVersion);
    FString CloudPath;
    if(CloudVersion==TEXT("RollingV1"))CloudPath=TEXT("/Game/Skills/StormClouds/RollingV1/NS_BlizzardStormCloud.NS_BlizzardStormCloud");
    else if(CloudVersion==TEXT("StormDomainV2"))CloudPath=TEXT("/Game/Skills/ElectricMagic/StormDomainV2/NS_StormDomainCloud.NS_StormDomainCloud");
    else if(CloudVersion==TEXT("ChargedV3"))CloudPath=TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardStormCloud.NS_BlizzardStormCloud");
    else if(CloudVersion==TEXT("StormV2"))CloudPath=TEXT("/Game/Skills/Blizzard/StormV2/NS_BlizzardStormCloud.NS_BlizzardStormCloud");
    else {UE_LOG(LogTemp,Error,TEXT("Unknown cloud version: %s"),*CloudVersion);return 8;}
    FMath::RandInit(1115);
    TArray<TObjectPtr<UObject>> Assets;
    const TCHAR* const* Paths=AFPSBlizzardZone::ZoneAssetPaths();
    for(int32 I=0;I<AFPSBlizzardZone::AssetCount;++I)
    {
        UObject* Asset=FSoftObjectPath(I==0?CloudPath:FString(Paths[I])).TryLoad();
        if(!Asset){UE_LOG(LogTemp,Error,TEXT("BLIZZARD_CAPTURE missing %s"),Paths[I]);return 2;}
        Assets.Add(Asset);Asset->AddToRoot();
        if(auto* System=Cast<UNiagaraSystem>(Asset))
        {System->RequestCompile(false);System->WaitForCompilationComplete();}
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto Definition=ColdSteelSkills::LoadDefinition(TEXT("blizzard"));
    const auto& Tuning=Definition.Blizzard;
    FBlizzardCast Spell;
    // Level-one footprint and timing from the current definition. No profile,
    // game mode, combatants, persistent map, or save system participates.
    Spell.RadiusX=(Tuning.RadiusXBase+Tuning.RadiusXPerLevel)*Tuning.UnitsToCM;
    Spell.RadiusY=(Tuning.RadiusYBase+Tuning.RadiusYPerLevel)*Tuning.UnitsToCM;
    Spell.Duration=Tuning.Duration;Spell.TickSeconds=Tuning.TickSeconds;
    const float CloudHeight=BlizzardEnvironment::VerticalReach(Spell.RadiusY);
    auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false)
        .ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("BlizzardVisualReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    World->Scene->SetFXSystem(World->FXSystem.Get());World->InitializeActorsForPlay(FURL());
    FlushRenderingCommands();
    if(!FNiagaraGpuComputeDispatchInterface::Get(World))return 3;
    auto* Floor=World->SpawnActor<AStaticMeshActor>();
    auto* FloorMesh=Floor->GetStaticMeshComponent();
    FloorMesh->SetMobility(EComponentMobility::Movable);
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    auto* Plain=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    if(!Cube||!Plain)return 4;
    FloorMesh->SetStaticMesh(Cube);FloorMesh->SetMaterial(0,Plain);
    Floor->SetActorLocation(FVector(0,0,-25));Floor->SetActorScale3D(FVector(100,100,.5));
    FloorMesh->SetCollisionProfileName(TEXT("BlockAll"));
    if(auto* MID=FloorMesh->CreateAndSetMaterialInstanceDynamic(0))MID->SetVectorParameterValue(TEXT("Color"),FLinearColor(.20f,.23f,.26f));
    FVector Eye(650,-800,500);FParse::Value(*Params,TEXT("EyeZ="),Eye.Z);
    const FVector Aim(0,0,CloudHeight*.48f);
    // A neutral, unlit backdrop makes charcoal cloud edges readable. This
    // transient stage material is never saved or assigned to a production asset.
    auto* BackMaterial=NewObject<UMaterial>(GetTransientPackage(),NAME_None,RF_Transient);
    BackMaterial->SetShadingModel(MSM_Unlit);
    auto* BackColor=NewObject<UMaterialExpressionConstant3Vector>(BackMaterial);
    BackColor->Material=BackMaterial;
    BackColor->Constant=FLinearColor(.22f,.25f,.29f);
    BackMaterial->GetExpressionCollection().AddExpression(BackColor);
    BackMaterial->GetEditorOnlyData()->EmissiveColor.Expression=BackColor;
    auto* BackBSDF=NewObject<UMaterialExpressionSubstrateUnlitBSDF>(BackMaterial);
    BackBSDF->Material=BackMaterial;
    BackBSDF->EmissiveColor.Expression=BackColor;
    BackMaterial->GetExpressionCollection().AddExpression(BackBSDF);
    BackMaterial->GetEditorOnlyData()->FrontMaterial.Expression=BackBSDF;
    BackMaterial->PostEditChange();
    auto* Backdrop=World->SpawnActor<AStaticMeshActor>();
    auto* BackMesh=Backdrop->GetStaticMeshComponent();BackMesh->SetMobility(EComponentMobility::Movable);
    BackMesh->SetStaticMesh(Cube);BackMesh->SetMaterial(0,BackMaterial);BackMesh->SetCastShadow(false);
    BackMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);BackMesh->SetReceivesDecals(false);
    const FVector ViewSide=Eye.GetSafeNormal2D();
    Backdrop->SetActorLocation(-ViewSide*950+FVector(0,0,700));
    Backdrop->SetActorRotation(FRotationMatrix::MakeFromY(ViewSide).Rotator());
    Backdrop->SetActorScale3D(FVector(120,.1,70));
    auto* Rig=World->SpawnActor<AActor>();
    auto* Light=NewObject<UDirectionalLightComponent>(Rig);Rig->AddInstanceComponent(Light);
    Light->SetMobility(EComponentMobility::Movable);Light->SetIntensity(10);
    Light->SetWorldRotation(FRotator(-42,25,0));Light->RegisterComponent();
    auto* Sky=NewObject<USkyLightComponent>(Rig);Rig->AddInstanceComponent(Sky);
    Sky->SourceType=SLS_SpecifiedCubemap;
    Sky->SetCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap")));
    Sky->SetIntensity(.8f);Sky->SetMobility(EComponentMobility::Movable);Sky->RegisterComponent();
    USkyLightComponent::UpdateSkyCaptureContents(World);
    constexpr int32 W=960,H=720;
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->AddToRoot();RT->RenderTargetFormat=RTF_RGBA8;
    RT->ClearColor=FLinearColor(.15f,.18f,.22f,1);RT->InitAutoFormat(W,H);RT->UpdateResourceImmediate(true);
    auto* Camera=NewObject<USceneCaptureComponent2D>(Rig);Rig->AddInstanceComponent(Camera);Camera->RegisterComponent();
    Camera->TextureTarget=RT;Camera->CaptureSource=SCS_FinalColorLDR;Camera->FOVAngle=52;
    Camera->bCaptureEveryFrame=Camera->bCaptureOnMovement=false;
    Camera->SetWorldLocationAndRotation(Eye,(Aim-Eye).Rotation());
    Camera->ShowFlags.SetTemporalAA(false);Camera->ShowFlags.SetAntiAliasing(false);Camera->ShowFlags.SetMotionBlur(false);
    Camera->ShowFlags.SetAtmosphere(false);Camera->ShowFlags.SetFog(false);
    auto& PP=Camera->PostProcessSettings;
    PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=1.f;
    PP.bOverride_BloomIntensity=true;PP.BloomIntensity=.15f;
    PP.AmbientCubemap=Sky->Cubemap;PP.bOverride_AmbientCubemapIntensity=true;PP.AmbientCubemapIntensity=.8f;
    FAssetCompilingManager::Get().FinishAllCompilation();
    World->BeginPlay();World->GetWorldSettings()->NotifyBeginPlay();World->GetWorldSettings()->NotifyMatchStarted();
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
    auto* Blizzard=World->SpawnActor<AFPSBlizzardZone>();
    if(!Blizzard->InitializeZone(Caster,Spell,FVector::ZeroVector,FVector::UpVector,FVector::ForwardVector,Assets))return 5;
    // Compare only clouds: StormDomain's electrical decorations do not belong
    // to Blizzard. Disable them on these preview components, not on the asset.
    if(CloudVersion==TEXT("StormDomainV2"))
    {
        TArray<UNiagaraComponent*> Components;Blizzard->GetComponents(Components);
        for(auto* FX:Components)if(FX->GetAsset()==Assets[0])
        {FX->SetEmitterEnable(TEXT("CloudDischarges"),false);FX->SetEmitterEnable(TEXT("FallingElectricSparks"),false);}
    }
    Blizzard->ActivateZone();
    FString Report=FString::Printf(TEXT("actor=AFPSBlizzardZone\nfixture=isolated_flat_floor_full_detail_no_weather\nwidth=%d\nheight=%d\nsimulation_fps=60\noutput_fps=20\nradius_x=%.3f\nradius_y=%.3f\nduration=%.3f\ncloud_height=%.3f\n"),W,H,Spell.RadiusX,Spell.RadiusY,Spell.Duration,CloudHeight);
    Report+=FString::Printf(TEXT("cloud_version=%s\ncloud_asset=%s\nassets_modified=0\nelectrical_decorations_disabled=%d\ncamera=650,-800,%.3f\ncamera_fov=52\nbackground=neutral_unlit\n"),*CloudVersion,*CloudPath,CloudVersion==TEXT("StormDomainV2"),Eye.Z);
    int32 Saved=0;bool SawCloud=false,SawMist=false;
    const int32 Frames=FMath::CeilToInt((Spell.Duration+.8f)*60);
    for(int32 Frame=0;Frame<Frames;++Frame)
    {
        Step();
        if(Frame%3==0)
        {
            TArray<FColor> Pixels;
            if(!RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)||Pixels.Num()!=W*H)return 6;
            for(FColor& Pixel:Pixels)Pixel.A=255;
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(W,H,Pixels,PNG);
            if(FFileHelper::SaveArrayToFile(PNG,*(Out/FString::Printf(TEXT("frame-%04d.png"),Saved))))++Saved;
        }
        if(Frame==59||Frame==179||Frame==269)
        {
            for(TObjectIterator<UNiagaraComponent> It;It;++It)
                if(It->GetWorld()==World&&It->GetAsset()&&(It->GetAsset()==Assets[0]||It->GetAsset()->GetName().Contains(TEXT("Blizzard"))))
                {
                    SawCloud|=It->IsActive()&&It->GetAsset()==Assets[0];
                    SawMist|=It->IsActive()&&It->GetAsset()->GetName()==TEXT("NS_BlizzardBoundaryMist");
                    Report+=FString::Printf(TEXT("frame=%d component=%s system=%s active=%d ready=%d\n"),Frame,*It->GetName(),*It->GetAsset()->GetName(),It->IsActive(),It->GetAsset()->IsReadyToRun());
                }
        }
    }
    Report+=FString::Printf(TEXT("saved_frames=%d\nsaw_active_cloud=%d\nsaw_active_mist=%d\n"),Saved,SawCloud,SawMist);
    FFileHelper::SaveStringToFile(Report,*(Out/TEXT("capture.txt")));
    UE_LOG(LogTemp,Display,TEXT("BLIZZARD_CAPTURE %s"),*Report);
    if(IsValid(Blizzard))Blizzard->FinishForRemoval();
    FlushRenderingCommands();World->DestroyWorld(false);FlushRenderingCommands();
    RT->RemoveFromRoot();for(UObject* Asset:Assets)Asset->RemoveFromRoot();
    return Saved==(Frames+2)/3&&SawCloud&&SawMist?0:7;
#else
    return 1;
#endif
}
