#include "WeaponEquipWireAudit.h"
#include "LMGGripReview.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "ImageUtils.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

// Opt-in, disposable review world only. Never changes mesh assets or the pose graph.
void AWeaponEquipWireController::TickM249WristVisual()
{
    if(!IsLocalController()||!FParse::Param(FCommandLine::Get(),TEXT("M249WristCapture")))return;
    auto* Subject=Cast<AFPSGAMECharacter>(GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Subject||!Model||!Model->IsAudit()||!PlayerCameraManager)return;
    struct FVisualRun
    {
        FString Out;int32 Frame=0,RemoteFrame=0;double Next=0,RemoteNext=0,CloseNext=0;
        TWeakObjectPtr<USceneCaptureComponent2D> Remote;
        FString RemoteItem;
        int32 MountFrames=0;
    };
    static FVisualRun Run;
    const double Now=GetWorld()->GetRealTimeSeconds();
    const auto Write=[&](const TSharedRef<FJsonObject>& Row,const TCHAR* File)
    {
        FString Text;FJsonSerializer::Serialize(Row,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
        FFileHelper::SaveStringToFile(Text+TEXT("\n"),*(Run.Out/File),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);
    };
    if(Run.Out.IsEmpty())
    {
        FString Receipt;if(!FParse::Value(FCommandLine::Get(),TEXT("EquipWireOutput="),Receipt))return;
        Run.Out=FPaths::GetPath(Receipt)/FPaths::GetBaseFilename(Receipt)/TEXT("Visual");
        IFileManager::Get().MakeDirectory(*(Run.Out/TEXT("Owner")),true);
        IFileManager::Get().MakeDirectory(*(Run.Out/TEXT("Remote")),true);
        // Both peers create their own local lights and backdrop; the replicated pawn
        // remains driven by the real owner and server, without per-frame teleports.
        auto* Set=GetWorld()->SpawnActor<AActor>();auto* Root=NewObject<USceneComponent>(Set);
        Set->SetRootComponent(Root);Set->AddInstanceComponent(Root);Root->RegisterComponent();
        auto* Sun=NewObject<UDirectionalLightComponent>(Set);Set->AddInstanceComponent(Sun);Sun->SetupAttachment(Root);
        Sun->SetMobility(EComponentMobility::Movable);Sun->SetIntensity(3.f);Sun->SetCastShadows(false);Sun->SetWorldRotation(FRotator(-35,-30,0));Sun->RegisterComponent();
        auto* Sky=NewObject<USkyLightComponent>(Set);Set->AddInstanceComponent(Sky);Sky->SetupAttachment(Root);
        Sky->SetMobility(EComponentMobility::Movable);Sky->SetIntensity(1.f);Sky->RegisterComponent();
        for(double Y:{0.,500.})
        {
            auto* Fill=NewObject<UPointLightComponent>(Set);Set->AddInstanceComponent(Fill);Fill->SetupAttachment(Root);
            Fill->SetMobility(EComponentMobility::Movable);Fill->SetIntensity(5000.f);Fill->SetAttenuationRadius(1500.f);
            Fill->SetCastShadows(false);Fill->SetWorldLocation(FVector(130,Y-100,200));Fill->RegisterComponent();
        }
        for(int32 I=0;I<2;++I)
        {
            auto* Wall=GetWorld()->SpawnActor<AStaticMeshActor>();auto* Mesh=Wall->GetStaticMeshComponent();
            Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
            Mesh->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")));
            // Client prediction also needs a real floor, not just the authority's
            // non-replicated box. This fixture surface has the same top height.
            if(I)Mesh->SetCollisionProfileName(TEXT("BlockAll"));
            else Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Wall->SetActorLocation(I?FVector(0,250,-10):FVector(650,250,300));
            Wall->SetActorScale3D(I?FVector(100,100,.2):FVector(.2,100,100));
        }
        auto* PP=GetWorld()->SpawnActor<APostProcessVolume>();PP->bUnbound=true;
        PP->Settings.bOverride_AutoExposureMinBrightness=PP->Settings.bOverride_AutoExposureMaxBrightness=true;
        PP->Settings.AutoExposureMinBrightness=PP->Settings.AutoExposureMaxBrightness=1.f;
        PP->Settings.bOverride_DynamicGlobalIlluminationMethod=PP->Settings.bOverride_ReflectionMethod=true;
        PP->Settings.DynamicGlobalIlluminationMethod=EDynamicGlobalIlluminationMethod::None;
        PP->Settings.ReflectionMethod=EReflectionMethod::None;
        auto* Capture=NewObject<USceneCaptureComponent2D>(Set);Set->AddInstanceComponent(Capture);Capture->SetupAttachment(Root);
        Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;
        Capture->FOVAngle=FParse::Param(FCommandLine::Get(),TEXT("M249WristBaseOnly"))?38.f:60.f;Capture->RegisterComponent();
        auto* Target=NewObject<UTextureRenderTarget2D>(Capture);Target->InitCustomFormat(800,800,PF_B8G8R8A8,false);Capture->TextureTarget=Target;
        Run.Remote=Capture;
        UE_LOG(LogTemp,Display,TEXT("M249_WRIST_VISUAL_READY %s"),*Run.Out);
    }
    // Save the actual local player's viewport, including normal camera/FOV and HUD.
    // No animation resampling, mesh reposing, or camera substitution is performed.
    if(!bFinished&&Stage>=1&&CaseIndex<LMGGripReview::Count()&&Now>=Run.Next&&!FScreenshotRequest::IsScreenshotRequested())
    {
        Run.Next=Now+1./30.;
        const FString Image=FString::Printf(TEXT("%02d_%06d.png"),CaseIndex,Run.Frame++);
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),Image);
        Row->SetNumberField(TEXT("time"),Now);Row->SetNumberField(TEXT("case"),CaseIndex);
        Row->SetNumberField(TEXT("stage"),Stage);Row->SetNumberField(TEXT("stage_time"),Now-StageAt);
        Row->SetStringField(TEXT("definition"),Subject->ActiveInventoryWeaponDefinition);
        Row->SetStringField(TEXT("hand_l"),Subject->AKMViewmodel->GetSocketLocation(TEXT("hand_l")).ToString());
        Row->SetNumberField(TEXT("ads"),Subject->WeaponADSFactor);Row->SetBoolField(TEXT("reloading"),Subject->IsReloading());
        if(auto* Anim=Subject->GunplayAnimation.Get())
        {
            Row->SetNumberField(TEXT("source_time"),Anim->ActionTime);Row->SetNumberField(TEXT("action_alpha"),Anim->ActionAlpha);
            Row->SetStringField(TEXT("grip_profile"),GetPathNameSafe(Anim->GripProfile));
        }
        Row->SetStringField(TEXT("source_mesh"),GetPathNameSafe(Subject->AKMViewmodel->GetSkeletalMeshAsset()));
        Row->SetStringField(TEXT("camera"),PlayerCameraManager->GetCameraLocation().ToString());
        Row->SetNumberField(TEXT("fov"),PlayerCameraManager->GetFOVAngle());
        Write(Row,TEXT("owner.jsonl"));FScreenshotRequest::RequestScreenshot(Run.Out/TEXT("Owner")/Image,true,false);
    }
    // Opt-in close-ups of the current runtime-skinned owner mesh. These do not
    // sample or re-pose animation and are additional to the real player viewport.
    if(LMGGripReview::Enabled()&&!bFinished&&Stage>=1&&Run.Remote.IsValid()&&Now>=Run.CloseNext)
    {
        Run.CloseNext=Now+.5;auto* Capture=Run.Remote.Get();auto* Mesh=Subject->AKMViewmodel.Get();
        Capture->ClearShowOnlyComponents();Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
        Capture->ShowOnlyComponent(Mesh);
        TArray<USceneComponent*> Attached;Mesh->GetChildrenComponents(true,Attached);
        TArray<UPrimitiveComponent*> Visible;Visible.Add(Mesh);
        for(auto* C:Attached)if(auto* P=Cast<UPrimitiveComponent>(C);P&&P->IsVisible()){Visible.Add(P);Capture->ShowOnlyComponent(P);}
        TArray<bool> OnlyOwner;for(auto* P:Visible){OnlyOwner.Add(P->bOnlyOwnerSee);P->SetOnlyOwnerSee(false);}
        const FVector Focus=FMath::Lerp(Mesh->GetSocketLocation(TEXT("lowerarm_l")),Mesh->GetSocketLocation(TEXT("hand_l")),.82f);
        const FQuat Basis=FRotator(0,90,0).Quaternion();
        for(int32 View=0;View<2;++View)
        {
            const FVector Position=Focus+Basis.RotateVector(View?FVector(35,-8,14):FVector(-35,-8,14));
            Capture->FOVAngle=42.f;Capture->SetWorldLocationAndRotation(Position,(Focus-Position).Rotation());Capture->CaptureScene();
            TArray<FColor> Pixels;if(Capture->TextureTarget->GameThread_GetRenderTargetResource()->ReadPixels(Pixels))
            {
                const FString Dir=Run.Out/TEXT("Close");IFileManager::Get().MakeDirectory(*Dir,true);
                const FString Image=FString::Printf(TEXT("%02d_%06d_%d.png"),CaseIndex,Run.Frame,View);TArray<uint8> PNG;
                FImageUtils::CompressImageArray(800,800,Pixels,PNG);FFileHelper::SaveArrayToFile(PNG,*(Dir/Image));
                auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),Image);Row->SetNumberField(TEXT("time"),Now);Row->SetNumberField(TEXT("case"),CaseIndex);Row->SetNumberField(TEXT("stage"),Stage);
                Row->SetNumberField(TEXT("stage_time"),Now-StageAt);Row->SetNumberField(TEXT("ads"),Subject->WeaponADSFactor);
                if(auto* A=Subject->GunplayAnimation.Get())Row->SetNumberField(TEXT("source_time"),A->ActionTime);
                Write(Row,TEXT("close.jsonl"));
            }
        }
        for(int32 I=0;I<Visible.Num();++I)Visible[I]->SetOnlyOwnerSee(OnlyOwner[I]);
        Capture->ClearShowOnlyComponents();Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives;
        Capture->FOVAngle=60.f;
    }
    // Additional view of the remote replicated third-person body, not a cloned pose.
    if(Now>=Run.RemoteNext&&Run.Remote.IsValid())
    {
        Run.RemoteNext=Now+.1;
        for(TActorIterator<AFPSGAMECharacter> It(GetWorld());It;++It)
        {
            if(*It==Subject||It->IsLocallyControlled())continue;
            auto* Body=It->FindComponentByClass<UFPSPlayerBodyComponent>();if(!Body||Body->GetBodyState().WeaponInstance.IsEmpty())continue;
            auto* Capture=Run.Remote.Get();const FVector Focus=It->GetActorLocation()+FVector(20,0,35);
            const FVector Position=Focus+(FParse::Param(FCommandLine::Get(),TEXT("M249WristBaseOnly"))?FVector(75,-100,20):FVector(100,-145,30));
            Capture->SetWorldLocationAndRotation(Position,(Focus-Position).Rotation());
            Capture->CaptureScene();TArray<FColor> Pixels;
            if(Capture->TextureTarget->GameThread_GetRenderTargetResource()->ReadPixels(Pixels))
            {
                const FString Image=FString::Printf(TEXT("%06d.png"),Run.RemoteFrame++);TArray<uint8> PNG;
                FImageUtils::CompressImageArray(800,800,Pixels,PNG);FFileHelper::SaveArrayToFile(PNG,*(Run.Out/TEXT("Remote")/Image));
                const auto State=Body->GetBodyState();auto Row=MakeShared<FJsonObject>();
                Row->SetStringField(TEXT("image"),Image);Row->SetNumberField(TEXT("time"),Now);
                Row->SetStringField(TEXT("weapon_instance"),State.WeaponInstance);Row->SetNumberField(TEXT("action"),int32(State.Action));
                Row->SetBoolField(TEXT("aiming"),State.bAiming);
                if(Body->ReplicatedWeapons.Num())Row->SetStringField(TEXT("profile"),Body->ReplicatedWeapons[0].GripProfile.ToSoftObjectPath().ToString());
                if(LMGGripReview::Enabled())
                {
                    if(Run.RemoteItem!=State.WeaponInstance){Run.RemoteItem=State.WeaponInstance;Run.MountFrames=0;}
                    if(Run.MountFrames++<6)
                    {
                        TArray<TSharedPtr<FJsonValue>> Parts;
                        TInlineComponentArray<UStaticMeshComponent*> Statics(*It);
                        for(auto* Part:Statics)
                        {
                            if(!Part->GetStaticMesh()||!Part->IsVisible()||Part->bHiddenInGame||Part->bOnlyOwnerSee)continue;
                            auto Info=MakeShared<FJsonObject>();
                            Info->SetStringField(TEXT("mesh"),Part->GetStaticMesh()->GetName());
                            Info->SetStringField(TEXT("parent"),GetNameSafe(Part->GetAttachParent()));
                            Info->SetStringField(TEXT("socket"),Part->GetAttachSocketName().ToString());
                            const FVector Local=Capture->GetComponentTransform().InverseTransformPosition(Part->Bounds.Origin);
                            if(Local.X>0.)
                            {
                                const double Focal=400./FMath::Tan(FMath::DegreesToRadians(Capture->FOVAngle*.5));
                                Info->SetNumberField(TEXT("screen_x"),400.+Focal*Local.Y/Local.X);
                                Info->SetNumberField(TEXT("screen_y"),400.-Focal*Local.Z/Local.X);
                            }
                            Parts.Add(MakeShared<FJsonValueObject>(Info));
                        }
                        Row->SetArrayField(TEXT("visible_parts"),Parts);
                    }
                }
                Write(Row,TEXT("remote.jsonl"));
            }
            break;
        }
    }
}
