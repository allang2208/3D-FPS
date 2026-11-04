#include "RuneSwordAuditCommandlet.h"
#if WITH_EDITOR
#include "RuneSwordComponent.h"
#include "RuneSwordMeshComponent.h"
#include "StarMarrowComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "FXSystem.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"
#include "NiagaraComponent.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraGpuComputeDispatchInterface.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstance.h"
#include "NiagaraSystemInstanceController.h"
#include "RenderingThread.h"
#include "Serialization/JsonSerializer.h"
#include "ShaderCompiler.h"
#endif

int32 URuneSwordAuditCommandlet::CaptureStarMarrowFire(const FString& Params)
{
#if !WITH_EDITOR
    return 2;
#else
    FString Out;
    if(!FParse::Value(*Params,TEXT("Out="),Out)||!FApp::CanEverRender())return 2;
    IFileManager::Get().MakeDirectory(*Out,true);
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Fire_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Append(*(TEXT(" -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("StarMarrowFireReview"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();FCommandLine::Set(*Original);};
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!World->Scene||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 3;
    // UWorld::CreateFXSystem deliberately skips commandlets even with an active RHI.
    // The disposable capture world needs the same dispatch interface as a game scene.
    if(!World->FXSystem)World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    FlushRenderingCommands();
    if(!FNiagaraGpuComputeDispatchInterface::Get(World))return 15;
    World->InitializeActorsForPlay(FURL());
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.Mana=100;State.Stamina=100;State.DungeonRun={};
    auto Item=Model->CreateItem(TEXT("ue_frost_crystal_sword"));Item.InstanceId=TEXT("fire-review");Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);if(!Data)Data=MakeShared<FJsonObject>();
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("star_marrow"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));State.Items.Add(Item);Model->AdoptNetMirror(State);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Pawn);Pawn->SetActorTickEnabled(false);
    for(auto* C:Pawn->GetComponents())C->SetComponentTickEnabled(false);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();auto* Core=Pawn->FindComponentByClass<UStarMarrowComponent>();
    Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();Sword->RefreshEquipment(Model);Sword->CancelAction();
    auto* Arms=Cast<URuneSwordMeshComponent>(Sword->Viewmodel);if(!Arms||!Sword->ModularSword)return 4;
    auto* Charge=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeMotion20261103/Standard/A_StarMarrow_Charge"));
    auto* Slash=Sword->Animations.FindRef(TEXT("Slash1")).Get();if(!Charge||!Slash)return 5;
    Sword->Animations.Add(TEXT("StarMarrowCharge"),Charge);Sword->SetClip(TEXT("Idle"),true);Arms->ClearWhirlwindEntry();Sword->SamplePose(0);
    Core->Configure(Model);
    if(Core->FlameLoad)Core->FlameLoad->WaitUntilComplete();
    FlushAsyncLoading();FAssetCompilingManager::Get().FinishAllCompilation();
    for(int32 I=0;I<3&&!Core->FlameSystem;++I){++GFrameCounter;FTickableGameObject::TickObjects(nullptr,LEVELTICK_All,false,1.f/60.f);}
    if(!Core->FlameSystem){UE_LOG(LogTemp,Error,TEXT("FIRE_REVIEW_LOAD equipped=%d handle=%d loaded=%s"),Core->IsEquipped(),Core->FlameLoad.IsValid(),Core->FlameLoad?*GetPathNameSafe(Core->FlameLoad->GetLoadedAsset()):TEXT("None"));return 6;}
    Core->Trigger();if(Core->Remaining()<=0){UE_LOG(LogTemp,Error,TEXT("FIRE_REVIEW_TRIGGER equipped=%d ready=%d busy=%d local=%d mana=%f"),Core->IsEquipped(),Sword->IsStarMarrowChargeMotionReady(),Sword->IsBusy(),Pawn->IsLocallyControlled(),Model->Mana());return 7;}
    FFlameArmorAttachments Spans;FlameArmorAttachments::Gather(Pawn,Spans);if(Spans.IsEmpty())return 8;
    const FVector Center=(Spans[0].Base+Spans[0].Tip)*.5;
    auto* Rig=World->SpawnActor<AActor>();
    auto* Light=NewObject<UDirectionalLightComponent>(Rig);Rig->AddInstanceComponent(Light);Light->SetIntensity(4.f);Light->SetWorldRotation(FRotator(-45,25,0));Light->RegisterComponent();
    auto* Fill=NewObject<UDirectionalLightComponent>(Rig);Rig->AddInstanceComponent(Fill);Fill->SetIntensity(2.f);Fill->SetLightColor(FLinearColor(.7f,.80f,1.f));Fill->SetWorldRotation(FRotator(-20,180,0));Fill->RegisterComponent();
    auto* Capture=NewObject<USceneCaptureComponent2D>(Rig);Rig->AddInstanceComponent(Capture);
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->bAlwaysPersistRenderingState=true;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->CaptureSource=SCS_FinalColorLDR;
    auto* Target=NewObject<UTextureRenderTarget2D>(Rig);Target->ClearColor=FLinearColor(.024f,.031f,.042f);Target->InitCustomFormat(640,640,PF_B8G8R8A8,false);Target->UpdateResourceImmediate(true);Capture->TextureTarget=Target;
    Capture->RegisterComponent();Capture->FOVAngle=58.f;Capture->SetWorldLocationAndRotation(Center-FVector::ForwardVector*155.,FRotator::ZeroRotator);
    Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetTemporalAA(false);
    auto& PP=Capture->PostProcessSettings;PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=0;PP.bOverride_BloomIntensity=true;PP.BloomIntensity=.2f;
    // A scene capture has no player view owner. Expose the equipped primitives only to this isolated camera.
    Arms->SetOnlyOwnerSee(false);Capture->ShowOnlyComponent(Arms);
    TInlineComponentArray<UStaticMeshComponent*> Meshes(Pawn);
    for(auto* M:Meshes)if(M==Sword->ModularSword||M->IsAttachedTo(Sword->ModularSword)){M->SetOnlyOwnerSee(false);Capture->ShowOnlyComponent(M);}
    if(FParse::Param(*Params,TEXT("GrayStudio")))
    {
        auto* Wall=NewObject<UStaticMeshComponent>(Rig);Rig->AddInstanceComponent(Wall);
        Wall->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube")));
        Wall->SetCollisionEnabled(ECollisionEnabled::NoCollision);Wall->SetCastShadow(false);Wall->RegisterComponent();
        Wall->SetWorldLocation(Center+FVector(400.,0.,0.));Wall->SetWorldScale3D(FVector(.1,30.,30.));
        if(auto* Gray=Wall->CreateAndSetMaterialInstanceDynamic(0))Gray->SetVectorParameterValue(TEXT("Color"),FLinearColor(.14f,.16f,.20f));
        Capture->ShowOnlyComponent(Wall);
    }
    if(GShaderCompilingManager)GShaderCompilingManager->FinishAllCompilation();
    FString CSV=TEXT("frame,time,phase,base_px,base_py,tip_px,tip_py,root_flow,tip_flow,core,tongues,curls,wake,embers\n");
    const auto SaveFrame=[&](const FString& Name)
    {
        World->SendAllEndOfFrameUpdates();Capture->CaptureScene();FlushRenderingCommands();
        TArray<FColor> Pixels;if(!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)||Pixels.Num()!=640*640)return false;
        for(auto& Pixel:Pixels)Pixel.A=255;
        TArray64<uint8> Bytes;FImageUtils::PNGCompressImageArray(640,640,Pixels,Bytes);return FFileHelper::SaveArrayToFile(Bytes,*(Out/Name));
    };
    if(!SaveFrame(TEXT("reference.png")))return 9;
    constexpr float Dt=1.f/60.f;UNiagaraComponent* FX=nullptr;
    for(int32 F=0;F<388;++F)
    {
        ++GFrameCounter;World->Tick(LEVELTICK_TimeOnly,Dt);
        float PoseTime=0.f;const TCHAR* Phase;
        if(F<132){Phase=TEXT("charge");PoseTime=F*Dt;}
        else if(F<222){Phase=TEXT("idle");if(F==132){Sword->CancelAction();Sword->SetClip(TEXT("Idle"),true);}PoseTime=(F-132)*Dt;}
        else if(F<296){Phase=F<248?TEXT("swing"):TEXT("stop");if(F==222)Sword->SetClip(TEXT("Slash1"),false);PoseTime=FMath::Min((F-222)*Dt,25*Dt)*Slash->GetPlayLength()*1.5f;}
        else if(F<340){Phase=TEXT("recover");PoseTime=FMath::Lerp(25*Dt*1.5f,1.f,(F-296)/43.f)*Slash->GetPlayLength();}
        else {Phase=TEXT("expiry");if(F==340){Core->ChargedUntil=Core->Clock()+.45;Sword->SetClip(TEXT("Idle"),true);}PoseTime=(F-340)*Dt;}
        Arms->AdvanceLocomotionEntry(Dt);Sword->Elapsed=PoseTime;Sword->SamplePose(PoseTime);
        Core->TickComponent(Dt,LEVELTICK_All,nullptr);
        if(!FX&&Core->FlameFX.Num())
        {
            FX=Core->FlameFX[0];if(!FX)return 10;
            Capture->ShowOnlyComponent(FX);FX->SetForceSolo(true);
            UE_LOG(LogTemp,Display,TEXT("FIRE_REVIEW_SYSTEM %s"),*GetPathNameSafe(FX->GetAsset()));
        }
        if(!FX)return 11;
        FX->SetOnlyOwnerSee(false);if(FX->IsActive())FX->AdvanceSimulation(1,Dt);
        if(F==150&&!FX->GetSystemInstanceController()){UE_LOG(LogTemp,Error,TEXT("FIRE_REVIEW_NO_INSTANCE active=%d assetready=%d worldready=%d"),FX->IsActive(),FX->GetAsset()->IsReadyToRun(),FX->IsWorldReadyToRun());return 16;}
        if(F%2)continue;
        const auto& H=Core->FlameHistory[0];
        // Follow translation during the swing so the tip stays in the inspection frame.
        // Orientation and focal length stay fixed; reversal and plume inertia remain visible.
        if(F>=222&&F<340)Capture->SetWorldLocation((H.Base+H.Tip)*.5-FVector::ForwardVector*155.);
        if(F==340)Capture->SetWorldLocation(Center-FVector::ForwardVector*155.);
        const auto Project=[&](FVector V){V-=Capture->GetComponentLocation();const double Scale=320./(FMath::Max(.001,V.X)*FMath::Tan(FMath::DegreesToRadians(29.)));return FVector2D(320.+V.Y*Scale,320.-V.Z*Scale);};
        const FVector2D Base=Project(H.Base),Tip=Project(H.Tip);
        CSV+=FString::Printf(TEXT("%d,%.3f,%s,%.3f,%.3f,%.3f,%.3f,%.2f,%.2f"),F,F*Dt,Phase,Base.X,Base.Y,Tip.X,Tip.Y,H.BaseFlow.Size(),H.TipFlow.Size());
        if(auto Controller=FX->GetSystemInstanceController())if(auto* Instance=Controller->GetSystemInstance_Unsafe())
            for(const auto& E:Instance->GetEmitters())CSV+=FString::Printf(TEXT(",%d"),E->GetNumParticles());
        CSV+=TEXT("\n");
        if(!SaveFrame(FString::Printf(TEXT("f%03d.png"),F)))return 12;
        if(F==170||F==250||F==354||F==382){const bool Visible=FX->IsVisible();FX->SetVisibility(false);if(!SaveFrame(FString::Printf(TEXT("off%03d.png"),F)))return 13;FX->SetVisibility(Visible);}
    }
    const bool Saved=FFileHelper::SaveStringToFile(CSV,*(Out/TEXT("frames.csv")));Capture->DestroyComponent();Core->Clear();
    UE_LOG(LogTemp,Display,TEXT("FIRE_REVIEW_FRAMES %s"),*Out);return Saved?0:14;
#endif
}
