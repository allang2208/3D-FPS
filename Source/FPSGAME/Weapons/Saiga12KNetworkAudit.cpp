#include "ShotgunAttachmentAuditCommandlet.h"
#include "Saiga12KWeaponAssets.h"
#include "Saiga12KMagazineAssets.h"
#include "Saiga12KAttachments.h"
#include "ShotgunSuppressorAssets.h"
#include "WeaponGripProfile.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodyWeaponMeshComponent.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "Sound/SoundBase.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/NameAsStringProxyArchive.h"

// Explicit S12K regression: actual assets, authority presentation and packet
// codec. Socket transport is a separate fixture; no player saves are modified.
int32 UShotgunAttachmentAuditCommandlet::RunSaiga12KNetworkAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=SaigaNet_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SaigaNetworkAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool Pass,const FString& Name,double Value=0.)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Pass);Row->SetNumberField(TEXT("value"),Value);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("SAIGA_NETWORK %s %s %.6f"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Value);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    auto Item=Model->CreateItem(Saiga12KWeaponAssets::Definition);Item.InstanceId=TEXT("SaigaNetworkItem");Item.Place=1;Item.Cell=6;Item.Magazine=20;Seed.Items={Item};Model->Current=Seed;
    auto* PC=World->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();PC->SetPlayerState(World->SpawnActor<AColdSteelPlayerState>());
    auto* Local=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);PC->Possess(Local);
    Local->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Local->DispatchBeginPlay();Model->CurrentPawn=Local;
    auto* RemotePC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();PS->SetOwner(RemotePC);RemotePC->SetPlayerState(PS);
    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,500),FRotator::ZeroRotator);RemotePC->Possess(Remote);Remote->SetPlayerState(PS);
    auto* Shadow=Model->CreateShadowModel(Seed);PS->ShadowModel=Shadow;Remote->NetShadowProfile=Shadow;Shadow->CurrentPawn=Remote;
    Remote->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Remote->DispatchBeginPlay();
    auto* Body=Local->FindComponentByClass<UFPSPlayerBodyComponent>();auto* RemoteBody=Remote->FindComponentByClass<UFPSPlayerBodyComponent>();
    const auto Configure=[&](AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Profile,const TCHAR* Grip,const TCHAR* Mag,const TCHAR* Stock,const TCHAR* Muzzle,const TCHAR* Optic)
    {
        auto Data=MakeShared<FJsonObject>();auto Parts=MakeShared<FJsonObject>();
        Parts->SetStringField(TEXT("underbarrel"),Grip);Parts->SetStringField(TEXT("magazine"),Mag);Parts->SetStringField(TEXT("stock"),Stock);
        Parts->SetStringField(TEXT("muzzle"),Muzzle);Parts->SetStringField(TEXT("optic"),Optic);Parts->SetStringField(TEXT("tactical"),TEXT("laser"));Parts->SetStringField(TEXT("tactical_secondary"),TEXT("blessed_laser"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("gunsmith_version"),1);
        auto& I=Profile->Current.Items[0];I.Data.Reset();FJsonSerializer::Serialize(Data,TJsonWriterFactory<>::Create(&I.Data));
        Pawn->ApplyColdSteelProfile(Profile);Pawn->bInventoryWeaponReady=true;Pawn->WeaponState=EAKMWeaponState::Idle;Pawn->ActiveActionAnimation=nullptr;Pawn->WeaponADSFactor=0.f;
        Pawn->UpdateActionPose(0.f);++GFrameCounter;Pawn->AKMViewmodel->TickAnimation(0.f,false);Pawn->AKMViewmodel->RefreshBoneTransforms();Pawn->AKMViewmodel->UpdateChildTransforms();
        auto* B=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();B->DisplayState=Pawn->IsLocallyControlled()?B->SampleLocalState():B->SampleRemoteAuthorityState();B->CaptureEquipment();
    };
    // Only the owning client has previewed these older grip families. The
    // server receives the final loadout, as with a coalesced equipment update.
    for(const TCHAR* Grip:{TEXT("vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop")})
        Configure(Local,Model,Grip,TEXT("false"),TEXT("false"),TEXT("false"),TEXT("false"));
    const auto Final=[&](AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Profile)
    {Configure(Pawn,Profile,TEXT("angled_foregrip"),Saiga12KMagazineAssets::DrumPart,Saiga12KSpecialStockAssets::Part,TEXT("shotgun_suppressor"),TEXT("panoramic_red_dot"));};
    Final(Local,Model);Final(Remote,Shadow);
    Check(Body&&RemoteBody&&Body->LocalWeapons.Num()==1&&RemoteBody->LocalWeapons.Num()==1,TEXT("owner and remote authority both capture S12K"));
    if(Body->LocalWeapons.Num()!=1||RemoteBody->LocalWeapons.Num()!=1)return 2;
    const auto& A=Body->LocalWeapons[0];const auto& B=RemoteBody->LocalWeapons[0];
    Check(A.MotionSchema==B.MotionSchema,TEXT("same final loadout has identical schema despite grip preview history"));
    Check(A.Parts.Num()==B.Parts.Num(),TEXT("same final loadout has identical attachment count"),A.Parts.Num()-B.Parts.Num());
    Check(A.GripProfile.ToSoftObjectPath()==B.GripProfile.ToSoftObjectPath()&&A.GripProfile.LoadSynchronous(),TEXT("both peers resolve current angled grip profile"));
    Check(A.GunFireSound.ToSoftObjectPath().GetLongPackageName()==Saiga12KWeaponAssets::FireSoundPath&&B.GunFireSound==A.GunFireSound,TEXT("native S12K fire sound published to observers"));
    Check(A.GunSuppressedSound.ToSoftObjectPath().GetLongPackageName()==ShotgunSuppressorAssets::SoundPath&&B.GunSuppressedSound==A.GunSuppressedSound,TEXT("shared shotgun suppressor sound published to observers"));
    Check(FMath::IsNearlyEqual(Local->EffectiveFireInterval(),Remote->EffectiveFireInterval()),TEXT("stock cadence agrees on owner and authority"),Local->EffectiveFireInterval());
    Check(Local->GetMagazineCapacity()==20&&Remote->GetMagazineCapacity()==20,TEXT("drum capacity is 20 on owner and authority"));
    Check(!Local->UsesSingleShotTrigger()&&!Remote->UsesSingleShotTrigger(),TEXT("S12K retains hold-to-fire automatic trigger"));
    const auto HasPart=[](const FFPSBodyWeapon& W,const TCHAR* S){return W.Parts.ContainsByPredicate([S](const FFPSBodyAttachment& P){return P.bVisible&&P.Mesh.ToSoftObjectPath().ToString().Contains(S);});};
    Check(HasPart(A,TEXT("SM_Saiga12K_Drum20"))&&HasPart(B,TEXT("SM_Saiga12K_Drum20")),TEXT("20-round drum appears in both manifests"));
    Check(HasPart(A,TEXT("SM_Saiga12K_SpecialStock"))&&HasPart(B,TEXT("SM_Saiga12K_SpecialStock")),TEXT("S12K special stock appears in both manifests"));
    struct FCase{const TCHAR* Role;UAnimSequence* Clip;EAKMWeaponState State;float Fraction;};
    const FCase Cases[]={{TEXT("idle"),Local->IdleAnimation,EAKMWeaponState::Idle,0.f},{TEXT("inspect"),Local->InspectAnimation,EAKMWeaponState::Inspecting,.5f},{TEXT("drum reload"),Local->DrumReloadAnimation,EAKMWeaponState::Reloading,.5f},{TEXT("drum empty regrip"),Local->DrumReloadEmptyAnimation,EAKMWeaponState::ReloadingEmpty,.88f}};
    uint32 Sequence=1;
    for(const auto& C:Cases)
    {
        Local->WeaponState=C.State;Local->bPendingEmptyReload=C.State==EAKMWeaponState::ReloadingEmpty;Local->ActiveActionAnimation=C.State==EAKMWeaponState::Idle?nullptr:C.Clip;
        Local->ActionStartPosition=0.f;Local->ActionPlayRate=1.f;Local->WeaponStateDuration=Local->ActionDuration=C.Clip->GetPlayLength();Local->WeaponStateElapsed=C.Fraction*Local->WeaponStateDuration;
        Local->UpdateActionPose(0.f);++GFrameCounter;Local->AKMViewmodel->TickAnimation(0.f,false);Local->AKMViewmodel->RefreshBoneTransforms();Local->AKMViewmodel->UpdateChildTransforms();
        auto State=Body->SampleLocalState();Body->CaptureMotion(State);Body->DisplayState=State;Body->CaptureLaserPresentation();State=Body->DisplayState;
        TArray<uint8> Bytes;bool Saved=false,Loaded=false;auto Sent=State.Contacts;
        {FMemoryWriter Memory(Bytes);FNameAsStringProxyArchive Archive(Memory);Sent.NetSerialize(Archive,nullptr,Saved);}
        FFPSBodyMotionSample Received;
        {FMemoryReader Memory(Bytes);FNameAsStringProxyArchive Archive(Memory);Received.NetSerialize(Archive,nullptr,Loaded);}
        Check(Saved&&Loaded&&Received.IsSane()&&Received.SupportGrip.Equals(Sent.SupportGrip,.025),FString(C.Role)+TEXT(" packet retains support grip"));
        State.Contacts=Received;RemoteBody->AcceptBodyPresentation(State,Sequence++);RemoteBody->ApplyMotion(.2f);
        Check(RemoteBody->HasMatchingMotionRig(0),FString(C.Role)+TEXT(" remote accepts owner rig after equipment history divergence"));
        Check(RemoteBody->BodyAnimation->LeftGripFromRight.Equals(State.Contacts.SupportGrip,.05),FString(C.Role)+TEXT(" remote applies owner support grip"));
    }
    auto Stale=Body->DisplayState;Stale.WeaponInstance=TEXT("previous-copy-of-S12K");RemoteBody->AcceptBodyPresentation(Stale,Sequence++);
    Check(!RemoteBody->DisplayState.Contacts.HasSupportGrip,TEXT("old instance cannot overwrite current hand contact"));
    RemoteBody->LastPresentationReceivedAt=RemoteBody->ServerClock()-1.f;RemoteBody->DisplayState=RemoteBody->SampleRemoteAuthorityState();
    Check(!RemoteBody->DisplayState.Contacts.HasSupportGrip&&RemoteBody->DisplayState.Lasers.IsEmpty(),TEXT("expired presentation clears grip and laser"));
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("checks"),Rows.Num());Result->SetNumberField(TEXT("failures"),Failures);Result->SetArrayField(TEXT("results"),Rows);Result->SetBoolField(TEXT("socket_transport"),false);
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));FString Output;
    if(!FParse::Value(*Params,TEXT("Output="),Output))Output=FPaths::ProjectSavedDir()/TEXT("Saiga12KNetwork20261019/result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Json,*Output);
    Model->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {It->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
