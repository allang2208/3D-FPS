#include "ShotgunAttachmentAuditCommandlet.h"
#include "SVCHWeaponAssets.h"
#include "SVCHMagazineAssets.h"
#include "SniperSuppressorAssets.h"
#include "WeaponGripProfile.h"
#include "FPSGunplayAnimInstance.h"
#include "../Characters/FPSArmJointCorrectiveComponent.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "GunsmithSystem.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/NameAsStringProxyArchive.h"

// Explicit, isolated asset/pose/authority/packet checks. A separate UDP fixture
// exercises transport; this commandlet never modifies the player's profile.
int32 UShotgunAttachmentAuditCommandlet::RunSVCHReview(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=SVCHReview_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SVCHReview"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();auto* Gunsmith=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Model||!Model->IsAudit()||!Gunsmith)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool Pass,const FString& Name,double Value=0.)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Pass);Row->SetNumberField(TEXT("value"),Value);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("SVCH_REVIEW %s %s %.6f"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Value);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    auto Item=Model->CreateItem(SVCHWeaponAssets::Definition);Item.InstanceId=TEXT("SVCHReviewItem");Item.Place=1;Item.Cell=6;Item.Magazine=10;Seed.Items={Item};Model->Current=Seed;
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->SetPlayerState(World->SpawnActor<AColdSteelPlayerState>());
    auto* Local=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Local);
    Local->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Local->DispatchBeginPlay();Model->CurrentPawn=Local;
    // Explicit hand-only diagnostic: sample the real Gunplay graph (including
    // action/idle handoff), not just source bones with an offline pose layer.
    if(FParse::Param(*Params,TEXT("SVCHHandOnly")))
    {
        FString Candidate,Output;
        FParse::Value(*Params,TEXT("Candidate="),Candidate);
        if(!FParse::Value(*Params,TEXT("Output="),Output))Output=FPaths::ProjectSavedDir()/TEXT("SVCHHandReview/poses.json");
        auto Result=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Families;
        const auto Pack=[](const FTransform& T)
        {
            const FVector P=T.GetTranslation(),S=T.GetScale3D();const FQuat Q=T.GetRotation();
            TArray<TSharedPtr<FJsonValue>> V;
            for(double X:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})V.Add(MakeShared<FJsonValueNumber>(X));
            return V;
        };
        auto* V9=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7"));
        if(FParse::Param(*Params,TEXT("SVCHBlueGlove")))
        {
            auto Gloves=Model->CreateItem(TEXT("ue_blue_mage_gloves"));Gloves.Place=1;Gloves.Cell=3;
            Model->Current.Items.Add(Gloves);
        }
        const TCHAR* Grips[]={TEXT("false"),TEXT("angled_foregrip"),TEXT("vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop")};
        const TCHAR* FamilyNames[]={TEXT("base"),TEXT("angled"),TEXT("vertical"),TEXT("canted"),TEXT("prism")};
        for(int32 FamilyIndex=0;FamilyIndex<5;++FamilyIndex)
        {
            TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Model->Current.Items[0].Data),Data);
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("underbarrel"),Grips[FamilyIndex]);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
            Model->Current.Items[0].Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Model->Current.Items[0].Data));
            Local->ApplyColdSteelProfile(Model);Local->bInventoryWeaponReady=true;Local->WeaponState=EAKMWeaponState::Idle;
            // Let the same outfit loader as gameplay provide its actual hand
            // carriers. A synthetic V9 follower would hide routing failures.
            if(auto* Outfit=Local->FindComponentByClass<UFPSModularOutfitComponent>())
            {
                Outfit->RefreshInventory();
                for(int32 Warmup=0;Warmup<3;++Warmup)
                {FlushAsyncLoading();Outfit->TickComponent(.3f,LEVELTICK_All,nullptr);}
            }
            FlushAsyncLoading();
            const FName Family(FamilyNames[FamilyIndex]);
            if(!Candidate.IsEmpty())
            {
                FString Json;
                if(!FFileHelper::LoadFileToString(Json,*(Candidate/(Family.ToString()+TEXT(".json")))))return 2;
                auto* Trial=NewObject<UWeaponGripProfile>(Local);
                if(!Trial->SetSharedClipsFromJson(Json))return 2;
                Local->WeaponGripProfiles.Add(Family,Trial);
            }
            Local->ActiveActionAnimation=nullptr;Local->WeaponADSFactor=0.f;Local->UpdateActionPose(0.f);
            auto FamilyRow=MakeShared<FJsonObject>();FamilyRow->SetStringField(TEXT("family"),Family.ToString());
            TArray<TSharedPtr<FJsonValue>> Surfaces;
            TInlineComponentArray<USkeletalMeshComponent*> SurfaceComponents;Local->GetComponents(SurfaceComponents);
            for(auto* Part:SurfaceComponents)if(Part->GetSkeletalMeshAsset()&&Part->IsVisible())
            {
                auto Info=MakeShared<FJsonObject>();Info->SetStringField(TEXT("component"),Part->GetName());
                Info->SetStringField(TEXT("mesh"),Part->GetSkeletalMeshAsset()->GetPathName());
                Info->SetStringField(TEXT("leader"),GetNameSafe(Part->LeaderPoseComponent.Get()));
                TArray<TSharedPtr<FJsonValue>> MorphNames;
                for(const auto& Morph:Part->GetSkeletalMeshAsset()->GetMorphTargets())if(Morph)MorphNames.Add(MakeShared<FJsonValueString>(Morph->GetName()));
                Info->SetArrayField(TEXT("morph_names"),MorphNames);Surfaces.Add(MakeShared<FJsonValueObject>(Info));
            }
            FamilyRow->SetArrayField(TEXT("visible_surfaces"),Surfaces);
            auto* Mesh=Local->AKMViewmodel.Get();auto* Anim=Cast<UFPSGunplayAnimInstance>(Mesh->GetAnimInstance());
            if(!Anim||!V9)return 2;
            FamilyRow->SetArrayField(TEXT("view_to_camera"),Pack(Mesh->GetComponentTransform().GetRelativeTransform(Local->FirstPersonCamera->GetComponentTransform())));
            FamilyRow->SetNumberField(TEXT("camera_horizontal_fov"),Local->FirstPersonCamera->FieldOfView);
            FamilyRow->SetNumberField(TEXT("camera_aspect"),Local->FirstPersonCamera->AspectRatio);
            TArray<TSharedPtr<FJsonValue>> Names,Frames;
            const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
            for(int32 B=0;B<Ref.GetNum();++B)Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(B).ToString()));
            FamilyRow->SetArrayField(TEXT("names"),Names);
            for(int32 Frame=-1;Frame<=108;++Frame)
            {
                const float Time=FMath::Max(0,Frame)/120.f;
                Local->WeaponState=Frame<0?EAKMWeaponState::Idle:EAKMWeaponState::QuickCombat;
                Local->ActiveActionAnimation=Frame<0?nullptr:Local->QuickCombatAnimation;
                Local->ActionStartPosition=0.f;Local->ActionPlayRate=1.f;
                Local->WeaponStateDuration=Local->ActionDuration=.9f;Local->WeaponStateElapsed=Time;
                Local->UpdateActionPose(0.f);++GFrameCounter;
                Mesh->TickAnimation(0.f,false);Mesh->RefreshBoneTransforms();Mesh->UpdateChildTransforms();
                if(auto* Correctives=Local->FindComponentByClass<UFPSArmJointCorrectiveComponent>())
                    Correctives->TickComponent(.3f,LEVELTICK_All,nullptr);
                auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("frame"),Frame);
                Row->SetNumberField(TEXT("time"),Time);Row->SetNumberField(TEXT("action_time"),Anim->ActionTime);
                Row->SetNumberField(TEXT("action_alpha"),Anim->ActionAlpha);
                Row->SetStringField(TEXT("profile"),GetPathNameSafe(Anim->GripProfile));
                TArray<TSharedPtr<FJsonValue>> Bones;
                for(const FTransform& T:Mesh->GetComponentSpaceTransforms())Bones.Add(MakeShared<FJsonValueArray>(Pack(T)));
                Row->SetArrayField(TEXT("bones"),Bones);
                auto Morphs=MakeShared<FJsonObject>();
                for(const auto& Morph:V9->GetMorphTargets())if(Morph)Morphs->SetNumberField(Morph->GetName(),Mesh->GetMorphTarget(Morph->GetFName()));
                Row->SetObjectField(TEXT("morphs"),Morphs);Frames.Add(MakeShared<FJsonValueObject>(Row));
            }
            FamilyRow->SetArrayField(TEXT("frames"),Frames);Families.Add(MakeShared<FJsonValueObject>(FamilyRow));
        }
        Result->SetArrayField(TEXT("families"),Families);Result->SetBoolField(TEXT("real_gunplay_graph"),true);
        Result->SetBoolField(TEXT("candidate_transient"),!Candidate.IsEmpty());
        FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Json));
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);const bool Saved=FFileHelper::SaveStringToFile(Json,*Output);
        for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
        {It->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
        Model->CurrentPawn.Reset();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
        UE_LOG(LogTemp,Display,TEXT("SVCH_HAND_REVIEW_COMPLETE saved=%d"),Saved);
        return Saved?0:2;
    }
    auto* RemotePC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();PS->SetOwner(RemotePC);RemotePC->SetPlayerState(PS);
    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,500),FRotator::ZeroRotator);RemotePC->Possess(Remote);Remote->SetPlayerState(PS);
    auto* Shadow=Model->CreateShadowModel(Seed);PS->ShadowModel=Shadow;Remote->NetShadowProfile=Shadow;Shadow->CurrentPawn=Remote;
    Remote->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Remote->DispatchBeginPlay();
    auto* Body=Local->FindComponentByClass<UFPSPlayerBodyComponent>();auto* RemoteBody=Remote->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!RemoteBody)return 2;
    const auto Configure=[&](AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Profile,const TCHAR* Grip,bool Extended,bool Suppressed)
    {
        auto& I=Profile->Current.Items[0];TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("underbarrel"),Grip);Parts->SetStringField(TEXT("magazine"),Extended?TEXT("ext_mag"):TEXT("false"));
        Parts->SetStringField(TEXT("muzzle"),Suppressed?SniperSuppressorAssets::Part:TEXT("false"));
        Parts->SetStringField(TEXT("optic"),TEXT("false"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
        I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));
        Pawn->ApplyColdSteelProfile(Profile);Pawn->bInventoryWeaponReady=true;Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;Pawn->WeaponADSFactor=0.f;
        Pawn->UpdateActionPose(0.f);++GFrameCounter;Pawn->AKMViewmodel->TickAnimation(0.f,false);Pawn->AKMViewmodel->RefreshBoneTransforms();Pawn->AKMViewmodel->UpdateChildTransforms();
        auto* B=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();B->DisplayState=Pawn->IsLocallyControlled()?B->SampleLocalState():B->SampleRemoteAuthorityState();B->CaptureEquipment();
    };
    for(const TCHAR* Grip:{TEXT("vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop")})Configure(Local,Model,Grip,false,false);
    uint32 Sequence=1;
    for(const TCHAR* Grip:{TEXT("false"),TEXT("angled_foregrip"),TEXT("vertical_foregrip"),TEXT("tactical_vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop")})
    for(bool Extended:{false,true})
    {
        Configure(Local,Model,Grip,Extended,true);Configure(Remote,Shadow,Grip,Extended,true);
        const FString Prefix=FString(Grip)+(Extended?TEXT("/20 "):TEXT("/10 "));
        if(Body->LocalWeapons.Num()!=1||RemoteBody->LocalWeapons.Num()!=1){Check(false,Prefix+TEXT("weapon manifests"));continue;}
        const auto& A=Body->LocalWeapons[0];const auto& B=RemoteBody->LocalWeapons[0];
        Check(A.MotionSchema==B.MotionSchema&&A.Parts.Num()==B.Parts.Num(),Prefix+TEXT("owner preview history cannot change part schema"));
        Check(Body->BodyAnimation&&Body->BodyAnimation->RifleHold.bValid&&RemoteBody->BodyAnimation&&RemoteBody->BodyAnimation->RifleHold.bValid,Prefix+TEXT("calibrated full-body hold"));
        Check(Local->GetMagazineCapacity()==(Extended?20:10)&&Remote->GetMagazineCapacity()==Local->GetMagazineCapacity(),Prefix+TEXT("magazine capacity"));
        Check(A.bGunSuppressed&&B.bGunSuppressed&&A.MuzzlePart!=INDEX_NONE&&A.MuzzleTip.Equals(FVector(SniperSuppressorAssets::TipCM,0,0),.01),Prefix+TEXT("observer suppressor and exit"));
        UE_LOG(LogTemp,Display,TEXT("SVCH_REVIEW_MUZZLE local=%d remote=%d index=%d tip=%s variant=%s remote_variant=%s part=%s"),
            A.bGunSuppressed,B.bGunSuppressed,A.MuzzlePart,*A.MuzzleTip.ToString(),*Local->MuzzleVariant,*Remote->MuzzleVariant,
            *GetPathNameSafe(Local->MuzzleAttachment?Local->MuzzleAttachment->GetStaticMesh():nullptr));
        auto* Profile=Local->WeaponGripProfileFor(Local->ResolveRifleGripProfile());
        Check(Profile&&Profile->FindAction(TEXT("quick_melee"))&&Local->RifleQuickCombatClip(Local->ResolveRifleGripProfile())==Local->QuickCombatAnimation,Prefix+TEXT("native quick-melee profile selected"));
        struct FCase{const TCHAR* Name;UAnimSequence* Clip;EAKMWeaponState State;float Time;};
        const FCase Cases[]={{TEXT("inspect"),Local->InspectAnimation,EAKMWeaponState::Inspecting,1.2f},
            {TEXT("normal mag seat"),Local->ReloadAnimation,EAKMWeaponState::Reloading,240.f/120.f},
            {TEXT("empty left bolt"),Local->ReloadEmptyAnimation,EAKMWeaponState::ReloadingEmpty,325.f/120.f},
            {TEXT("empty regrip"),Local->ReloadEmptyAnimation,EAKMWeaponState::ReloadingEmpty,416.f/120.f},
            {TEXT("quick contact"),Local->QuickCombatAnimation,EAKMWeaponState::QuickCombat,20.f/120.f},
            {TEXT("quick recovery"),Local->QuickCombatAnimation,EAKMWeaponState::QuickCombat,68.f/120.f}};
        for(const auto& C:Cases)
        {
            if(!C.Clip){Check(false,Prefix+C.Name+TEXT(" missing clip"));continue;}
            Local->WeaponState=C.State;Local->bPendingEmptyReload=C.State==EAKMWeaponState::ReloadingEmpty;Local->ActiveActionAnimation=C.Clip;
            Local->ActionStartPosition=0.f;Local->ActionPlayRate=1.f;Local->WeaponStateDuration=Local->ActionDuration=C.Clip->GetPlayLength();Local->WeaponStateElapsed=C.Time;
            Local->UpdateActionPose(0.f);++GFrameCounter;Local->AKMViewmodel->TickAnimation(0.f,false);Local->AKMViewmodel->RefreshBoneTransforms();Local->AKMViewmodel->UpdateChildTransforms();
            auto State=Body->SampleLocalState();
            if(C.State==EAKMWeaponState::QuickCombat){State.Action=EFPSBodyAction::GunBash;State.ActionVariant=TEXT("RifleBash");}
            Body->CaptureMotion(State);Body->DisplayState=State;
            TArray<uint8> Bytes;bool Saved=false,Loaded=false;auto Sent=State.Contacts;
            {FMemoryWriter Memory(Bytes);FNameAsStringProxyArchive Archive(Memory);Sent.NetSerialize(Archive,nullptr,Saved);}
            FFPSBodyMotionSample Received;
            {FMemoryReader Memory(Bytes);FNameAsStringProxyArchive Archive(Memory);Received.NetSerialize(Archive,nullptr,Loaded);}
            Check(Saved&&Loaded&&Received.IsSane()&&Received.SupportGrip.Equals(Sent.SupportGrip,.025),Prefix+C.Name+TEXT(" packet retains hands"));
            State.Contacts=Received;RemoteBody->AcceptBodyPresentation(State,Sequence++);RemoteBody->ApplyMotion(.2f);
            Check(RemoteBody->HasMatchingMotionRig(0),Prefix+C.Name+TEXT(" authority accepts mechanics"));
            Check(RemoteBody->BodyAnimation->LeftGripFromRight.Equals(State.Contacts.SupportGrip,.05),Prefix+C.Name+TEXT(" observer support contact"));
            if(C.State==EAKMWeaponState::QuickCombat)
            {
                Check(Received.Wrists==3&&Received.CoupledWrists&&Received.Channel==TEXT("QuickMelee"),Prefix+C.Name+TEXT(" native bash drives both world hands"));
                auto* V9=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7"));
                if(V9)
                {
                    const auto& Ref=V9->GetRefSkeleton();auto Rest=Ref.GetRefBonePose();
                    for(int32 I=0;I<Rest.Num();++I)if(Ref.GetParentIndex(I)>=0)Rest[I]=Rest[I]*Rest[Ref.GetParentIndex(I)];
                    const int32 H=Ref.FindBoneIndex(TEXT("hand_r")),L=Ref.FindBoneIndex(TEXT("lowerarm_r"));
                    const auto Hand=Local->AKMViewmodel->GetSocketTransform(TEXT("hand_r"),RTS_Component);
                    const auto Elbow=Local->AKMViewmodel->GetSocketTransform(TEXT("lowerarm_r"),RTS_Component);
                    const FVector Ideal=(Hand.GetRotation()*Rest[H].GetRotation().Inverse()).RotateVector((Rest[H].GetLocation()-Rest[L].GetLocation()).GetSafeNormal());
                    const double Angle=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Ideal,(Hand.GetLocation()-Elbow.GetLocation()).GetSafeNormal()),-1.,1.)));
                    Check(Angle<32.,Prefix+C.Name+TEXT(" actual gunplay wrist bend degrees"),Angle);
                }
            }
        }
    }
    if(FParse::Param(*Params,TEXT("SVCHExecution")))
    {
#include "SVCHQuickCombatReview.inl"
    }
    for(const TCHAR* Definition:{TEXT("ue_svd"),TEXT("ue_svch")})
    {
        auto I=Model->CreateItem(Definition);I.Place=1;I.Cell=6;
        Check(ColdSteelInventory::Text(I,TEXT("weaponType"))==TEXT("sniper")&&ColdSteelSkills::IsRifle(&I)&&FMath::IsNearlyEqual(ColdSteelInventory::Number(I,TEXT("critDamageBonus")),1.),FString(Definition)+TEXT(" class crit and rifle mastery"));
        const auto Base=Gunsmith->Calculate(Definition,{});
        const auto Mod=Gunsmith->Calculate(Definition,{{TEXT("muzzle"),SniperSuppressorAssets::Part}});
        Check(FMath::IsNearlyEqual(Mod.Speed/Base.Speed,.75,.0001)&&FMath::IsNearlyEqual(Mod.RecoilMultiplier/Base.RecoilMultiplier,.60,.0001)&&FMath::IsNearlyEqual(Mod.StabilityMultiplier/Base.StabilityMultiplier,1.30,.0001),FString(Definition)+TEXT(" suppressor multipliers"));
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);
        Data->SetStringField(TEXT("weaponType"),TEXT("rifle"));Data->SetNumberField(TEXT("critDamageBonus"),.5);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("muzzle"),SniperSuppressorAssets::Part);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));auto Legacy=Seed;Legacy.Items={I};
        auto* Migrated=Model->CreateShadowModel(Legacy);Remote->NetShadowProfile=Migrated;
        const auto* Held=Migrated?Migrated->Equipped():nullptr;
        Check(Held&&ColdSteelInventory::Text(*Held,TEXT("weaponType"))==TEXT("sniper")&&FMath::IsNearlyEqual(ColdSteelInventory::Number(*Held,TEXT("critDamageBonus")),1.),FString(Definition)+TEXT(" legacy guest shadow migration"));
        const auto Shot=ColdSteelSkills::Snapshot(Remote,Held,true);const auto Melee=ColdSteelSkills::Snapshot(Remote,Held,false);
        Check(Shot.bSilentLethalShot&&Shot.bRifle&&!Melee.bSilentLethalShot,FString(Definition)+TEXT(" server shadow silent-shot scope excludes melee"));
    }
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("checks"),Rows.Num());Result->SetNumberField(TEXT("failures"),Failures);Result->SetArrayField(TEXT("results"),Rows);Result->SetBoolField(TEXT("socket_transport"),false);Result->SetBoolField(TEXT("rendered"),false);
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));FString Output;
    if(!FParse::Value(*Params,TEXT("Output="),Output))Output=FPaths::ProjectSavedDir()/TEXT("SVCHReview20261019/result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Json,*Output);
    Model->CurrentPawn.Reset();for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {It->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
