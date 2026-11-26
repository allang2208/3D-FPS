// Explicit user-requested offline check. No automatic game/startup execution.
#include "KukriDecisiveComponent.h"
#if WITH_EDITOR
#include "../SwordTasselMeshComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "ImageUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "PreviewScene.h"
#include "RenderingThread.h"
#include "RHIGPUReadback.h"
#include "Serialization/JsonSerializer.h"

struct FKukriDecisiveGlowCheck
{
    static bool ReadCapture(UTextureRenderTarget2D* Target,const FString& Name,int32& BluePixels,int32& CrystalPixels)
    {
        auto* Resource=Target->GameThread_GetRenderTargetResource();
        FRHITexture* Source=Resource?Resource->GetRenderTargetTexture().GetReference():nullptr;
        if(!Source)return false;
        struct FPacket {TUniquePtr<FRHIGPUTextureReadback> Readback;TAtomic<bool> Done{false};TArray<FColor> Pixels;};
        auto Packet=MakeShared<FPacket,ESPMode::ThreadSafe>();Packet->Readback=MakeUnique<FRHIGPUTextureReadback>(TEXT("DecisiveGlow"));
        ENQUEUE_RENDER_COMMAND(DecisiveGlowCopy)([Packet,Source](FRHICommandListImmediate& Cmd)
        {Cmd.Transition(FRHITransitionInfo(Source,ERHIAccess::Unknown,ERHIAccess::CopySrc));Packet->Readback->EnqueueCopy(Cmd,Source);Cmd.Transition(FRHITransitionInfo(Source,ERHIAccess::CopySrc,ERHIAccess::SRVMask));});
        const int32 Width=Target->SizeX,Height=Target->SizeY;
        const double Deadline=FPlatformTime::Seconds()+10.;
        while(!Packet->Done.Load()&&FPlatformTime::Seconds()<Deadline)
        {
            ENQUEUE_RENDER_COMMAND(DecisiveGlowRead)([Packet,Width,Height](FRHICommandListImmediate& Cmd)
            {
                if(Packet->Done.Load()||!Packet->Readback->IsReady())return;
                int32 Pitch=0,Rows=0;const auto* Values=static_cast<const FFloat16Color*>(Packet->Readback->Lock(Pitch,&Rows));
                if(Values&&Pitch>=Width&&Rows>=Height)
                {Packet->Pixels.SetNumUninitialized(Width*Height);for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)Packet->Pixels[Y*Width+X]=Values[Y*Pitch+X].GetFloats().ToFColorSRGB();}
                if(Values)Packet->Readback->Unlock();Packet->Done.Store(true);
            });
            FlushRenderingCommands();FPlatformProcess::Sleep(.01f);
        }
        if(Packet->Pixels.Num()!=Width*Height)return false;
        // Fixed camera/framing: compare the crystal separately from the metal.
        // The old near-surface lamp can turn more frame pixels blue while the
        // crystal itself remains a tiny point; total coverage is not improvement.
        BluePixels=0;CrystalPixels=0;
        for(int32 Y=0;Y<Height;++Y)for(int32 X=0;X<Width;++X)
        {
            const auto& C=Packet->Pixels[Y*Width+X];
            const bool Blue=C.B>80&&int32(C.B)>int32(C.R)+24&&int32(C.B)>int32(C.G)+16;
            BluePixels+=Blue;CrystalPixels+=Blue&&X>=Width*.52f&&X<Width*.62f&&Y>=Height*.61f&&Y<Height*.75f;
        }
        TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(Width,Height,TArrayView64<const FColor>(Packet->Pixels.GetData(),Packet->Pixels.Num()),PNG);
        return FFileHelper::SaveArrayToFile(PNG,*Name);
    }
    static void Run()
    {
        const FString Folder=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("KukriDecisiveGlow20261031"));IFileManager::Get().MakeDirectory(*Folder,true);
        const FString Original=FCommandLine::Get();
        FCommandLine::Set(*(TEXT("DecisiveGlowCheck -ColdSteelProfile=SkillNetworkAudit_DecisiveGlow_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
        auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("DecisiveGlowCheck"));FCommandLine::Set(*Original);
        auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
        ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
        if(!World||!Model||!Model->IsAudit())return;
        World->TimeSeconds=10.f;
        auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
        auto Item=Model->CreateItem(TEXT("ue_kukri"));Item.Place=1;Item.Cell=6;
        TSharedPtr<FJsonObject> ItemData;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),ItemData);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("lanyard"),TEXT("kukri_lanyard_decisive"));ItemData->SetObjectField(TEXT("gunsmith_parts"),Parts);
        Item.Data.Reset();FJsonSerializer::Serialize(ItemData,TJsonWriterFactory<>::Create(&Item.Data));Seed.Items={Item};Model->AdoptNetMirror(Seed);
        auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();PC->SetPlayer(NewObject<ULocalPlayer>(GEngine));PC->Possess(Pawn);Model->AttachPawn(Pawn);
        auto* Effect=Pawn->FindComponentByClass<UKukriDecisiveComponent>();Effect->Configure(Model);
        auto* MeshAsset=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/Kukri20261020/PendantPrecision20261030/Decisive/SM_Kukri_DecisivePendant.SM_Kukri_DecisivePendant"));
        auto* Mesh=NewObject<USwordTasselMeshComponent>(Pawn);Mesh->SetupAttachment(Pawn->GetRootComponent());Mesh->SetStaticMesh(MeshAsset);Mesh->RegisterComponent();
        FString SpecText;FFileHelper::LoadFileToString(SpecText,*FPaths::Combine(FPaths::ProjectDir(),TEXT("SourceAssets/KukriPendantPrecision20261030/Decisive/model.json")));
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(SpecText),Data);Mesh->Configure(Data->GetObjectField(TEXT("spec")));Mesh->SetComponentTickEnabled(false);
        Effect->Visuals={{Mesh,Item.InstanceId,false}};
        TArray<TSharedPtr<FJsonValue>> Checks,Samples;int32 Failures=0;
        const auto Check=[&](bool OK,const FString& Name){auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);Checks.Add(MakeShared<FJsonValueObject>(R));Failures+=!OK;};
        Check(Effect->State.Blades.Num()==1&&Effect->Equipped.Contains(Item.InstanceId),TEXT("real installed pendant creates preparation state"));
        Check(MeshAsset&&MeshAsset->GetFName()==TEXT("SM_Kukri_DecisivePendant"),TEXT("current asset retains visual discovery identity"));
        // Render only this saved mesh in a dark isolated preview scene, using the
        // actual MIDs updated by Present(), with the game's modest bloom settings.
        FPreviewScene Studio(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(true).SetLightBrightness(.08f).SetSkyBrightness(.02f));
        auto* Display=Studio.GetWorld()->SpawnActor<AStaticMeshActor>();auto* DisplayMesh=Display->GetStaticMeshComponent();DisplayMesh->SetMobility(EComponentMobility::Movable);DisplayMesh->SetStaticMesh(MeshAsset);DisplayMesh->SetForcedLodModel(1);
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)DisplayMesh->SetMaterial(I,Mesh->GetMaterial(I));
        auto* PreviewLight=NewObject<UPointLightComponent>();PreviewLight->SetMobility(EComponentMobility::Movable);PreviewLight->SetCastShadows(false);PreviewLight->SetIntensityUnits(ELightUnits::Lumens);PreviewLight->SetInverseExposureBlend(1.f);PreviewLight->SetSourceRadius(.2f);PreviewLight->SetLightColor(FLinearColor(.12f,.38f,1.f));PreviewLight->SetAttenuationRadius(40.f);PreviewLight->SetIndirectLightingIntensity(0.f);Studio.AddComponent(PreviewLight,FTransform::Identity);PreviewLight->SetWorldLocation(FVector(2.76604,-.20,-6.4));PreviewLight->SetVisibility(false);
        auto* Target=NewObject<UTextureRenderTarget2D>();Target->AddToRoot();Target->RenderTargetFormat=RTF_RGBA16f;Target->ClearColor=FLinearColor(.001f,.001f,.001f,1);Target->InitAutoFormat(768,768);Target->UpdateResourceImmediate(true);
        auto* Capture=NewObject<USceneCaptureComponent2D>();Capture->AddToRoot();Capture->TextureTarget=Target;Capture->CaptureSource=SCS_FinalColorLDR;Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->FOVAngle=20.f;
        Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetMotionBlur(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=AEM_Manual;
        Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
        Capture->PostProcessSettings.bOverride_BloomIntensity=true;Capture->PostProcessSettings.BloomIntensity=.15f;Capture->PostProcessSettings.bOverride_BloomThreshold=true;Capture->PostProcessSettings.BloomThreshold=2.f;
        Studio.AddComponent(Capture,FTransform::Identity);Capture->SetWorldLocationAndRotation(FVector(2.0,30,-4.5),FRotator(0,-90,0));
        ON_SCOPE_EXIT {Studio.RemoveComponent(Capture);Capture->RemoveFromRoot();Capture->DestroyComponent();Studio.RemoveComponent(PreviewLight);PreviewLight->DestroyComponent();Studio.GetWorld()->DestroyActor(Display);Target->ReleaseResource();FlushRenderingCommands();Target->RemoveFromRoot();};
        FAssetCompilingManager::Get().FinishAllCompilation();
        const auto Render=[&](const FString& Name,int32& Pixels,int32& CrystalPixels)
        {
            for(int32 I=0;I<8;++I){++GFrameCounter;ENQUEUE_RENDER_COMMAND(DecisiveGlowFrame)([](FRHICommandListImmediate& Cmd){++GFrameNumberRenderThread;Cmd.EndFrame();});Studio.GetWorld()->SendAllEndOfFrameUpdates();Capture->CaptureScene();FlushRenderingCommands();}
            return ReadCapture(Target,FPaths::Combine(Folder,Name+TEXT(".png")),Pixels,CrystalPixels);
        };
        const double ReadyAt=Effect->State.Blades.IsEmpty()?12.5:Effect->State.Blades[0].ReadyAt;
        const float Ages[]={-.5f,0.f,1.2f,2.4f,3.6f};const TCHAR* Names[]={TEXT("charging"),TEXT("ready_flash"),TEXT("breath_peak"),TEXT("breath_trough"),TEXT("next_peak")};
        int32 PeakPixels=0,TroughPixels=0,ChargingPixels=0,PeakCrystal=0;
        for(int32 S=0;S<UE_ARRAY_COUNT(Ages);++S)
        {
            World->TimeSeconds=ReadyAt+Ages[S];Effect->Present();auto* M=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(1));
            const float Charge=M->K2_GetScalarParameterValue(TEXT("DecisiveCharge")),Pulse=M->K2_GetScalarParameterValue(TEXT("DecisiveReadyPulse")),Breath=M->K2_GetScalarParameterValue(TEXT("DecisiveBreath"));
            Check(FMath::IsNearlyEqual(Charge,S==0?.8f:1.f,.001f),FString(Names[S])+TEXT(" charge reaches live MID"));
            Check((S==1?Pulse>.99f:Pulse<.001f),FString(Names[S])+TEXT(" ready burst gate"));
            Check((S==2||S==4?Breath>.99f:Breath<.001f),FString(Names[S])+TEXT(" breath phase"));
            const bool Lit=Effect->Lights.Num()>0&&Effect->Lights[0]->IsVisible();Check(Lit==(S!=0),FString(Names[S])+TEXT(" local light visibility"));
            PreviewLight->SetVisibility(Lit);PreviewLight->SetIntensity(Lit?Effect->Lights[0]->Intensity:0.f);
            if(Lit)
            {
                const auto* LiveLight=Effect->Lights[0].Get();
                PreviewLight->SetUseInverseSquaredFalloff(LiveLight->bUseInverseSquaredFalloff);PreviewLight->SetIntensityUnits(LiveLight->IntensityUnits);
                PreviewLight->SetInverseExposureBlend(LiveLight->InverseExposureBlend);PreviewLight->SetAttenuationRadius(LiveLight->AttenuationRadius);
                PreviewLight->SetWorldLocation(Mesh->GetComponentTransform().InverseTransformPosition(LiveLight->GetComponentLocation()));
            }
            int32 Blue=0,CrystalBlue=0;Check(Render(Names[S],Blue,CrystalBlue),FString(Names[S])+TEXT(" actual UE material capture saved"));
            if(S==0)ChargingPixels=Blue;if(S==2){PeakPixels=Blue;PeakCrystal=CrystalBlue;}if(S==3)TroughPixels=Blue;
            auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("phase"),Names[S]);R->SetNumberField(TEXT("charge"),Charge);R->SetNumberField(TEXT("pulse"),Pulse);R->SetNumberField(TEXT("breath"),Breath);R->SetNumberField(TEXT("light_intensity_unitless"),Lit?Effect->Lights[0]->Intensity:0);R->SetNumberField(TEXT("blue_pixels"),Blue);R->SetNumberField(TEXT("crystal_blue_pixels"),CrystalBlue);Samples.Add(MakeShared<FJsonValueObject>(R));
        }
        Check(PeakPixels>ChargingPixels+50,TEXT("ready crystal visibly blue beyond charging state"));
        Check(TroughPixels>ChargingPixels+20,TEXT("breathing trough remains visibly lit"));
        int32 OldPixels=0,OldCrystal=0;
        PreviewLight->SetUseInverseSquaredFalloff(true);PreviewLight->SetIntensityUnits(ELightUnits::Lumens);PreviewLight->SetAttenuationRadius(40.f);PreviewLight->SetWorldLocation(FVector(2.76604,-.20,-6.4));PreviewLight->SetIntensity(8.f);PreviewLight->SetInverseExposureBlend(0.f);
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)
        {
            const FString Name=MeshAsset->GetStaticMaterials()[I].MaterialSlotName.ToString();
            const FString Path=TEXT("/Game/Weapons/Kukri20261020/DecisiveGlow20261031/Before/")+Name+TEXT(".")+Name;
            auto* Parent=LoadObject<UMaterialInterface>(nullptr,*Path);
            if(auto* Old=Parent?UMaterialInstanceDynamic::Create(Parent,Display):nullptr)
            {Old->SetScalarParameterValue(TEXT("DecisiveCharge"),1.f);Old->SetScalarParameterValue(TEXT("DecisiveFlash"),0.f);Old->SetScalarParameterValue(TEXT("DecisiveReadyPulse"),0.f);DisplayMesh->SetMaterial(I,Old);}
        }
        FAssetCompilingManager::Get().FinishAllCompilation();
        Check(Render(TEXT("before_ready"),OldPixels,OldCrystal),TEXT("same-mesh previous material comparison saved"));
        Check(PeakCrystal>OldCrystal+50,TEXT("new crystal has greater visible blue coverage than previous crystal"));
        Effect->EquipmentKey+=TEXT("_unequipped");Effect->Present();
        Check(Effect->Lights.Num()==0||!Effect->Lights[0]->IsVisible(),TEXT("equipment mismatch extinguishes light"));
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)if(auto* M=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(I)))Check(M->K2_GetScalarParameterValue(TEXT("DecisiveBreath"))==0&&M->K2_GetScalarParameterValue(TEXT("DecisiveReadyPulse"))==0,TEXT("equipment mismatch clears all visual layers"));
        auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("failures"),Failures);Report->SetArrayField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("samples"),Samples);Report->SetBoolField(TEXT("isolated_no_player_save"),true);Report->SetBoolField(TEXT("real_gameplay_input_or_network_tested"),false);Report->SetBoolField(TEXT("visual_registry_injected_for_isolated_check"),true);
        Report->SetNumberField(TEXT("previous_ready_blue_pixels"),OldPixels);
        Report->SetNumberField(TEXT("previous_crystal_blue_pixels"),OldCrystal);
        FString JSON;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&JSON));FFileHelper::SaveStringToFile(JSON,*FPaths::Combine(Folder,TEXT("result.json")));
        UE_LOG(LogTemp,Display,TEXT("DECISIVE_GLOW_CHECK %d checks, %d failures"),Checks.Num(),Failures);
    }
};
static FAutoConsoleCommand DecisiveGlowCheckCommand(TEXT("ColdSteel.CheckDecisiveGlow"),TEXT("Explicit isolated ready/breath material and point-light check."),FConsoleCommandDelegate::CreateStatic(&FKukriDecisiveGlowCheck::Run));
#endif
