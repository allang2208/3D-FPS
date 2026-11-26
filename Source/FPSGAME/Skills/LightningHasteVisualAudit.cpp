#include "SkillNetworkAuditCommandlet.h"
#if WITH_EDITOR
#include "FPSLightningHasteComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SplineComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "ImageUtils.h"
#include "FXSystem.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
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

int32 USkillNetworkAuditCommandlet::CaptureLightningHaste(const FString& Params)
{
#if !WITH_EDITOR
    return 2;
#else
    FString Out;if(!FParse::Value(*Params,TEXT("Out="),Out)||!FApp::CanEverRender())return 2;
    IFileManager::Get().MakeDirectory(*Out,true);
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_HasteVisual_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Append(*(TEXT(" -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("LightningHasteVisualAudit"));
    auto* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();FCommandLine::Set(*Original);};
    auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!World->Scene||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 3;
    if(!World->FXSystem)World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    FlushRenderingCommands();if(!FNiagaraGpuComputeDispatchInterface::Get(World))return 4;
    World->InitializeActorsForPlay(FURL());
    FString JsonText;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(JsonText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(JsonText),Config))return 5;
    auto* BodyAsset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    const auto Clips=Config->GetObjectField(TEXT("clips"));
    auto* Idle=LoadObject<UAnimSequence>(nullptr,*Clips->GetStringField(TEXT("Unarmed.Idle")));
    auto* Walk=LoadObject<UAnimSequence>(nullptr,*Clips->GetStringField(TEXT("Unarmed.Walk.Fwd")));
    auto* System=LoadObject<UNiagaraSystem>(nullptr,LightningHasteAssets::Arc);
    if(!BodyAsset||!Idle||!Walk||!System)return 6;
    System->WaitForCompilationComplete(true,false);
    auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.DungeonRun={};
    auto Item=Model->CreateItem(TEXT("ue_frost_crystal_sword"));Item.Place=1;Item.Cell=6;State.Items.Add(Item);Model->AdoptNetMirror(State);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,100),FRotator::ZeroRotator);
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->Possess(Pawn);
    Pawn->SetActorTickEnabled(false);for(auto* C:Pawn->GetComponents())C->SetComponentTickEnabled(false);
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();Body->Character=Pawn;Body->Configuration=Config;
    auto* Skin=Pawn->GetMesh();Skin->SetSkeletalMesh(BodyAsset);Skin->SetRelativeLocation(FVector(0,0,-96));Skin->SetRelativeRotation(FRotator(0,-90,0));
    Skin->SetVisibility(true);Skin->SetHiddenInGame(false);Skin->SetOwnerNoSee(false);Skin->SetOnlyOwnerSee(false);Skin->PlayAnimation(Idle,true);
    Skin->SetPlayRate(0);Skin->SetPosition(.1f,false);Skin->TickAnimation(0,false);Skin->RefreshBoneTransforms();Body->InitializeFirstPersonLowerBody();
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Sword->RefreshEquipment(Model);Sword->CancelAction();Sword->SetClip(TEXT("Idle"),true);Sword->SamplePose(0);
    auto* Arms=Sword->Viewmodel.Get();if(!Arms||!Arms->GetSkeletalMeshAsset()||!Body->FirstPersonLowerBody)return 7;
    auto* Haste=Pawn->FindComponentByClass<UFPSLightningHasteComponent>();Haste->ArcSystem=System;
    Haste->State.Cast=Model->LightningHasteStats();Haste->State.bActive=true;Haste->State.StartedAt=Haste->Clock()-.5;

    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(0,400,100),FRotator::ZeroRotator);
    auto* RemotePC=World->SpawnActor<ASkillAuditRemoteController>();RemotePC->Possess(Remote);
    Remote->SetActorTickEnabled(false);for(auto* C:Remote->GetComponents())C->SetComponentTickEnabled(false);
    auto* RemoteBody=Remote->FindComponentByClass<UFPSPlayerBodyComponent>();RemoteBody->Character=Remote;
    auto* RemoteSkin=Remote->GetMesh();RemoteSkin->SetSkeletalMesh(BodyAsset);RemoteSkin->SetRelativeLocation(FVector(0,0,-96));RemoteSkin->SetRelativeRotation(FRotator(0,-90,0));
    RemoteSkin->SetVisibility(true);RemoteSkin->SetHiddenInGame(false);RemoteSkin->SetOwnerNoSee(false);RemoteSkin->PlayAnimation(Idle,true);RemoteSkin->SetPlayRate(0);
    auto* RemoteHaste=Remote->FindComponentByClass<UFPSLightningHasteComponent>();RemoteHaste->ArcSystem=System;
    RemoteHaste->State=Haste->State;
    auto* Rig=World->SpawnActor<AActor>();
    for(int32 I=0;I<2;++I){auto* L=NewObject<UDirectionalLightComponent>(Rig);Rig->AddInstanceComponent(L);L->SetIntensity(I?2.f:4.f);L->SetWorldRotation(FRotator(-35,I?160.f:-20.f,0));L->RegisterComponent();}
    auto* Capture=NewObject<USceneCaptureComponent2D>(Rig);Rig->AddInstanceComponent(Capture);
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->bAlwaysPersistRenderingState=true;Capture->CaptureSource=SCS_FinalColorLDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    auto* Target=NewObject<UTextureRenderTarget2D>(Rig);Target->ClearColor=FLinearColor(.025f,.03f,.04f);Target->InitCustomFormat(720,720,PF_B8G8R8A8,false);Target->UpdateResourceImmediate(true);Capture->TextureTarget=Target;
    Capture->RegisterComponent();Capture->FOVAngle=52.f;Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetTemporalAA(false);
    auto& PP=Capture->PostProcessSettings;PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=0;PP.bOverride_BloomIntensity=true;PP.BloomIntensity=.25f;
    FlushAsyncLoading();FAssetCompilingManager::Get().FinishAllCompilation();if(GShaderCompilingManager)GShaderCompilingManager->FinishAllCompilation();
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Save=[&](const FString& Name,USkeletalMeshComponent* Mesh,UFPSLightningHasteComponent* C,int32 Begin,int32 End,FVector Center,float Distance,bool ShowMesh=true)
    {
        Capture->ClearShowOnlyComponents();if(ShowMesh)Capture->ShowOnlyComponent(Mesh);
        // SceneCapture has no owning player. Record runtime flags before exposing them to this inspection camera.
        const bool Only=Mesh->bOnlyOwnerSee;Mesh->SetOnlyOwnerSee(false);
        const auto Kind=Mesh->FirstPersonPrimitiveType;Mesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::None);
        for(int32 I=Begin;I<End&&I<C->ArcFX.Num();++I)Capture->ShowOnlyComponent(C->ArcFX[I]);
        const FVector Camera=Center+FVector(Distance,Distance*.25,Distance*.15);Capture->SetWorldLocationAndRotation(Camera,(Center-Camera).Rotation());
        World->SendAllEndOfFrameUpdates();Capture->CaptureScene();FlushRenderingCommands();TArray<FColor> Pixels;
        bool OK=Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)&&Pixels.Num()==720*720;
        if(OK){for(auto& Pixel:Pixels)Pixel.A=255;TArray64<uint8> Bytes;FImageUtils::PNGCompressImageArray(720,720,Pixels,Bytes);OK=FFileHelper::SaveArrayToFile(Bytes,*(Out/Name));}
        Mesh->SetOnlyOwnerSee(Only);Mesh->SetFirstPersonPrimitiveType(Kind);return OK;
    };
    const auto Record=[&](UFPSLightningHasteComponent* C,const TCHAR* Mode,int32 Frame)
    {
        for(int32 I=0;I<C->ArcFX.Num();++I)
        {
            auto* FX=C->ArcFX[I].Get();auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("mode"),Mode);Row->SetNumberField(TEXT("frame"),Frame);Row->SetNumberField(TEXT("limb"),I);
            Row->SetStringField(TEXT("source"),GetPathNameSafe(C->LimbMeshes[I].Get()));Row->SetStringField(TEXT("root"),C->LimbRoots[I].ToString());Row->SetStringField(TEXT("tip"),C->LimbTips[I].ToString());
            Row->SetBoolField(TEXT("active"),FX->IsActive());Row->SetBoolField(TEXT("visible"),FX->IsVisible());Row->SetNumberField(TEXT("spline_cm"),C->ArcPaths[I]->GetSplineLength());
            Row->SetStringField(TEXT("path_transform"),C->ArcPaths[I]->GetComponentTransform().ToString());
            Row->SetStringField(TEXT("fx_bounds"),FX->Bounds.GetBox().ToString());
            if(!C->ArcPaths[I]->GetComponentScale().Equals(FVector::OneVector,.001))++Failures;
            if(auto* Source=C->LimbMeshes[I].Get())
            {
                if(auto* Leader=Source->LeaderPoseComponent.Get())
                {
                    const bool Ordered=C->PrimaryComponentTick.GetPrerequisites().ContainsByPredicate([&](const FTickPrerequisite& P){return P.PrerequisiteObject.Get()==Leader;});
                    Row->SetBoolField(TEXT("pose_leader_ordered"),Ordered);if(!Ordered)++Failures;
                }
                const FVector FirstPoint=C->ArcPaths[I]->GetLocationAtSplinePoint(0,ESplineCoordinateSpace::World);
                const FVector LastPoint=C->ArcPaths[I]->GetLocationAtSplinePoint(C->ArcPaths[I]->GetNumberOfSplinePoints()-1,ESplineCoordinateSpace::World);
                Row->SetNumberField(TEXT("root_distance_cm"),FVector::Dist(FirstPoint,Source->GetSocketLocation(C->LimbRoots[I])));
                Row->SetNumberField(TEXT("tip_distance_cm"),FVector::Dist(LastPoint,Source->GetSocketLocation(C->LimbTips[I])));
            }
            TArray<TSharedPtr<FJsonValue>> Counts,Execution,Bounds;int32 Total=0;
            if(auto Controller=FX->GetSystemInstanceController())if(auto* Instance=Controller->GetSystemInstance_Unsafe())
                for(const auto& E:Instance->GetEmitters()){const int32 N=E->GetNumParticles();Counts.Add(MakeShared<FJsonValueNumber>(N));Execution.Add(MakeShared<FJsonValueNumber>(int32(E->GetExecutionState())));Bounds.Add(MakeShared<FJsonValueString>(E->GetBounds().ToString()));Total+=N;}
            Row->SetArrayField(TEXT("emitter_particles"),Counts);Row->SetNumberField(TEXT("total_particles"),Total);
            Row->SetArrayField(TEXT("emitter_execution"),Execution);
            Row->SetArrayField(TEXT("emitter_bounds"),Bounds);
            if(Frame<100&&(!FX->IsActive()||!FX->IsVisible()||Total==0))++Failures;
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    };
    constexpr float Dt=1.f/60.f;
    for(int32 F=0;F<120;++F)
    {
        ++GFrameCounter;World->Tick(LEVELTICK_TimeOnly,Dt);
        const bool Moving=F>=40&&F<100;
        Pawn->GetCharacterMovement()->Velocity=Remote->GetCharacterMovement()->Velocity=Moving?FVector(500,0,0):FVector::ZeroVector;
        if(F==40){Skin->PlayAnimation(Walk,true);Skin->SetPlayRate(0);RemoteSkin->PlayAnimation(Walk,true);RemoteSkin->SetPlayRate(0);}
        for(auto* M:{Skin,RemoteSkin}){M->SetPosition(F*Dt,false);M->TickAnimation(0,false);M->RefreshBoneTransforms();}
        Sword->SamplePose(F*Dt);
        if(F==100){Haste->State.StartedAt=Haste->Clock()-Haste->State.Cast.Duration+.2;RemoteHaste->State.StartedAt=Haste->State.StartedAt;}
        Haste->UpdateVisuals(Dt);RemoteHaste->UpdateVisuals(Dt);
        for(auto* C:{Haste,RemoteHaste})for(auto FX:C->ArcFX)
        {
            FX->SetOnlyOwnerSee(false);FX->SetOwnerNoSee(false);FX->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::None);
            FX->SetForceSolo(true);if(FX->IsActive())FX->AdvanceSimulation(1,Dt);
        }
        if(F==5||F==30||F==70||F==108||F==118)
        {
            Record(Haste,TEXT("owner"),F);Record(RemoteHaste,TEXT("remote"),F);
            const FVector Hands=(Arms->GetSocketLocation(TEXT("hand_l"))+Arms->GetSocketLocation(TEXT("hand_r")))*.5;
            const FVector Feet=(Skin->GetSocketLocation(TEXT("foot_l"))+Skin->GetSocketLocation(TEXT("foot_r")))*.5+FVector(0,0,20);
            if(!Save(FString::Printf(TEXT("hands_%03d.png"),F),Arms,Haste,0,2,Hands,95))++Failures;
            if(!Save(FString::Printf(TEXT("feet_%03d.png"),F),Skin,Haste,2,4,Feet,150))++Failures;
            if(!Save(FString::Printf(TEXT("remote_%03d.png"),F),RemoteSkin,RemoteHaste,0,4,Remote->GetActorLocation(),260))++Failures;
            if(F==70)
            {
                Save(TEXT("hands_fx_only.png"),Arms,Haste,0,2,Hands,95,false);
                Save(TEXT("hands_fx_wide.png"),Arms,Haste,0,2,Pawn->GetActorLocation(),350,false);
                Save(TEXT("hands_reverse.png"),Arms,Haste,0,2,Hands,-95);
                for(auto* C:{Haste,RemoteHaste})for(auto FX:C->ArcFX)FX->SetVisibility(false);
                Save(TEXT("hands_off.png"),Arms,Haste,0,2,Hands,95);Save(TEXT("feet_off.png"),Skin,Haste,2,4,Feet,150);
            }
        }
    }
    if(Haste->ArcFX.Num()||RemoteHaste->ArcFX.Num())++Failures;
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("failures"),Failures);Result->SetArrayField(TEXT("samples"),Rows);
    Result->SetStringField(TEXT("system"),System->GetPathName());Result->SetBoolField(TEXT("isolated_scene_capture"),true);Result->SetBoolField(TEXT("real_network_transport"),false);
    FString Output;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Out/TEXT("result.json")));
    Capture->DestroyComponent();Haste->ClearVisuals();RemoteHaste->ClearVisuals();
    UE_LOG(LogTemp,Display,TEXT("HASTE_VISUAL samples=%d failures=%d out=%s"),Rows.Num(),Failures,*Out);
    return Failures?1:0;
#endif
}
