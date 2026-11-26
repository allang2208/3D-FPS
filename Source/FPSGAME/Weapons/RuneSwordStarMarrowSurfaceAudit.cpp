#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "RuneSwordMeshComponent.h"
#include "HighlandBreakSweep.h"
#include "HighlandRidgeThrust.h"
#include "HAL/IConsoleManager.h"
#include "Engine/StreamableManager.h"
#include "../FPSGAMECharacter.h"
#include "../BallisticAuditTarget.h"
#include "Components/BoxComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSArmJointCorrectiveComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "StaticMeshResources.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ImageUtils.h"
#include "RenderingThread.h"
#include "Serialization/JsonSerializer.h"

namespace
{
// Same native pose and camera for both images; only the optical ribbon is toggled.
int32 CaptureSweepRefraction(UCameraComponent* Camera,USceneComponent* Arms,UStaticMeshComponent* Rift,const FString& Out)
{
    UWorld* World=Camera->GetWorld();
    auto* Stage=World->SpawnActor<AActor>();
    auto* Capture=NewObject<USceneCaptureComponent2D>(Stage);
    Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
    Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->CaptureSource=SCS_FinalColorLDR;Capture->ShowFlags.SetMotionBlur(false);
    Capture->ShowFlags.SetAntiAliasing(false);Capture->ShowFlags.SetEyeAdaptation(false);Capture->ShowFlags.SetFog(false);
    Capture->FOVAngle=FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(37.5f))*16.f/9.f));
    const FTransform Eye=Camera->GetComponentTransform();Capture->SetWorldTransform(Eye);
    auto* RT=NewObject<UTextureRenderTarget2D>(Stage);RT->RenderTargetFormat=RTF_RGBA8;
    constexpr int32 W=640,H=360;RT->InitAutoFormat(W,H);RT->UpdateResourceImmediate(true);
    Capture->TextureTarget=RT;Capture->RegisterComponent();
    auto* Light=NewObject<UDirectionalLightComponent>(Stage);Light->SetIntensity(4.f);
    Light->SetWorldRotation(Eye.GetRotation()*FRotator(-22,18,0).Quaternion());Light->RegisterComponent();
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    UMaterialInstanceDynamic* Tiles[]={UMaterialInstanceDynamic::Create(Base,Stage),UMaterialInstanceDynamic::Create(Base,Stage)};
    Tiles[0]->SetVectorParameterValue(TEXT("Color"),FLinearColor(.055f,.12f,.16f));
    Tiles[1]->SetVectorParameterValue(TEXT("Color"),FLinearColor(.65f,.43f,.20f));
    for(int32 Y=-10;Y<=10;++Y)for(int32 Z=-6;Z<=6;++Z)
    {
        auto* Tile=NewObject<UStaticMeshComponent>(Stage);Tile->SetStaticMesh(Cube);Tile->SetMaterial(0,Tiles[(Y+Z+16)%2]);
        Tile->SetCollisionEnabled(ECollisionEnabled::NoCollision);Tile->SetCastShadow(false);
        Tile->SetWorldTransform(FTransform(Eye.GetRotation(),Eye.TransformPosition(FVector(400,Y*55,Z*55)),FVector(.03,.55,.55)));
        Tile->RegisterComponent();Capture->ShowOnlyComponent(Tile);
    }
    TArray<USceneComponent*> Parts;Arms->GetChildrenComponents(true,Parts);Parts.Add(Arms);
    TArray<UPrimitiveComponent*> RestoreOwnerOnly;
    for(auto* Part:Parts)if(auto* Primitive=Cast<UPrimitiveComponent>(Part))
    {
        Capture->ShowOnlyComponent(Primitive);
        if(Primitive->bOnlyOwnerSee){RestoreOwnerOnly.Add(Primitive);Primitive->SetOnlyOwnerSee(false);}
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto Shot=[&](bool On,TArray<FColor>& Pixels)
    {
        Rift->SetVisibility(On);World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
        for(int32 I=0;I<3;++I){Capture->CaptureScene();FlushRenderingCommands();}
        if(!RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels))return false;
        TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(W,H,Pixels,PNG);
        return FFileHelper::SaveArrayToFile(PNG,*(Out/(On?TEXT("rift-on.png"):TEXT("rift-off.png"))));
    };
    TArray<FColor> Off,On;const bool Captured=Shot(false,Off)&&Shot(true,On);
    for(auto* Primitive:RestoreOwnerOnly)Primitive->SetOnlyOwnerSee(true);
    Rift->SetVisibility(true);Stage->Destroy();
    if(!Captured||Off.Num()!=W*H||On.Num()!=Off.Num())return -1;
    int32 Changed=0;
    for(int32 I=0;I<On.Num();++I)if(FMath::Max3(FMath::Abs(int32(On[I].R)-Off[I].R),
        FMath::Abs(int32(On[I].G)-Off[I].G),FMath::Abs(int32(On[I].B)-Off[I].B))>=4)++Changed;
    return Changed;
}
template<class T> void Binary(const TArray<T>& Values,const FString& Path)
{FFileHelper::SaveArrayToFile(TArrayView<const uint8>(reinterpret_cast<const uint8*>(Values.GetData()),Values.Num()*sizeof(T)),*Path);}
TArray<TSharedPtr<FJsonValue>> Vec(const FVector& V)
{return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};}
TSharedPtr<FJsonObject> Transform(const FTransform& T)
{
    auto J=MakeShared<FJsonObject>();J->SetArrayField(TEXT("p"),Vec(T.GetLocation()));J->SetArrayField(TEXT("s"),Vec(T.GetScale3D()));
    const FQuat Q=T.GetRotation();J->SetArrayField(TEXT("q"),{MakeShared<FJsonValueNumber>(Q.X),MakeShared<FJsonValueNumber>(Q.Y),MakeShared<FJsonValueNumber>(Q.Z),MakeShared<FJsonValueNumber>(Q.W)});return J;
}
}

int32 URuneSwordAuditCommandlet::AuditStarMarrowSurface(const FString& Params)
{
    FString Out;if(!FParse::Value(*Params,TEXT("Out="),Out))return 2;
    int32 SampleRate=240;FParse::Value(*Params,TEXT("SampleRate="),SampleRate);SampleRate=FMath::Clamp(SampleRate,30,240);
    FString RequestedVariant;FParse::Value(*Params,TEXT("Variant="),RequestedVariant);
    FString CasesPath;FParse::Value(*Params,TEXT("SwordGripCases="),CasesPath);
    TArray<TSharedPtr<FJsonValue>> Cases;
    if(!CasesPath.IsEmpty())
    {
        FString Input;if(!FFileHelper::LoadFileToString(Input,*CasesPath)||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input),Cases))return 8;
    }
    else for(const FString Variant:{FString(TEXT("Standard")),FString(TEXT("LongGrip"))})
    {
        auto Case=MakeShared<FJsonObject>();Case->SetStringField(TEXT("id"),Variant);
        Case->SetStringField(TEXT("definition"),TEXT("ue_frost_crystal_sword"));
        Case->SetStringField(TEXT("role"),TEXT("StarMarrowCharge"));
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("star_marrow"));
        if(Variant==TEXT("LongGrip"))Parts->SetStringField(TEXT("grip"),TEXT("long_twohand"));
        Case->SetObjectField(TEXT("parts"),Parts);Cases.Add(MakeShared<FJsonValueObject>(Case));
    }
    IFileManager::Get().MakeDirectory(*Out,true);
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Surface_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("StarMarrowSurfaceAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("StarMarrowSurfaceAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 3;
    World->InitializeActorsForPlay(FURL());
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->bShowMouseCursor=false;PC->Possess(Pawn);
    Pawn->SetActorTickEnabled(false);for(auto* C:Pawn->GetComponents())C->SetComponentTickEnabled(false);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();
    auto* Corrective=Pawn->FindComponentByClass<UFPSArmJointCorrectiveComponent>();if(!Corrective)return 4;
    bool AllSweepCasesPassed=true;
    for(const auto& CaseValue:Cases)
    {
        const auto Case=CaseValue->AsObject();if(!Case)return 9;
        const FString Variant=Case->GetStringField(TEXT("id")),Definition=Case->GetStringField(TEXT("definition")),Role=Case->GetStringField(TEXT("role"));
        if(!RequestedVariant.IsEmpty()&&RequestedVariant!=Variant)continue;
        const FString Folder=Out/Variant;IFileManager::Get().MakeDirectory(*Folder,true);
        auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.Mana=100;State.Stamina=100;State.DungeonRun={};
        for(auto& Skill:State.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
        auto Item=Model->CreateItem(Definition);Item.InstanceId=TEXT("surface-")+Variant;Item.Place=1;Item.Cell=6;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);if(!Data)Data=MakeShared<FJsonObject>();
        const auto Parts=Case->GetObjectField(TEXT("parts"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));State.Items={Item};Model->AdoptNetMirror(State);
        const bool RidgeTake=FName(*Role)==HighlandRidgeThrust::Charge;
        const bool RidgeMotion=RidgeTake||HighlandRidgeThrust::IsRelease(FName(*Role));
        // This commandlet has no game tick to dispatch delayed streamable callbacks.
        IConsoleVariable* DelegateDelay=RidgeMotion?IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames")):nullptr;
        const int32 SavedDelay=DelegateDelay?DelegateDelay->GetInt():0;
        if(DelegateDelay)DelegateDelay->Set(0,ECVF_SetByCode);
        Sword->RefreshEquipment(Model);Sword->CancelAction();
        if(RidgeMotion)FlushAsyncLoading();
        if(DelegateDelay)DelegateDelay->Set(SavedDelay,ECVF_SetByCode);
        auto* Mesh=Cast<URuneSwordMeshComponent>(Sword->Viewmodel);if(!Mesh||!Sword->ModularSword)return 5;
        auto* Asset=Mesh->GetSkeletalMeshAsset();
        UAnimSequence* Clip=Sword->Animations.FindRef(FName(*Role));
        if(FName(*Role)==HighlandBreakSweep::Clip && Sword->BroadbladeLoad)
        {
            Sword->BroadbladeLoad->WaitUntilComplete();
            Sword->GrantBroadbladeSweep(Item.InstanceId);
            if(!Sword->BeginBroadbladeSweep() || Sword->CurrentClip!=HighlandBreakSweep::Clip)return 10;
            Clip=Sword->CurrentAnimation;
            Sword->CancelAction();
        }
        if(Role==TEXT("StarMarrowCharge"))
        {
            FString Grip;Parts->TryGetStringField(TEXT("grip"),Grip);
            Clip=LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeMotion20261103/")+
                FString(Grip==TEXT("long_twohand")?TEXT("LongGrip"):TEXT("Standard"))+TEXT("/A_StarMarrow_Charge")));
        }
        if(!Clip)return 6;Sword->Animations.Add(FName(*Role),Clip);
        FAssetCompilingManager::Get().FinishAllCompilation();
        bool CheckSweepRift=false;
        Case->TryGetBoolField(TEXT("check_sweep_rift"),CheckSweepRift);
        if(CheckSweepRift)
        {
            const bool FromHeavy=Case->GetStringField(TEXT("entry"))==TEXT("heavy");
            const bool LongGrip=Parts->GetStringField(TEXT("grip"))==TEXT("long_twohand");
            const float Dt=FromHeavy?1.f/30.f:1.f/120.f;
            Sword->CancelAction();Sword->SetClip(TEXT("Idle"),true);
            if(!Sword->StartSwing(TEXT("HeavyRelease"),true))return 12;
            if(!FromHeavy)for(int32 I=0;I<360&&Sword->bAttacking;++I)Sword->TickComponent(Dt,LEVELTICK_All,nullptr);
            Sword->BeginPrimaryAttack();
            for(int32 I=0;I<60&&Sword->bHeavyAttack;++I)Sword->TickComponent(Dt,LEVELTICK_All,nullptr);
            if(!Sword->bAttacking||Sword->CurrentClip!=HighlandBreakSweep::Clip)return 13;
            const FVector Forward=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
            auto Receiver=[&](float Distance)
            {
                auto* Target=World->SpawnActor<ABallisticAuditTarget>();
                auto* Shape=Target->FindComponentByClass<UBoxComponent>();
                Shape->SetBoxExtent(FVector(4,4,20));Shape->SetCollisionObjectType(ECC_Pawn);
                Target->SetActorLocation(Pawn->GetActorLocation()+Forward*Distance);return Target;
            };
            auto* Front=Receiver(105);auto* Outer=Receiver(Sword->SwingReach-16);
            auto* Back=Receiver(-105);auto* Far=Receiver(Sword->SwingReach+75);
            auto* LeftTarget=Receiver(0);auto* RightTarget=Receiver(0);
            LeftTarget->SetActorLocation(Pawn->GetActorLocation()+Forward.RotateAngleAxis(-78.f,FVector::UpVector)*180.f);
            RightTarget->SetActorLocation(Pawn->GetActorLocation()+Forward.RotateAngleAxis(78.f,FVector::UpVector)*180.f);
            auto* Ribbon=Cast<UStaticMesh>(HighlandBreakSweep::RiftPath(LongGrip).ResolveObject());
            if(!Ribbon||!Ribbon->GetRenderData()||!Sword->RiftMaterial)return 14;
            const auto& Buffers=Ribbon->GetRenderData()->LODResources[0].VertexBuffers;
            int32 VisibleFrames=0,HoldFrames=0,FrontHits=0,OuterHits=0,ChangedPixels=-1;
            const bool PixelCapture=FParse::Param(*Params,TEXT("SweepRiftPixels")) && Variant==TEXT("StandardIdleEntry");
            float MaxTipError=0,Total=0,Held=0;bool SawDissolve=false,EndedBeforeIdle=false,Passed=true;
            for(int32 I=0;I<320&&Sword->bAttacking;++I)
            {
                const float PrevDamage=Front->Received,PrevOuter=Outer->Received;
                const float PrevProgress=Sword->RiftMaterial->K2_GetScalarParameterValue(TEXT("SweepProgress"));
                const float Pause=Sword->SweepHitPause;Held+=FMath::Min(Pause,Dt);
                Sword->TickComponent(Dt,LEVELTICK_All,nullptr);Total+=Dt;
                FrontHits+=Front->Received>PrevDamage;OuterHits+=Outer->Received>PrevOuter;
                if(!Sword->bRiftActive)
                {
                    if(SawDissolve&&Sword->bAttacking)EndedBeforeIdle=true;
                    Passed&=!Sword->RiftVisual->IsVisible();continue;
                }
                Passed&=Sword->RiftVisual->IsVisible()&&Sword->RiftVisual->GetStaticMesh()==Ribbon;
                if(!Sword->RiftVisual->GetAttachParent())
                {
                    SawDissolve|=Sword->RiftMaterial->K2_GetScalarParameterValue(TEXT("RiftFade"))<1.f;
                    continue;
                }
                ++VisibleFrames;
                const float P=Sword->RiftMaterial->K2_GetScalarParameterValue(TEXT("SweepProgress"));
                if(PixelCapture && ChangedPixels<0 && P>.48f)
                    ChangedPixels=CaptureSweepRefraction(Sword->Camera,Mesh,Sword->RiftVisual,Folder);
                Passed&=FMath::IsNearlyEqual(P,(Sword->Elapsed-Sword->ContactStart)/(Sword->ContactEnd-Sword->ContactStart),.001f);
                if(Pause>=Dt){++HoldFrames;Passed&=FMath::IsNearlyEqual(P,PrevProgress,.0001f);}
                FVector Left=FVector::ZeroVector,Right=Left;float Lo=-1,Hi=2;
                for(uint32 V=0;V<Buffers.PositionVertexBuffer.GetNumVertices();++V)
                {
                    const FVector2f UV=Buffers.StaticMeshVertexBuffer.GetVertexUV(V,0);
                    if(UV.Y<.999f)continue;
                    const FVector Pos(Buffers.PositionVertexBuffer.VertexPosition(V));
                    if(UV.X<=P&&UV.X>Lo){Lo=UV.X;Left=Pos;}
                    if(UV.X>=P&&UV.X<Hi){Hi=UV.X;Right=Pos;}
                }
                if(Lo<0||Hi>1){Passed=false;continue;}
                const FVector Point=FMath::Lerp(Left,Right,Hi>Lo?(P-Lo)/(Hi-Lo):0.f);
                const FVector Edge=Sword->RiftVisual->GetComponentTransform().TransformPosition(Point);
                const FVector Tip=Sword->ModularSword->GetComponentTransform().TransformPosition(Sword->ModularBladeTip);
                MaxTipError=FMath::Max(MaxTipError,float(FVector::Distance(Edge,Tip)));
            }
            const bool RangeOK=FrontHits==1&&OuterHits==1&&LeftTarget->Received>0&&RightTarget->Received>0&&Back->Received==0&&Far->Received==0;
            for(auto* T:{Front,Outer,Back,Far,LeftTarget,RightTarget})T->Destroy();
            Passed&=RangeOK&&VisibleFrames>0&&HoldFrames>0&&SawDissolve&&EndedBeforeIdle&&MaxTipError<1.f&&
                FMath::IsNearlyEqual(Held,HighlandBreakSweep::HitPauseSeconds,.002f);
            Sword->GrantBroadbladeSweep(Item.InstanceId);Sword->BeginPrimaryAttack();
            for(int32 I=0;I<60&&!Sword->bRiftActive;++I)Sword->TickComponent(Dt,LEVELTICK_All,nullptr);
            const bool Whiff=Sword->bRiftActive&&!Sword->bImpactFeedbackPlayed&&Sword->SweepHitPause==0.f;
            Sword->CancelAction();
            const bool Cancelled=!Sword->bRiftActive&&!Sword->RiftVisual->IsVisible()&&!Sword->RiftVisual->GetAttachParent();
            Sword->StartSwing(TEXT("Slash1"),false,0.f);
            for(int32 I=0;I<120&&!Sword->bRiftActive&&Sword->bAttacking;++I)Sword->TickComponent(Dt,LEVELTICK_All,nullptr);
            const bool NextSlash= Sword->bRiftActive && Sword->RiftMeshes.IsValidIndex(0) &&
                Sword->RiftVisual->GetStaticMesh()==Sword->RiftMeshes[0] && !Sword->RiftVisual->GetAttachParent();
            Sword->CancelAction();
            Passed&=!PixelCapture||ChangedPixels>0;
            Passed&=Whiff&&Cancelled&&NextSlash;
            auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("passed"),Passed);
            Result->SetBoolField(TEXT("next_normal_slash"),NextSlash);
            Result->SetNumberField(TEXT("hold_frames"),HoldFrames);
            Result->SetNumberField(TEXT("front_hits"),FrontHits);Result->SetNumberField(TEXT("outer_hits"),OuterHits);
            Result->SetNumberField(TEXT("changed_pixels_640x360"),ChangedPixels);
            Result->SetStringField(TEXT("mesh"),Ribbon->GetPathName());Result->SetNumberField(TEXT("visible_stroke_frames"),VisibleFrames);
            Result->SetNumberField(TEXT("max_tip_error_cm"),MaxTipError);Result->SetNumberField(TEXT("held_seconds"),Held);
            Result->SetNumberField(TEXT("swing_seconds"),Total);Result->SetBoolField(TEXT("range_and_single_hits"),RangeOK);
            Result->SetBoolField(TEXT("fade_finished_during_recovery"),EndedBeforeIdle);Result->SetBoolField(TEXT("whiff"),Whiff);
            Result->SetBoolField(TEXT("cancelled_cleanly"),Cancelled);FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
            FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("rift.json")));
            AllSweepCasesPassed&=Passed;
            continue;
        }
        const auto& LOD=Asset->GetResourceForRendering()->LODRenderData[0];const auto* Weights=Mesh->GetSkinWeightBuffer(0);
        if(!Weights||!Weights->GetNeedsCPUAccess())return 7;
        const int32 Count=LOD.GetNumVertices();const auto& Ref=Asset->GetRefSkeleton();
        TArray<uint32> Indices;LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);Binary(Indices,Folder/TEXT("arms.indices"));
        TArray<FVector3f> Bind;TArray<uint16> BoneIndices;TArray<float> BoneWeights;TArray<uint16> MainBone;
        Bind.SetNum(Count);MainBone.SetNum(Count);const int32 Influences=Weights->GetMaxBoneInfluences();
        BoneIndices.SetNumZeroed(Count*Influences);BoneWeights.SetNumZeroed(Count*Influences);
        for(const auto& Section:LOD.RenderSections)for(uint32 I=Section.BaseVertexIndex;I<Section.BaseVertexIndex+Section.NumVertices;++I)
        {
            Bind[I]=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(I);float Best=-1;
            for(int32 K=0;K<Influences;++K)
            {
                const int32 B=Section.BoneMap[Weights->GetBoneIndex(I,K)];const float W=float(Weights->GetBoneWeight(I,K))/65535.f;
                BoneIndices[I*Influences+K]=B;BoneWeights[I*Influences+K]=W;if(W>Best){Best=W;MainBone[I]=B;}
            }
        }
        Binary(Bind,Folder/TEXT("arms.bind"));Binary(MainBone,Folder/TEXT("arms.mainbone"));Binary(BoneIndices,Folder/TEXT("arms.bones"));Binary(BoneWeights,Folder/TEXT("arms.weights"));
        auto Metadata=MakeShared<FJsonObject>();Metadata->SetStringField(TEXT("mesh"),Asset->GetPathName());Metadata->SetStringField(TEXT("animation"),Clip->GetPathName());
        Metadata->SetNumberField(TEXT("vertex_count"),Count);Metadata->SetNumberField(TEXT("influences"),Influences);Metadata->SetNumberField(TEXT("fps"),SampleRate);
        TArray<TSharedPtr<FJsonValue>> Names,Rest;TArray<FTransform> RefPose=Ref.GetRefBonePose();
        for(int32 I=0;I<Ref.GetNum();++I){if(Ref.GetParentIndex(I)>=0)RefPose[I]=RefPose[I]*RefPose[Ref.GetParentIndex(I)];Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(I).ToString()));Rest.Add(MakeShared<FJsonValueObject>(Transform(RefPose[I])));}
        Metadata->SetArrayField(TEXT("bone_names"),Names);Metadata->SetArrayField(TEXT("rest"),Rest);
        Metadata->SetNumberField(TEXT("morph_count"),Asset->GetMorphTargets().Num());
        Metadata->SetObjectField(TEXT("case"),Case);
        Sword->SetClip(TEXT("Idle"),true);Mesh->ClearWhirlwindEntry();Sword->SamplePose(0);
        TArray<TSharedPtr<FJsonValue>> PartRows;TArray<UStaticMeshComponent*> Static;Pawn->GetComponents(Static);int32 PartIndex=0;
        FTransform Root=Mesh->GetSocketTransform(TEXT("WPN_root"));Root.SetScale3D(FVector::OneVector);
        for(auto* Part:Static)if(Part->GetStaticMesh()&&(Part==Sword->ModularSword||Part->IsAttachedTo(Sword->ModularSword)))
        {
            const auto& L=Part->GetStaticMesh()->GetRenderData()->LODResources[0];TArray<FVector3f> V;TArray<uint32> I;
            for(uint32 J=0;J<L.VertexBuffers.PositionVertexBuffer.GetNumVertices();++J)
            {
                const FVector Local(L.VertexBuffers.PositionVertexBuffer.VertexPosition(J));
                V.Add(FVector3f(Root.InverseTransformPosition(Part->GetComponentTransform().TransformPosition(Local))));
            }
            for(int32 J=0;J<L.IndexBuffer.GetNumIndices();++J)I.Add(L.IndexBuffer.GetIndex(J));
            const FString Label=FString::Printf(TEXT("part%d"),PartIndex++);Binary(V,Folder/(Label+TEXT(".vertices")));Binary(I,Folder/(Label+TEXT(".indices")));
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),Label);Row->SetStringField(TEXT("mesh"),Part->GetStaticMesh()->GetPathName());PartRows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Metadata->SetArrayField(TEXT("parts"),PartRows);TArray<TSharedPtr<FJsonValue>> Frames;
        if(RidgeTake)
        {
            Sword->BeginPrimaryAttack();
            if(!Sword->bCharging||Sword->CurrentClip!=HighlandRidgeThrust::Charge||
                !Sword->Animations.FindRef(HighlandRidgeThrust::Release))return 16;
            Metadata->SetNumberField(TEXT("charge_required"),Sword->RequiredChargeSeconds);
            Metadata->SetNumberField(TEXT("charge_clip_seconds"),Clip->GetPlayLength());
        }
        else if(Role==TEXT("StarMarrowCharge"))Sword->BeginStarMarrowChargeMotion();
        else if(FName(*Role)==HighlandBreakSweep::Clip)
        {
            FString Entry;Case->TryGetStringField(TEXT("entry"),Entry);
            if(Entry==TEXT("heavy") || Entry==TEXT("late"))
            {
                Sword->StartSwing(TEXT("HeavyRelease"),true);
                Sword->Elapsed=Entry==TEXT("heavy")?RuneSwordHeavyRhythm::FollowEnd:.76f;
                Sword->SamplePose(Sword->Elapsed);
            }
            Sword->GrantBroadbladeSweep(Item.InstanceId);
            if(Entry==TEXT("tap"))
            {
                Sword->BeginPrimaryAttack();
                Sword->Elapsed=.10f;
                Sword->SamplePose(Sword->Elapsed);
                Sword->ReleasePrimaryAttack();
            }
            else Sword->BeginAttack();
            if(Entry==TEXT("late"))
                for(int32 Step=0;Step<120 && Sword->bHeavyAttack;++Step)
                    Sword->TickComponent(1.f/120.f,LEVELTICK_All,nullptr);
            if(Sword->CurrentClip!=HighlandBreakSweep::Clip || !Sword->bAttacking)return 11;
            Clip=Sword->CurrentAnimation;
            Metadata->SetStringField(TEXT("animation"),Clip->GetPathName());
        }
        else
        {
            FString Entry;
            const bool UseEntry=RidgeMotion&&Case->TryGetStringField(TEXT("entry_role"),Entry);
            if(UseEntry)
            {
                Sword->SetClip(FName(*Entry),false);
                if(!Sword->CurrentAnimation)return 6;
                double Phase=.5;Case->TryGetNumberField(TEXT("entry_phase"),Phase);
                Mesh->ClearWhirlwindEntry();
                Sword->SamplePose(Sword->CurrentAnimation->GetPlayLength()*FMath::Clamp(Phase,0.,1.));
            }
            Sword->SetClip(FName(*Role),false);
            if(!UseEntry)Mesh->ClearWhirlwindEntry();
        }
        int32 SampleCount=0;Case->TryGetNumberField(TEXT("samples"),SampleCount);
        const int32 ButtonUp=RidgeTake?FMath::CeilToInt(Sword->RequiredChargeSeconds*SampleRate):0;
        if(RidgeTake)Metadata->SetNumberField(TEXT("button_up_frame"),ButtonUp);
        const int32 LastFrame=RidgeTake?ButtonUp+FMath::RoundToInt(Sword->Animations.FindRef(HighlandRidgeThrust::Release)->GetPlayLength()*SampleRate):
            (SampleCount>1?SampleCount-1:FMath::RoundToInt(Clip->GetPlayLength()*SampleRate));
        const float SampleDelta=SampleCount>1?Clip->GetPlayLength()/LastFrame:1.f/SampleRate;
        for(int32 Frame=0;Frame<=LastFrame;++Frame)
        {
            const float T=RidgeTake?Frame*SampleDelta:FMath::Min(Frame*SampleDelta,Clip->GetPlayLength());
            if(RidgeTake)
            {
                if(Frame<=ButtonUp)Sword->ChargeStartedAt=World->GetTimeSeconds()-T;
                if(Frame)Sword->TickComponent(SampleDelta,LEVELTICK_All,nullptr);
                if(Frame==ButtonUp)
                {
                    Sword->ReleasePrimaryAttack();
                    if(Sword->CurrentClip!=HighlandRidgeThrust::Release||!Sword->bHeavyAttack)return 17;
                    Metadata->SetNumberField(TEXT("contact_start"),Sword->ContactStart);
                    Metadata->SetNumberField(TEXT("contact_end"),Sword->ContactEnd);
                }
            }
            else {Sword->Elapsed=T;if(Frame)Mesh->AdvanceLocomotionEntry(SampleDelta);Sword->SamplePose(T);}
            Corrective->TickComponent(SampleDelta,LEVELTICK_All,nullptr);
            // Evaluate the actual morph weights in bind space, then skin with the final runtime bone matrices.
            TArray<FVector3f> Morphed=Bind;int32 Active=0;
            for(const UMorphTarget* Morph:Asset->GetMorphTargets())
            {
                const float W=Mesh->GetMorphTarget(Morph->GetFName());if(FMath::Abs(W)<1e-6f)continue;++Active;
                for(auto Delta=Morph->GetDeltaIteratorForLOD(0);!Delta.AtEnd();++Delta)
                    if(Morphed.IsValidIndex(Delta->SourceIdx))Morphed[Delta->SourceIdx]+=Delta->PositionDelta*W;
            }
            TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);TArray<FVector3f> V;V.SetNumZeroed(Count);
            for(int32 I=0;I<Count;++I)for(int32 K=0;K<Influences;++K)
                if(BoneWeights[I*Influences+K]>0)V[I]+=FVector3f(Matrices[BoneIndices[I*Influences+K]].TransformPosition(Morphed[I]))*BoneWeights[I*Influences+K];
            Binary(V,Folder/FString::Printf(TEXT("f%04d.vertices"),Frame));
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("frame"),Frame);Row->SetNumberField(TEXT("seconds"),T);Row->SetNumberField(TEXT("active_correctives"),Active);
            FTransform W=Mesh->GetSocketTransform(TEXT("WPN_root"),RTS_Component);W.SetScale3D(FVector::OneVector);Row->SetObjectField(TEXT("weapon"),Transform(W));
            auto Bones=MakeShared<FJsonObject>();
            for(int32 B=0;B<Ref.GetNum();++B)
            {
                const FName Name=Ref.GetBoneName(B);
                Bones->SetObjectField(Name.ToString(),Transform(Mesh->GetSocketTransform(Name,RTS_Component)));
            }
            FVector CameraLocation=FVector::ZeroVector;FRotator CameraRotation=FRotator::ZeroRotator;
            Sword->GetCameraMotion(CameraLocation,CameraRotation);
            Row->SetArrayField(TEXT("camera_location_cm"),Vec(CameraLocation));
            Row->SetArrayField(TEXT("camera_rotation_pyr"),Vec(FVector(CameraRotation.Pitch,CameraRotation.Yaw,CameraRotation.Roll)));
            Row->SetObjectField(TEXT("bones"),Bones);Frames.Add(MakeShared<FJsonValueObject>(Row));
        }
        bool CheckContact=false;Case->TryGetBoolField(TEXT("check_contact"),CheckContact);
        if(CheckContact && FName(*Role)==HighlandBreakSweep::Clip)
        {
            const FVector Aim=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
            auto SpawnReceiver=[&](float Offset)
            {
                auto* Target=World->SpawnActor<ABallisticAuditTarget>();
                auto* Shape=Target->FindComponentByClass<UBoxComponent>();
                Shape->SetBoxExtent(FVector(4,4,20));Shape->SetCollisionObjectType(ECC_Pawn);
                Target->SetActorLocation(Pawn->GetActorLocation()+Aim*Offset);
                return Target;
            };
            auto* Front=SpawnReceiver(105);auto* Back=SpawnReceiver(-105);
            Sword->CancelAction();Sword->SetClip(TEXT("Idle"),true);
            Sword->GrantBroadbladeSweep(Item.InstanceId);Sword->BeginAttack();
            int32 Changes=0;float ClockAtHit=-1.f,Paused=0.f,Total=0.f;
            constexpr float Dt=1.f/240.f;
            for(int32 Step=0;Sword->bAttacking && Step<400;++Step)
            {
                const float PrevDamage=Front->Received;
                Paused+=FMath::Min(Dt,Sword->SweepHitPause);
                Sword->TickComponent(Dt,LEVELTICK_All,nullptr);Total+=Dt;
                if(Front->Received>PrevDamage){++Changes;ClockAtHit=Sword->Elapsed;}
            }
            auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("front_hits"),Changes);
            Result->SetNumberField(TEXT("back_damage"),Back->Received);Result->SetNumberField(TEXT("contact_time"),ClockAtHit);
            Result->SetNumberField(TEXT("held_seconds"),Paused);Result->SetNumberField(TEXT("total_seconds"),Total);
            Metadata->SetObjectField(TEXT("contact_probe"),Result);
            Front->Destroy();Back->Destroy();
        }
        Metadata->SetArrayField(TEXT("frames"),Frames);FString Json;FJsonSerializer::Serialize(Metadata,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("surface.json")));
        UE_LOG(LogTemp,Display,TEXT("STAR_MARROW_SURFACE %s vertices=%d frames=%d morphs=%d parts=%d"),*Variant,Count,LastFrame+1,Asset->GetMorphTargets().Num(),PartIndex);
    }
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return AllSweepCasesPassed?0:15;
}
