#include "M24HoldReviewCommandlet.h"
#include "M24SurfaceReview.h"
int32 RunM249ReloadReview(const FString& ManifestPath, const FString& Output);
#if WITH_EDITOR
#include "M24WeaponAssets.h"
#include "M24Attachments.h"
#include "SVDWeaponAssets.h"
#include "M249WeaponAssets.h"
#include "M249BipodAnimation.h"
#include "PKMBipodComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "PKMLowpolyWeaponAssets.h"
#include "RifleHipFraming.h"
#include "../UI/ColdSteelPreviewScene.h"
#include "../UI/GunsmithPreviewLighting.h"
#include "../Characters/FPSArmJointCorrectiveComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "AssetCompilingManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "ContentStreaming.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Engine/Texture.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "RenderingThread.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "SkeletalRenderPublic.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "ShaderCompiler.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"
#endif

int32 UM24HoldReviewCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    FString Output;
    if (!FParse::Value(*Params,TEXT("Output="),Output)) return 1;
    FString ReloadManifest;
    if (FParse::Value(*Params,TEXT("M249ReloadManifest="),ReloadManifest))
        return RunM249ReloadReview(ReloadManifest,Output);
    FString SurfaceManifest;
    if (FParse::Value(*Params,TEXT("SurfaceManifest="),SurfaceManifest))
        return RunM24SurfaceReview(SurfaceManifest,Output);
    float SoftboxScale=.15f,Exposure=-.25f;
    FParse::Value(*Params,TEXT("SoftboxScale="),SoftboxScale);
    FParse::Value(*Params,TEXT("Exposure="),Exposure);
    IFileManager::Get().MakeDirectory(*Output,true);
    FString Failure;
    auto Studio=FColdSteelPreviewScene::TryCreate(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false).SetForceMipsResident(true).SetLightBrightness(2.5f).SetSkyBrightness(.8f),Failure);
    if (!Studio) return 2;
    UWorld* World=Studio->GetWorld(); World->SetShouldTick(false);
    Studio->SetSkyCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
    // A local transient pawn permits the existing corrective driver to run exactly as in-game.
    APawn* Owner=World->SpawnActor<APawn>();
    APlayerController* Controller=World->SpawnActor<APlayerController>();
    Controller->SetAsLocalPlayerController();
    Controller->Possess(Owner);
    auto* Rig=NewObject<USkeletalMeshComponent>(Owner); Owner->AddInstanceComponent(Rig); Owner->SetRootComponent(Rig);
    Rig->SetForcedLOD(1); Rig->SetCastShadow(false); Studio->AddComponent(Rig,FTransform::Identity);
    auto* Correctives=NewObject<UFPSArmJointCorrectiveComponent>(Owner);
    Owner->AddInstanceComponent(Correctives); Correctives->RegisterComponent();
    TStrongObjectPtr<USceneCaptureComponent2D> Capture(NewObject<USceneCaptureComponent2D>(GetTransientPackage()));
    TStrongObjectPtr<UTextureRenderTarget2D> Target(NewObject<UTextureRenderTarget2D>(GetTransientPackage()));
    Target->RenderTargetFormat=RTF_RGBA8_SRGB;Target->ClearColor=FLinearColor(.045f,.055f,.07f,1);
    Target->InitAutoFormat(1280,720);Target->UpdateResourceImmediate(true);
    Capture->TextureTarget=Target.Get();Capture->CaptureSource=SCS_FinalColorLDR;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->bAlwaysPersistRenderingState=true;
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetVolumetricFog(false);
    Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetBloom(false);Capture->ShowFlags.SetTemporalAA(true);
    Capture->ShowFlags.SetAntiAliasing(true);Capture->ShowFlags.SetLighting(true);Capture->ShowFlags.SetMaterials(true);
    Capture->FOVAngle=FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(37.5f))*16.f/9.f));
    Capture->bOverride_CustomNearClippingPlane=true;Capture->CustomNearClippingPlane=1.f;
    auto& PP=Capture->PostProcessSettings;
    PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=Exposure;PP.bOverride_FilmGrainIntensity=true;PP.FilmGrainIntensity=0;
    Studio->AddComponent(Capture.Get(),FTransform::Identity);
    auto* Fill=NewObject<UDirectionalLightComponent>(GetTransientPackage());Fill->SetIntensity(.25f);
    Fill->SetLightColor(FLinearColor(.82f,.91f,1.f));Fill->SetCastShadows(false);
    Studio->AddComponent(Fill,FTransform(FRotator(-15,150,0)));
    GunsmithPreviewLighting::Create(*Studio,*Capture);
    TArray<TSharedPtr<FJsonValue>> Results;
    const bool bM249=FParse::Param(*Params,TEXT("M249"));
    const bool bM249Side=bM249&&FParse::Param(*Params,TEXT("M249Side"));
    const bool bM249Focus=bM249&&FParse::Param(*Params,TEXT("M249Focus"));
    FString ReviewRole=TEXT("reload"),ReviewTimes=TEXT("0.4,0.5,0.6,0.8,1.0,1.2,1.6,2.2"),ReviewView=TEXT("left");
    FParse::Value(*Params,TEXT("Role="),ReviewRole);FParse::Value(*Params,TEXT("Times="),ReviewTimes);FParse::Value(*Params,TEXT("View="),ReviewView);
    ReviewTimes.ReplaceInline(TEXT("|"),TEXT(",")); // FParse treats commas as command-line terminators.
    const bool bBipod=bM249Focus&&ReviewRole==TEXT("bipod");
    const bool bRetract=bBipod&&FParse::Param(*Params,TEXT("Retract"));
    auto Binary=[&](const auto& Values,const FString& Name)
    {
        const TArrayView<const uint8> Bytes(reinterpret_cast<const uint8*>(Values.GetData()),Values.Num()*sizeof(Values[0]));
        return FFileHelper::SaveArrayToFile(Bytes,*(Output/Name));
    };
    for (bool bM24 : bM249 ? TArray<bool>{false} : TArray<bool>{false,true})
    {
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,bM249?M249WeaponAssets::MeshPath:bM24?M24WeaponAssets::MeshPath:SVDWeaponAssets::MeshPath);
        auto* Idle=LoadObject<UAnimSequence>(nullptr,*(bM249?M249WeaponAssets::AnimationPath(TEXT("idle")):bM24?M24WeaponAssets::AnimationPath(TEXT("idle")):SVDWeaponAssets::AnimationPath(TEXT("idle"))));
        if (!Mesh||!Idle) return 3;
        FRifleHipFraming Framing;Framing.Initialize(bM249?M249WeaponAssets::Definition:bM24?M24WeaponAssets::Definition:SVDWeaponAssets::Definition,Idle,FVector(0,7,-7),FRotator(0,90,0),FVector::OneVector,false);
        if (!bM249 && !Framing.IsReady()) return 4;
        Rig->SetSkeletalMeshAsset(Mesh);Rig->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        const FVector Hip=bM249?FVector(9,9,-11):Framing.Location(FVector::ZeroVector);
        const FQuat Base=bM249?FRotator(0,90,0).Quaternion():Framing.Rotation(FQuat::Identity);
        Rig->SetWorldTransform(FTransform(Base,Hip));
        Rig->PlayAnimation(Idle,true);Rig->SetPlayRate(0);Rig->SetPosition(0,false);Rig->TickAnimation(0,false);Rig->RefreshBoneTransforms();
        Capture->ClearShowOnlyComponents();Capture->ShowOnlyComponent(Rig);
        if(bM249Focus&&ReviewView==TEXT("ads"))
        {
            UMaterialInstanceDynamic* Colors[2];
            auto* BackdropMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
            for(int32 I=0;I<2;++I)
            {
                Colors[I]=UMaterialInstanceDynamic::Create(BackdropMaterial,Owner);
                Colors[I]->SetVectorParameterValue(TEXT("Color"),I?FLinearColor(.9f,.9f,.9f):FLinearColor(.02f,.02f,.02f));
            }
            auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
            for(int32 Y=-6;Y<=6;++Y)for(int32 Z=-6;Z<=6;++Z)
            {
                auto* Tile=NewObject<UStaticMeshComponent>(Owner);Tile->SetStaticMesh(Cube);Tile->SetMaterial(0,Colors[(Y+Z+12)%2]);
                Tile->SetCollisionEnabled(ECollisionEnabled::NoCollision);Tile->SetCastShadow(false);
                Studio->AddComponent(Tile,FTransform(FQuat::Identity,FVector(300.,Y*10.,Z*10.),FVector(.01,.1,.1)));
                Capture->ShowOnlyComponent(Tile);
            }
        }
        TArray<UStaticMeshComponent*> Parts;
        UPKMBipodComponent* Bipod=nullptr;
        UFPSGunplayAnimInstance* BipodAnim=nullptr;
        if(bBipod)
        {
            PKMLowpolyWeaponAssets::ConfigureBipod(Owner,Rig,true);
            Bipod=Cast<UPKMBipodComponent>(PKMLowpolyWeaponAssets::FindBipod(Owner));
            if(!Bipod)return 20;
            TInlineComponentArray<UStaticMeshComponent*> Mounted(Owner);
            for(auto* Part:Mounted)if(Part==Bipod||Part->GetAttachParent()==Bipod){Parts.Add(Part);Capture->ShowOnlyComponent(Part);}
            const int32 Material=Rig->GetMaterialIndex(TEXT("M249_Bipod"));
            const auto& LOD=Mesh->GetResourceForRendering()->LODRenderData[0];
            for(int32 S=0;S<LOD.RenderSections.Num();++S)if(LOD.RenderSections[S].MaterialIndex==Material)Rig->ShowMaterialSection(Material,S,false,0);
            Rig->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());
            BipodAnim=Cast<UFPSGunplayAnimInstance>(Rig->GetAnimInstance());if(!BipodAnim)return 21;
            BipodAnim->IdleClip=Idle;
            BipodAnim->GripProfile=LoadObject<UWeaponGripProfile>(nullptr,M249BipodAnimation::SupportProfile);
            BipodAnim->AimClip=LoadObject<UAnimSequence>(nullptr,*M249WeaponAssets::AnimationPath(TEXT("aim")));
            BipodAnim->ActionGripProfile=LoadObject<UWeaponGripProfile>(nullptr,M249BipodAnimation::Profile);
        }
        if (bM24) for (const auto* Key:{M24Attachments::Scope,M24Attachments::Suppressor,M24Attachments::CheekRest})
        {
            auto* Part=M24Attachments::Configure(Owner,Rig,nullptr,Key,true);
            if (!Part) return 5;
            Parts.Add(Part);Capture->ShowOnlyComponent(Part);
        }
        FAssetCompilingManager::Get().FinishAllCompilation();
        if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
        if(bM249)
        {
            Rig->SetTextureForceResidentFlag(true);Rig->PrestreamTextures(30.f,true);
            World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
            UTexture::ForceUpdateTextureStreaming();IStreamingManager::Get().StreamAllResources(0.f);
        }
        Studio->UpdateCaptureContents();
        FBox Assembly=Rig->Bounds.GetBox();
        for(const auto* Part:Parts)Assembly+=Part->Bounds.GetBox();
        GunsmithPreviewLighting::Update(*Capture,Assembly,false,SoftboxScale);
        struct FSample {const TCHAR* Role;float Time;bool ADS=false;};
        TArray<FSample> Samples={{TEXT("idle"),0.f}};
        if(bM249)Samples.Append({{TEXT("idle"),0.f,true},{TEXT("reload"),1.6f},{TEXT("reload"),2.17f},{TEXT("reload"),4.7f},
            {TEXT("reload_empty"),5.13f},{TEXT("reload_empty"),5.36f},{TEXT("reload_empty"),5.78f}});
        if(bM24)Samples.Append({{TEXT("idle"),1.f},{TEXT("aim"),0.f},{TEXT("fire"),1.f},{TEXT("cycle"),1.f},{TEXT("reload"),1.f},{TEXT("reload_empty"),65.f/30.f},{TEXT("equip"),.8f},{TEXT("inspect"),1.5f},{TEXT("quick_melee"),.9f}});
        if(bM249Focus)
        {
            Samples.Reset();
            if(ReviewView==TEXT("ads"))Samples.Add({TEXT("idle"),0.f,true});
            else {TArray<FString> Times;ReviewTimes.ParseIntoArray(Times,TEXT(","));for(const auto& Time:Times)Samples.Add({*ReviewRole,FCString::Atof(*Time)});}
            const auto& LOD=Mesh->GetResourceForRendering()->LODRenderData[0];TArray<uint32> Indices;LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);Binary(Indices,TEXT("surface.indices"));
            TArray<uint32> Materials;Materials.Init(0,Indices.Num()/3);TArray<uint8> Left;Left.Init(0,LOD.GetNumVertices());
            const auto* Weights=Rig->GetSkinWeightBuffer(0);const auto& Ref=Mesh->GetRefSkeleton();
            for(const auto& Section:LOD.RenderSections)
            {
                for(uint32 T=Section.BaseIndex/3;T<Section.BaseIndex/3+Section.NumTriangles;++T)Materials[T]=Section.MaterialIndex;
                for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
                {
                    int32 Best=-1;uint16 Max=0;
                    for(uint32 J=0;J<Weights->GetMaxBoneInfluences();++J)if(Weights->GetBoneWeight(V,J)>Max){Max=Weights->GetBoneWeight(V,J);Best=Section.BoneMap[Weights->GetBoneIndex(V,J)];}
                    Left[V]=Best>=0&&Ref.GetBoneName(Best).ToString().EndsWith(TEXT("_l"));
                }
            }
            Binary(Materials,TEXT("surface.materials"));Binary(Left,TEXT("surface.left"));
        }
        for(const auto& Sample:Samples)
        {
            auto* Clip=LoadObject<UAnimSequence>(nullptr,*(bBipod?FString(TEXT("/Game/Weapons/M249/Bipod/A_M249_Bipod")):bM249?M249WeaponAssets::AnimationPath(Sample.Role):bM24?M24WeaponAssets::AnimationPath(Sample.Role):SVDWeaponAssets::AnimationPath(Sample.Role)));
            if (!Clip) return 6;
            Capture->SetWorldTransform(FTransform::Identity);
            if(bM249Side)Capture->FOVAngle=50.f;
            if(bM249Focus)Capture->FOVAngle=ReviewView==TEXT("ads")?FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(27.5f))*16.f/9.f)):ReviewView==TEXT("player")?107.5f:48.f;
            if(bM249)Rig->SetWorldTransform(FTransform(Base,FCString::Strncmp(Sample.Role,TEXT("reload"),6)==0?FVector(10,0,-5):Hip));
            if(!bBipod){Rig->PlayAnimation(Clip,true);Rig->SetPlayRate(0);}
            const float BipodPhase=FMath::Clamp(bRetract?1.f-Sample.Time/M249BipodAnimation::Duration:Sample.Time/M249BipodAnimation::Duration,0.f,1.f);
            const float BipodTime=BipodPhase*M24Bipod::PoseDuration;
            if(bBipod)
            {
                BipodAnim->BaseTime=0.f;BipodAnim->ActionClip=Clip;BipodAnim->ActionTime=BipodTime;
                BipodAnim->ActionAlpha=M24Bipod::Ease(0.f,.025f,BipodTime)*(1.f-M24Bipod::Ease(.44f,M24Bipod::PoseDuration,BipodTime));
                BipodAnim->AimAlpha=M24Bipod::Seat(BipodPhase)*(bRetract?1.f-M24Bipod::Ease(0.f,.22f,Sample.Time):1.f);
            }
            for(int32 Frame=0;Frame<12;++Frame)
            {
                ++GFrameCounter;
                World->Tick(LEVELTICK_All,1.f/60.f);
                if(!bBipod)Rig->SetPosition(Sample.Time,false);
                Rig->TickAnimation(0,false);Rig->RefreshBoneTransforms();Rig->UpdateComponentToWorld();
                if(bBipod)Bipod->SetM249DeploymentWeight(M249BipodAnimation::LegWeight(BipodPhase));
                if(bM249)
                {
                    PKMLowpolyWeaponAssets::SetSections(Rig,FCString::Strncmp(Sample.Role,TEXT("reload"),6)==0,
                        FCString::Strcmp(Sample.Role,TEXT("reload_empty"))==0,Sample.Time,100);
                    if(bBipod&&ReviewView==TEXT("player"))
                    {
                        const FVector Rear=Rig->GetSocketTransform(TEXT("WPN_RearSight"),RTS_Component).GetLocation();
                        const FVector Axis=(Rig->GetSocketTransform(TEXT("WPN_FrontSight"),RTS_Component).GetLocation()-Rear).GetSafeNormal();
                        const FVector Up=Rig->GetSocketTransform(TEXT("WPN_root"),RTS_Component).GetRotation().RotateVector(M249WeaponAssets::SightUp);
                        const FQuat Align=FRotationMatrix::MakeFromXZ(Axis,Up).ToQuat().Inverse();
                        FTransform Framed;Framed.Blend(FTransform(Base,Hip),FTransform(Align,FVector(20.,0,0)-Align.RotateVector(Rear)),BipodAnim->AimAlpha);
                        Rig->SetWorldTransform(Framed);
                    }
                    if(Sample.ADS)
                    {
                        if(bM249Focus)
                        {
                            // The same complete-frame calibration used by UpdateADSPose;
                            // keep the camera fixed, moving the viewmodel as gameplay does.
                            const FVector Rear=Rig->GetSocketTransform(TEXT("WPN_RearSight"),RTS_Component).GetLocation();
                            const FVector Axis=(Rig->GetSocketTransform(TEXT("WPN_FrontSight"),RTS_Component).GetLocation()-Rear).GetSafeNormal();
                            const FVector Up=Rig->GetSocketTransform(TEXT("WPN_root"),RTS_Component).GetRotation().RotateVector(M249WeaponAssets::SightUp);
                            const FQuat Align=FRotationMatrix::MakeFromXZ(Axis,Up).ToQuat().Inverse();
                            Rig->SetWorldTransform(FTransform(Align,FVector(20.,0,0)-Align.RotateVector(Rear)));Capture->SetWorldTransform(FTransform::Identity);
                        }
                        else
                        {
                        const FVector Rear=Rig->GetSocketLocation(TEXT("WPN_RearSight"));
                        const FVector Axis=(Rig->GetSocketLocation(TEXT("WPN_FrontSight"))-Rear).GetSafeNormal();
                        const FVector Up=Rig->GetSocketTransform(TEXT("WPN_root")).GetRotation().RotateVector(M249WeaponAssets::SightUp);
                        Capture->SetWorldLocationAndRotation(Rear-Axis*20.,FRotationMatrix::MakeFromXZ(Axis,Up).ToQuat());
                        }
                    }
                    else if(bM249Focus&&ReviewView!=TEXT("player"))
                    {
                        const FVector Center=Rig->GetComponentTransform().TransformPosition(bBipod?FVector(-2,-16,-17):FVector(4,-10,4));
                        const FVector Eye=Center+Base.RotateVector(ReviewView==TEXT("top")?FVector(-40,-10,65):bBipod?FVector(-82,-12,20):FVector(-65,-5,28));
                        Capture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());
                    }
                    else if(bM249Side)
                    {
                        const FVector Center=Rig->GetSocketLocation(TEXT("WPN_root"))+FVector(0,0,-12);
                        const FVector Eye=Center+Base.RotateVector(FVector(65,-45,38));
                        Capture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());
                    }
                }
                Correctives->TickComponent(.3f,LEVELTICK_All,nullptr);
                World->SendAllEndOfFrameUpdates();Capture->CaptureScene();FlushRenderingCommands();
            }
            TArray<FColor> Pixels;
            if (!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels)) return 7;
            for(auto& Pixel:Pixels)Pixel.A=255;
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(1280,720,Pixels,PNG);
            const FString Name=FString::Printf(TEXT("%s_%s_%03d"),bM249?TEXT("M249"):bM24?TEXT("M24"):TEXT("SVD"),Sample.ADS?TEXT("ads"):Sample.Role,FMath::RoundToInt(Sample.Time*(bM249Focus?1000:30)));
            if (!FFileHelper::SaveArrayToFile(PNG,*(Output/(Name+TEXT(".png")))))return 8;
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("view"),Name);Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());
            Row->SetStringField(TEXT("clip"),Clip->GetPathName());Row->SetBoolField(TEXT("framing_ready"),bM249||Framing.IsReady());
            Row->SetStringField(TEXT("hip_cm"),Hip.ToString());
            Row->SetNumberField(TEXT("corrective_count"),Mesh->GetMorphTargets().Num());
            Row->SetBoolField(TEXT("local_corrective_driver"),Owner->IsLocallyControlled());
            Row->SetStringField(TEXT("camera"),Sample.ADS?TEXT("aligned sight axis; 20 cm rear eye"):
                bM249Side?TEXT("right-side arm and charging-handle inspection"):
                bM249?TEXT("native M249 hip/action anchor"):TEXT("calibrated hip; aim entry reviews the aim clip in this same camera"));
            Row->SetNumberField(TEXT("elbow_left_weight"),Rig->GetMorphTarget(TEXT("JC_ElbowFlex75_L")));
            float MaxDelta=0;
            for(const UMorphTarget* Morph:Mesh->GetMorphTargets())for(const auto& LOD:Morph->GetMorphLODModels())for(const auto& Vertex:LOD.Vertices)MaxDelta=FMath::Max(MaxDelta,Vertex.PositionDelta.Size());
            Row->SetNumberField(TEXT("max_morph_delta_cm"),MaxDelta);
            if(bM249Focus)
            {
                TArray<FFinalSkinVertex> Skinned;Rig->GetCPUSkinnedVertices(Skinned,0);TArray<FVector3f> Points;Points.Reserve(Skinned.Num());for(const auto& V:Skinned)Points.Add(V.Position);
                Binary(Points,Name+TEXT(".vertices"));Row->SetNumberField(TEXT("source_seconds"),Sample.Time);
                if(bBipod)
                {
                    Row->SetBoolField(TEXT("retract"),bRetract);Row->SetNumberField(TEXT("action_seconds"),BipodTime);
                    Row->SetNumberField(TEXT("action_alpha"),BipodAnim->ActionAlpha);Row->SetNumberField(TEXT("aim_alpha"),BipodAnim->AimAlpha);
                    TArray<TSharedPtr<FJsonValue>> Bones;
                    for(int32 B=0;B<Mesh->GetRefSkeleton().GetNum();++B)
                    {
                        const FName Bone=Mesh->GetRefSkeleton().GetBoneName(B);const FTransform X=Rig->GetSocketTransform(Bone,RTS_Component);
                        auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("bone"),Bone.ToString());
                        const FVector P=X.GetLocation(),S=X.GetScale3D();const FQuat Q=X.GetRotation();TArray<TSharedPtr<FJsonValue>> T;
                        for(double Value:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})T.Add(MakeShared<FJsonValueNumber>(Value));
                        V->SetArrayField(TEXT("transform"),T);Bones.Add(MakeShared<FJsonValueObject>(V));
                    }
                    Row->SetArrayField(TEXT("bones"),Bones);
                    for(int32 I=0;I<Parts.Num();++I)
                    {
                        auto* Part=Parts[I];const auto& LOD=Part->GetStaticMesh()->GetRenderData()->LODResources[0];
                        const FTransform X=Part->GetComponentTransform().GetRelativeTransform(Rig->GetComponentTransform());
                        TArray<FVector3f> V;TArray<uint32> F;
                        for(uint32 J=0;J<LOD.VertexBuffers.PositionVertexBuffer.GetNumVertices();++J)V.Add(FVector3f(X.TransformPosition(FVector(LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(J)))));
                        for(int32 J=0;J<LOD.IndexBuffer.GetNumIndices();++J)F.Add(LOD.IndexBuffer.GetIndex(J));
                        const FString Prefix=Name+TEXT("_")+Part->GetStaticMesh()->GetName();Binary(V,Prefix+TEXT(".vertices"));Binary(F,Prefix+TEXT(".indices"));
                    }
                }
                Row->SetStringField(TEXT("view_mode"),ReviewView);Row->SetStringField(TEXT("component_transform"),Rig->GetComponentTransform().ToString());
                const auto& LOD=Mesh->GetResourceForRendering()->LODRenderData[0];FVector Dot=FVector::ZeroVector;int32 Count=0;
                for(const auto& Section:LOD.RenderSections)if(Mesh->GetMaterials()[Section.MaterialIndex].MaterialSlotName==TEXT("M249_MagnifierReticle"))
                    for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V){Dot+=FVector(Points[V]);++Count;}
                if(Count&&Sample.ADS)
                {
                    const FVector P=Capture->GetComponentTransform().InverseTransformPosition(Rig->GetComponentTransform().TransformPosition(Dot/Count));
                    const double Scale=640./FMath::Tan(FMath::DegreesToRadians(Capture->FOVAngle*.5));
                    Row->SetNumberField(TEXT("reticle_pixel_x"),640.+Scale*P.Y/P.X);Row->SetNumberField(TEXT("reticle_pixel_y"),360.-Scale*P.Z/P.X);
                }
            }
            Results.Add(MakeShared<FJsonValueObject>(Row));
        }
        for(auto* Part:Parts)Part->DestroyComponent();
    }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("views"),Results);Report->SetBoolField(TEXT("complete"),true);
    Report->SetNumberField(TEXT("softbox_scale"),SoftboxScale);Report->SetNumberField(TEXT("exposure"),Exposure);
    Report->SetBoolField(TEXT("gameplay_test"),false);FString JSON;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&JSON));
    FFileHelper::SaveStringToFile(JSON,*(Output/TEXT("review.json")));
    UE_LOG(LogTemp,Display,TEXT("M24_HOLD_REVIEW_COMPLETE views=%d"),Results.Num());
    return 0;
#else
    return 1;
#endif
}
