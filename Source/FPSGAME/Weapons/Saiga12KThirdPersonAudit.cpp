#include "ShotgunAttachmentAuditCommandlet.h"
#include "Saiga12KWeaponAssets.h"
#include "Saiga12KMagazineAssets.h"
#include "Saiga12KAttachments.h"
#include "TacticalDeviceComponent.h"
#include "TacticalDeviceVariants.h"
#include "GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Characters/FPSPlayerBodyGrip.h"
#include "../Characters/FPSBodyRifleStockContacts.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"

// User-requested isolated checks: native animation graphs and actual fitted
// assets. No player save, damage, ammo use, map play or network socket transport.
int32 UShotgunAttachmentAuditCommandlet::RunSaiga12KPresentationAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=SaigaPresentation_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SaigaPresentationAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool Pass,const FString& Name,double Value=0.)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),Pass);R->SetNumberField(TEXT("value"),Value);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("SAIGA_BODY %s %s %.6f"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Value);
    };
    auto Base=Model->Snapshot();Base.Items.Reset();Base.ActiveWeaponSlot=6;Base.ActiveProductionTool.Reset();Base.DungeonRun={};
    auto Item=Model->CreateItem(Saiga12KWeaponAssets::Definition);Item.Place=1;Item.Cell=6;Item.Magazine=8;Base.Items={Item};Model->Current=Base;
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();
    PC->SetPlayerState(World->SpawnActor<AColdSteelPlayerState>());
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Pawn);
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pawn->DispatchBeginPlay();Model->CurrentPawn=Pawn;
    Pawn->ApplyColdSteelProfile(Model);
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!Body->BodyAnimation||!Pawn->IdleAnimation)return 2;
    auto* NativeBody=Body->GetBodyMesh();auto* Source=Pawn->AKMViewmodel.Get();
    const auto SourcePose=[&]()
    {
        Pawn->UpdateActionPose(0.f);Source->TickAnimation(0.f,false);Source->RefreshBoneTransforms();Source->UpdateChildTransforms();
    };
    const auto Idle=[&]()
    {
        Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;Pawn->bInventoryWeaponReady=true;
        Pawn->WeaponADSFactor=0.f;Pawn->LastShotWorldTime=-100.;SourcePose();
        Body->DisplayState=Body->SampleLocalState();Body->CaptureEquipment();
    };
    const auto Parts=[&](const TCHAR* Grip,const TCHAR* Mag,const TCHAR* Stock=TEXT("false"))
    {
        auto Data=MakeShared<FJsonObject>();auto Values=MakeShared<FJsonObject>();
        Values->SetStringField(TEXT("underbarrel"),Grip);Values->SetStringField(TEXT("magazine"),Mag);Values->SetStringField(TEXT("stock"),Stock);
        Values->SetStringField(TEXT("tactical"),TEXT("laser"));Values->SetStringField(TEXT("tactical_secondary"),TEXT("blessed_laser"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Values);Data->SetNumberField(TEXT("gunsmith_version"),1);
        auto& I=Model->Current.Items[0];I.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&I.Data));
        Pawn->ApplyColdSteelProfile(Model);Idle();
    };
    Parts(TEXT("false"),TEXT("false"));
    Check(Body->MotionBindings.Num()==1&&Body->BodyAnimation->RifleHold.bValid&&Body->BodyAnimation->bHasLeftGrip,TEXT("12K uses calibrated rifle hold and both hands"));
    if(Body->MotionBindings.Num()!=1)return 2;
    // Read the installed factory rubber pad in the same native root units.
    auto* Asset=Source->GetSkeletalMeshAsset();const auto& Ref=Asset->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)>=0)Bind[I]=Bind[I]*Bind[Ref.GetParentIndex(I)];
    const auto RootBind=Bind[Asset->GetRefSkeleton().FindBoneIndex(TEXT("WPN_root"))];FBox Pad(ForceInit);
    const auto* Render=Asset->GetResourceForRendering();
    if(Render&&!Render->LODRenderData.IsEmpty())
    {
        const auto& LOD=Render->LODRenderData[0];
        for(const auto& S:LOD.RenderSections)
            if(Asset->GetMaterials()[S.MaterialIndex].MaterialSlotName==TEXT("Saiga12K_StockPad"))
                for(uint32 V=S.BaseVertexIndex;V<S.BaseVertexIndex+S.NumVertices;++V)
                    Pad+=RootBind.InverseTransformPosition(FVector(LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V)));
    }
    const FVector* Stock=FPSBodyRifleStock::Find(Asset->GetPathName());
    const FVector Actual=Pad.IsValid?FVector(Pad.GetCenter().X,Pad.Min.Y,Pad.GetCenter().Z):FVector::ZeroVector;
    const double PadError=Stock?FVector::Distance(*Stock,Actual)*100.:10000.;
    UE_LOG(LogTemp,Display,TEXT("SAIGA_BODY_PAD actual_root=%s"),*Actual.ToString());
    Check(Pad.IsValid&&Stock&&PadError<.25,TEXT("factory buttpad calibration matches installed geometry cm"),PadError);
    for(const TCHAR* Key:{TEXT("Rifle.Idle"),TEXT("Rifle.Walk.Fwd"),TEXT("Rifle.Walk.Bwd"),TEXT("Rifle.Jog.Fwd"),TEXT("Crouch.Idle"),TEXT("Rifle.Reload"),TEXT("Rifle.Equip")})
    {
        const auto* Clip=Body->BodyAnimation->Clips.FindRef(Key).Get();
        Check(Clip&&Clip->GetSkeleton()==NativeBody->GetSkeletalMeshAsset()->GetSkeleton(),FString(TEXT("body animation available "))+Key);
    }
    // Evaluate the actual full-body graph at controlled pose states. This does
    // not stand in for rendered motion quality or mouse/CMC input testing.
    const auto Evaluate=[&](float Pitch,float Yaw,bool Aim,bool Crouch,float Speed=0.f,bool Sprint=false)
    {
        auto S=Body->SampleLocalState();S.AimPitch=Pitch;S.AimYaw=Yaw;S.bAiming=Aim;S.bCrouched=Crouch;S.bSprinting=Sprint;
        Body->CaptureMotion(S);Body->DisplayState=S;
        for(int32 Frame=0;Frame<24;++Frame)
        {
            ++GFrameCounter;
            Body->ApplyMotion(1.f/60.f);Body->BodyAnimation->BodyState=S;Body->BodyAnimation->Clock=Frame/60.f;
            Body->BodyAnimation->Speed=Speed;NativeBody->TickAnimation(1.f/60.f,false);NativeBody->RefreshBoneTransforms();NativeBody->UpdateChildTransforms();
        }
        auto* Gun=Body->MotionBindings[0].Mesh.Get();Gun->UpdateChildTransforms();
        const FVector Barrel=Gun->GetSocketTransform(TEXT("WPN_root")).TransformVectorNoScale(FVector(0,1,0)).GetSafeNormal();
        // The shared rifle graph lowers the muzzle by 12 degrees while not
        // aiming. Compare with that actual ready-pose contract, including the
        // current aim blend, rather than requiring ADS alignment during idle.
        const float ExpectedPitch=FMath::Clamp(Pitch-12.f*(1.f-Body->BodyAnimation->AimAlpha),-80.f,80.f);
        const double Direction=FVector::DotProduct(Barrel,FRotator(ExpectedPitch,Yaw,0).Vector());
        const FTransform Right=NativeBody->GetSocketTransform(TEXT("hand_r"));
        const FVector Left=(Body->BodyAnimation->LeftGripFromRight*Right).GetLocation();
        const double Contact=FVector::Distance(Left,NativeBody->GetSocketLocation(TEXT("hand_l")));
        const FVector Chest=NativeBody->GetSocketLocation(TEXT("spine_03"));
        const FVector Forward=FRotator(0,0,0).Vector();
        const auto ToBody=[&](const FVector& P){return NativeBody->GetComponentTransform().InverseTransformPosition(P);};
        UE_LOG(LogTemp,Display,TEXT("SAIGA_HAND_POSITION aim=%.1f/%.1f stock=%s right=%s left=%s chest=%s root=%s mount=%s"),
            Pitch,Yaw,*Body->BodyAnimation->RifleHold.StockInHand.ToString(),
            *ToBody(Right.GetLocation()).ToString(),*ToBody(NativeBody->GetSocketLocation(TEXT("hand_l"))).ToString(),
            *ToBody(Chest).ToString(),*ToBody(Gun->GetSocketLocation(TEXT("WPN_root"))).ToString(),*Gun->GetRelativeTransform().ToString());
        if(S.Action==EFPSBodyAction::None&&FMath::IsNearlyZero(Yaw)&&FMath::IsNearlyZero(Pitch))
        {
            Check(FVector::DotProduct(Right.GetLocation()-Chest,Forward)>10.,TEXT("right wrist remains ahead of chest cm"),FVector::DotProduct(Right.GetLocation()-Chest,Forward));
            Check(FVector::DotProduct(NativeBody->GetSocketLocation(TEXT("hand_l"))-Chest,Forward)>20.,TEXT("left wrist remains ahead of chest cm"),FVector::DotProduct(NativeBody->GetSocketLocation(TEXT("hand_l"))-Chest,Forward));
        }
        return FVector2D(Direction,Contact);
    };
    for(const TCHAR* Grip:{TEXT("false"),TEXT("vertical_foregrip"),TEXT("tactical_vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop"),TEXT("angled_foregrip")})
    {
        Parts(Grip,TEXT("false"));
        for(const FVector& State:{FVector(0,0,0),FVector(30,25,1),FVector(-30,-25,1)})
        {
            const auto R=Evaluate(State.X,State.Y,State.Z>0,false);
            const FString Label=FString::Printf(TEXT("grip %s pitch %.0f yaw %.0f"),Grip,State.X,State.Y);
            Check(R.X>.999,Label+TEXT(" barrel follows shared aim/ready pose"),R.X);
            Check(R.Y<1.,Label+TEXT(" support hand contact cm"),R.Y);
        }
    }
    Parts(TEXT("vertical_foregrip"),TEXT("false"));
    for(int32 Mode=0;Mode<4;++Mode)
    {
        const auto R=Evaluate(15,-20,Mode!=3,Mode==2,Mode==0?160.f:Mode==1?320.f:Mode==3?500.f:90.f,Mode==3);
        Check(R.X>.999,FString::Printf(TEXT("walk/jog/crouch/sprint mode %d muzzle direction"),Mode),R.X);
        Check(R.Y<1.,FString::Printf(TEXT("walk/jog/crouch/sprint mode %d support contact cm"),Mode),R.Y);
    }
    for(const TCHAR* Id:{TEXT("skeleton"),TEXT("core_stock"),TEXT("qr_performance"),TEXT("tactical_telescopic"),TEXT("legendary_adjustable_tactical_stock"),TEXT("saiga12k_bump_stock")})
    {
        Parts(TEXT("vertical_foregrip"),TEXT("false"),Id);
        const auto& D=Body->MotionBindings[0].Definition;int32 Visible=0;bool FactoryHidden=false;
        for(int32 I=0;I<Asset->GetMaterials().Num();++I)
            if(Asset->GetMaterials()[I].MaterialSlotName==TEXT("Saiga12K_StockPad"))FactoryHidden=D.HiddenMaterials.Contains(I);
        for(const auto& Part:D.Parts)if(Part.bVisible&&Part.Mesh.ToSoftObjectPath().ToString().Contains(FString(Id)==Saiga12KSpecialStockAssets::Part?TEXT("SpecialStock"):Id))++Visible;
        Check(FactoryHidden&&Visible==1&&Body->BodyAnimation->RifleHold.bValid,FString(TEXT("world stock replacement "))+Id);
        const auto R=Evaluate(20,15,true,false);Check(R.X>.999,FString(TEXT("stock barrel direction "))+Id,R.X);
    }
    // Match the reported loadout rather than checking the stock and drum only
    // in separate configurations. Repeat the real equipment refresh boundary.
    Parts(TEXT("tactical_vertical_foregrip"),Saiga12KMagazineAssets::DrumPart,Saiga12KSpecialStockAssets::Part);
    UE_LOG(LogTemp,Display,TEXT("SAIGA_BODY_LODS body=%d weapon=%d"),NativeBody->GetSkeletalMeshAsset()->GetLODNum(),Asset->GetLODNum());
    for(int32 LOD=0;LOD<NativeBody->GetSkeletalMeshAsset()->GetLODNum();++LOD)
    {
        NativeBody->SetForcedLOD(LOD+1);NativeBody->SetPredictedLODLevel(LOD);
        UE_LOG(LogTemp,Display,TEXT("SAIGA_BODY_LOD_SAMPLE %d"),LOD);
        Evaluate(0,0,false,false);
    }
    NativeBody->SetForcedLOD(1);NativeBody->SetPredictedLODLevel(0);
    for(int32 Refresh=0;Refresh<3;++Refresh)
    {
        Body->CaptureEquipment();
        const auto R=Evaluate(0,0,false,false);
        Check(R.X>.999&&R.Y<1.,FString::Printf(TEXT("reported stock/drum/tactical grip loadout refresh %d"),Refresh));
    }
    if(auto* Tuning=GI->GetSubsystem<UDevelopmentTuningSubsystem>())
        Tuning->SetEnabled(EDevelopmentTuningOption::ThirdPersonView,true,PC);
    for(int32 Frame=0;Frame<120;++Frame)
    {
        ++GFrameCounter;
        Pawn->UpdateActionPose(1.f/60.f);Source->TickAnimation(1.f/60.f,false);Source->RefreshBoneTransforms();Source->UpdateChildTransforms();
        Body->TickComponent(1.f/60.f,LEVELTICK_All,nullptr);
        NativeBody->TickAnimation(1.f/60.f,false);NativeBody->RefreshBoneTransforms();NativeBody->UpdateChildTransforms();
        if(Frame==0||Frame==30||Frame==119)
        {
            const FTransform FrameToBody=NativeBody->GetComponentTransform();
            UE_LOG(LogTemp,Display,TEXT("SAIGA_NORMAL_TICK frame=%d right=%s left=%s root=%s"),Frame,
                *FrameToBody.InverseTransformPosition(NativeBody->GetSocketLocation(TEXT("hand_r"))).ToString(),
                *FrameToBody.InverseTransformPosition(NativeBody->GetSocketLocation(TEXT("hand_l"))).ToString(),
                *FrameToBody.InverseTransformPosition(Body->MotionBindings[0].Mesh->GetSocketLocation(TEXT("WPN_root"))).ToString());
        }
    }
    Evaluate(0,0,false,false);
    // F6 can hold the observer camera while the character turns. The engine's
    // GetBaseAimRotation then reads that camera cache, not the gameplay eye.
    if(!PC->PlayerCameraManager)
    {
        PC->PlayerCameraManager=World->SpawnActor<APlayerCameraManager>();
        PC->PlayerCameraManager->InitializeFor(PC);
    }
    PC->SetControlRotation(FRotator::ZeroRotator);Pawn->FirstPersonCamera->SetWorldRotation(FRotator::ZeroRotator);
    World->Tick(LEVELTICK_TimeOnly,1.f/60.f);
    for(const FRotator& Observer:{FRotator::ZeroRotator,FRotator(0,180,0),FRotator(-25,135,0)})
    {
        FMinimalViewInfo View;View.Rotation=Observer;PC->PlayerCameraManager->FillCameraCache(View);
        auto State=Body->SampleLocalState();Body->CaptureMotion(State);Body->DisplayState=State;
        Check(Body->IsThirdPersonViewEnabled(),TEXT("F6 observer mode active for aim source reproduction"));
        Check(FMath::Abs(State.AimYaw)<.1f&&FMath::Abs(State.AimPitch)<.1f,
            FString::Printf(TEXT("gameplay aim independent of observer %.0f/%.0f"),Observer.Pitch,Observer.Yaw),State.AimYaw);
        for(int32 Frame=0;Frame<24;++Frame)
        {
            ++GFrameCounter;Body->ApplyMotion(1.f/60.f);Body->BodyAnimation->BodyState=State;
            NativeBody->TickAnimation(1.f/60.f,false);NativeBody->RefreshBoneTransforms();NativeBody->UpdateChildTransforms();
        }
        const FTransform Frame=NativeBody->GetComponentTransform();
        const FVector R=Frame.InverseTransformPosition(NativeBody->GetSocketLocation(TEXT("hand_r")));
        const FVector L=Frame.InverseTransformPosition(NativeBody->GetSocketLocation(TEXT("hand_l")));
        UE_LOG(LogTemp,Display,TEXT("SAIGA_OBSERVER observer=%s actual_eye=%s sampled=%.1f/%.1f right=%s left=%s"),
            *Observer.ToString(),*Pawn->FirstPersonCamera->GetComponentRotation().ToString(),State.AimPitch,State.AimYaw,*R.ToString(),*L.ToString());
        Check(R.Y>8.f&&L.Y>20.f,TEXT("both hands stay in front with detached observer"),FMath::Min(R.Y,L.Y));
    }
    PC->PlayerCameraManager->SetCameraCachePOV(FMinimalViewInfo());
    Parts(TEXT("vertical_foregrip"),Saiga12KMagazineAssets::DrumPart);
    Check(Pawn->bDrumInstalled&&Pawn->MagazineCapacity==20&&Pawn->LargeDrum&&Pawn->LargeDrum->IsVisible(),TEXT("20 round drum gameplay and source presentation"));
    const auto& DrumDefinition=Body->MotionBindings[0].Definition;
    int32 DrumPart=INDEX_NONE;
    for(int32 I=0;I<DrumDefinition.Parts.Num();++I)if(DrumDefinition.Parts[I].Mesh.ToSoftObjectPath().GetAssetName()==TEXT("SM_Saiga12K_Drum20"))DrumPart=I;
    Check(DrumPart!=INDEX_NONE&&DrumDefinition.Parts[DrumPart].bVisible,TEXT("world equipment contains forward-facing 12K drum"));
    if(DrumPart!=INDEX_NONE)
    {
        const auto& B=Body->MotionBindings[0];auto* Drum=B.Parts[DrumPart].Get();auto* Gun=B.Mesh.Get();
        const FVector AuthoredAxis(-0.000000112113,1.000000000000,0.000000000000);
        const double Dot=FVector::DotProduct(Drum->GetComponentQuat().RotateVector(AuthoredAxis),Gun->GetSocketTransform(TEXT("WPN_root")).TransformVectorNoScale(FVector(0,1,0)).GetSafeNormal());
        Check(Dot>.999,TEXT("installed drum endcap faces muzzle"),Dot);
    }
    // Authored emitter sockets must agree with the actual barrel on both sides.
    for(const TCHAR* Variant:{TEXT("laser"),TEXT("blessed_laser"),TEXT("flashlight")})
    {
        Pawn->SetGunsmithTactical(Variant,Variant);Idle();Evaluate(25,20,true,false);
        const auto& B=Body->MotionBindings[0];auto* Gun=B.Mesh.Get();
        const FVector Axis=Gun->GetSocketTransform(TEXT("WPN_root")).TransformVectorNoScale(FVector(0,1,0)).GetSafeNormal();int32 Count=0;
        for(int32 I=0;I<B.Definition.Parts.Num();++I)if(B.Definition.Parts[I].TacticalKind==Variant)
        {
            auto* Device=B.Parts[I].Get();const bool Sockets=Device&&Device->DoesSocketExist(TEXT("Emitter"))&&Device->DoesSocketExist(TEXT("AimGuide"));
            const double Dot=Sockets?FVector::DotProduct((Device->GetSocketLocation(TEXT("AimGuide"))-Device->GetSocketLocation(TEXT("Emitter"))).GetSafeNormal(),Axis):-1.;
            Check(Sockets&&B.Definition.Parts[I].bAuthoredEmitterAxis&&Dot>.999,FString::Printf(TEXT("world %s slot %d emitter faces muzzle"),Variant,Count),Dot);++Count;
        }
        Check(Count==2,FString(TEXT("both tactical slots captured "))+Variant,Count);
    }
    // Shared motion capture keeps mechanics, attachments and hands on one frame.
    Parts(TEXT("vertical_foregrip"),Saiga12KMagazineAssets::DrumPart);
    struct FActionCase{const TCHAR* Name;UAnimSequence* Clip;EAKMWeaponState State;};
    const FActionCase Actions[]={
        {TEXT("standard reload"),Pawn->ReloadAnimation,EAKMWeaponState::Reloading},
        {TEXT("standard empty"),Pawn->ReloadEmptyAnimation,EAKMWeaponState::ReloadingEmpty},
        {TEXT("drum reload"),Pawn->DrumReloadAnimation,EAKMWeaponState::Reloading},
        {TEXT("drum empty"),Pawn->DrumReloadEmptyAnimation,EAKMWeaponState::ReloadingEmpty},
        {TEXT("inspect"),Pawn->InspectAnimation,EAKMWeaponState::Inspecting},
        {TEXT("equip"),Pawn->EquipAnimation,EAKMWeaponState::Equipping}};
    for(const TCHAR* Grip:{TEXT("false"),TEXT("vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop"),TEXT("angled_foregrip")})
    for(const auto& A:Actions)
    {
        Parts(Grip,FCString::Strncmp(A.Name,TEXT("drum"),4)==0?Saiga12KMagazineAssets::DrumPart:TEXT("false"));
        bool Good=A.Clip!=nullptr;
        if(A.Clip)for(float Phase:{.15f,.45f,.8f,.98f})
        {
            Pawn->WeaponState=A.State;Pawn->ActiveActionAnimation=A.Clip;Pawn->ActionPlayRate=1.f;Pawn->ActionStartPosition=0.f;
            Pawn->bPendingEmptyReload=A.State==EAKMWeaponState::ReloadingEmpty;
            Pawn->WeaponStateDuration=Pawn->ActionDuration=A.Clip->GetPlayLength();Pawn->WeaponStateElapsed=Phase*Pawn->WeaponStateDuration;
            SourcePose();auto S=Body->SampleLocalState();Body->CaptureMotion(S);Body->DisplayState=S;Body->ApplyMotion(.2f);
            Good&=S.Contacts.IsSane()&&S.Contacts.CoupledWrists&&S.Contacts.Wrists==3&&S.Contacts.Fingers==3&&Body->HasMatchingMotionRig(0);
            const auto& B=Body->MotionBindings[0];Good&=B.Smoothed.Valid&&B.Smoothed.Bones.Num()==B.Definition.MotionBones.Num();
            UE_LOG(LogTemp,Display,TEXT("SAIGA_ACTION_POSE %s %s phase=%.2f"),Grip,A.Name,Phase);
            Evaluate(0,0,false,false);
        }
        Check(Good,FString::Printf(TEXT("world action %s / %s hand and mechanical routing"),Grip,A.Name));
    }
    Idle();
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("checks"),Rows.Num());Result->SetNumberField(TEXT("failures"),Failures);Result->SetArrayField(TEXT("results"),Rows);
    Result->SetStringField(TEXT("mode"),TEXT("isolated native animation graph, installed assets and controlled pose samples; no rendered or multiplayer acceptance"));
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    const FString Output=FPaths::ProjectSavedDir()/TEXT("Saiga12KThirdPerson20261018/result.json");IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Json,*Output);
    Model->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {It->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
