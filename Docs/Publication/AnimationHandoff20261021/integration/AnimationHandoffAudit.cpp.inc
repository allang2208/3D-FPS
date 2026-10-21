#include "ShotgunAttachmentAuditCommandlet.h"
#include "OffhandReloadHandoff.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSPlayerBodyAnimInstance.h"
#include "../Characters/FPSBodyPistolMotion.h"
#include "../Characters/FPSBodyWarhammerMotion.h"
#include "../Skills/SkillNetworkAuditCommandlet.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

namespace FPSBodyNetwork { bool IsTransition(const FFPSBodyState&,const FFPSBodyState&); }

// Explicit offline review: real authority handlers and reflected state fields,
// isolated profiles. This is not socket transport or a rendered multiplayer run.
int32 UShotgunAttachmentAuditCommandlet::RunAnimationHandoffAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    FCommandLine::Set(*(Original+TEXT(" -ShotgunAttachmentAudit -ColdSteelProfile=AnimationHandoff_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("AnimationHandoffAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool Pass,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),Pass);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!Pass;
        UE_LOG(LogTemp,Display,TEXT("HANDOFF_AUDIT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    auto Pistol=Model->CreateItem(TEXT("ue_m1911"));Pistol.Place=1;Pistol.Cell=6;Pistol.Magazine=1;
    auto Book=Model->CreateItem(TEXT("ue_alchemy_spellbook"));Book.Place=1;Book.Cell=8;
    auto Second=Model->CreateItem(TEXT("ue_g18"));Second.Place=1;Second.Cell=8;Second.Magazine=10;
    auto Hammer=Model->CreateItem(TEXT("ue_steel_warhammer"));Hammer.Place=1;Hammer.Cell=6;
    Seed.Items={Pistol};Model->Current=Seed;
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    auto* Shadow=Model->CreateShadowModel(Seed);PS->ShadowModel=Shadow;Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pawn->DispatchBeginPlay();
    Pawn->SetActorTickEnabled(false);
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    if(!Body||!Body->BodyAnimation)return 2;
    Body->SetComponentTickEnabled(false);
    uint32 Sequence=0;
    const auto Configure=[&](TArray<FColdSteelItem> Items)
    {
        auto Profile=Seed;Profile.Items=MoveTemp(Items);Shadow->Current=Profile;
        Pawn->ApplyColdSteelProfile(Shadow);Body->bHasReportedPresentation=false;
        Body->DisplayState=Body->SampleRemoteAuthorityState();Body->CaptureEquipment();
        return Body->DisplayState;
    };
    auto Single=Configure({Pistol});const float NativeReload=Pawn->GetReloadSeconds(true);
    auto WithBook=Configure({Pistol,Book});
    Check(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled()&&WithBook.OffhandInstance==Book.InstanceId,
        TEXT("remote authority resolves guest offhand identity"));
    UE_LOG(LogTemp,Display,TEXT("HANDOFF_RELOAD native=%.9f with_offhand=%.9f expected=%.9f"),
        NativeReload,Pawn->GetReloadSeconds(true),NativeReload+.95f);
    Check(FMath::IsNearlyEqual(Pawn->GetReloadSeconds(true),NativeReload+.95f,.0001f),
        TEXT("guest non-pistol offhand adds full handling cost"));
    Check(Model->Equipped(8)==nullptr,TEXT("guest reload does not add equipment to host profile"));
    bool BookRigChecked=false;
    for(int32 I=0;I<Body->MotionBindings.Num();++I)
    {
        const auto& Binding=Body->MotionBindings[I];
        if(Binding.Definition.PoseFamily!=TEXT("Spellbook"))continue;
        Body->DisplayState=WithBook;Body->DisplayState.Contacts.Rigs.SetNum(Body->MotionBindings.Num());
        auto& Rig=Body->DisplayState.Contacts.Rigs[I];Rig.Valid=true;Rig.Schema=Binding.Definition.MotionSchema;
        Rig.Bones.SetNum(Binding.Definition.MotionBones.Num());Rig.Parts.SetNum(Binding.Parts.Num());
        Check(Body->HasMatchingMotionRig(I),TEXT("matching book instance accepts mechanical sample"));
        Body->DisplayState.OffhandInstance=TEXT("old-book-same-layout");
        Check(!Body->HasMatchingMotionRig(I),TEXT("old book instance cannot drive new same-schema book"));
        BookRigChecked=true;
    }
    Check(BookRigChecked,TEXT("remote loadout includes a book rig"));
    PS->ServerAmmoInstance=Pistol.InstanceId;PS->ServerMagazineAmmo=1;FString Reason;
    Check(PS->ConsumeServerAmmo(Shadow->Equipped(),1,10.,Reason)&&
        FMath::IsNearlyEqual(PS->ServerReloadReadyAt,10.+double(NativeReload+.95f),.001),
        TEXT("authority ammo deadline includes offhand handling"));
    PC->SetControlRotation(FRotator(30.f,20.f,0.f));
    auto* Movement=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());Movement->bWantsToAim=true;
    auto Send=[&](FFPSBodyState State)
    {
        State.PresentationSampledAt=Body->ServerClock();
        Body->ServerBodyTransition_Implementation(State,++Sequence);return Body->ReplicatedState;
    };
    auto Lower=WithBook;Lower.OffhandReloadPhase=uint8(EOffhandReloadPhase::Lower);Lower.OffhandReloadProgress=.8f;
    Lower.OffhandReloadProgressRate=1.f/FOffhandReloadHandoff::LowerSeconds;Lower.OffhandReloadLowerWeight=.9f;
    Lower.AimPitch=-70.f;Lower.bAiming=false;
    auto Received=Send(Lower);
    Check(Received.OffhandReloadPhase==Lower.OffhandReloadPhase&&Received.OffhandReloadProgress==.8f,
        TEXT("lower phase and progress reach authority relay"));
    Check(Received.bAiming&&FMath::IsNearlyEqual(Received.AimPitch,30.f),TEXT("remote aim comes from authority controller and CMC"));
    auto Reload=Lower;Reload.OffhandReloadPhase=uint8(EOffhandReloadPhase::Reload);Reload.Action=EFPSBodyAction::ReloadEmpty;
    Reload.OffhandReloadProgress=0.f;Reload.OffhandReloadProgressRate=0.f;
    auto Returning=Reload;Returning.OffhandReloadPhase=uint8(EOffhandReloadPhase::Raise);
    Returning.bOffhandReloadReturnFromReload=true;Returning.OffhandReloadProgress=.1f;Returning.OffhandReloadProgressRate=1.f;
    Received=Send(Returning);
    Check(FPSBodyPistolMotion::ReturningHandWithoutItem(Received)&&FPSBodyPistolMotion::OffhandItemHidden(Received)
        &&!FPSBodyPistolMotion::UsesSupportReload(Received),TEXT("early return exits empty hand without pistol regrip"));
    Check(FPSBodyNetwork::IsTransition(Returning,Reload),TEXT("reload-to-return uses reliable edge"));
    auto Later=Returning;Later.OffhandReloadProgress=.7f;
    Received=Send(Later);
    Check(!FPSBodyPistolMotion::OffhandItemHidden(Received)&&FPSBodyPistolMotion::OffhandBodyLowerWeight(Received)<1.f,
        TEXT("late return reveals the offhand gradually"));
    const uint32 Accepted=Sequence;Body->ServerBodySnapshot_Implementation(Reload,Sequence-1);
    Check(Body->ReceivedPresentationSequence==Accepted&&Body->ReplicatedState.OffhandReloadPhase==Later.OffhandReloadPhase,
        TEXT("older reload snapshot cannot rewind return"));
    auto Wrong=Returning;Wrong.OffhandInstance=TEXT("previous-book");Received=Send(Wrong);
    Check(Received.OffhandReloadPhase==0,TEXT("changed offhand rejects old return"));
    Send(Returning);Body->LastPresentationReceivedAt=Body->ServerClock()-1.f;
    Check(Body->SampleRemoteAuthorityState().OffhandReloadPhase==0,TEXT("expired presentation cannot leave offhand hidden"));
    auto Extrapolated=Returning;Extrapolated.PresentationSampledAt=0.f;
    UFPSPlayerBodyComponent::AdvanceBodyPresentation(Extrapolated,1.f);
    Check(FMath::IsNearlyEqual(Extrapolated.OffhandReloadProgress,.22f),TEXT("offhand extrapolation is capped at 120 ms"));
    TArray<uint8> Bytes;auto Serialized=Returning;
    {FMemoryWriter Memory(Bytes);FObjectAndNameAsStringProxyArchive Archive(Memory,false);FFPSBodyState::StaticStruct()->SerializeItem(Archive,&Serialized,nullptr);}
    FFPSBodyState Roundtrip;
    {FMemoryReader Memory(Bytes);FObjectAndNameAsStringProxyArchive Archive(Memory,false);FFPSBodyState::StaticStruct()->SerializeItem(Archive,&Roundtrip,nullptr);}
    Check(Roundtrip.OffhandInstance==Returning.OffhandInstance&&Roundtrip.bOffhandReloadReturnFromReload&&
        Roundtrip.OffhandReloadPhase==Returning.OffhandReloadPhase&&Roundtrip.OffhandReloadProgressRate==1.f,
        TEXT("reflected serialization retains offhand handoff fields"));
    auto Dual=Configure({Pistol,Second});
    Check(Dual.bDual&&Dual.bOffhandPistol&&FMath::IsNearlyEqual(Pawn->GetReloadSeconds(true),NativeReload),
        TEXT("dual pistols do not pay non-pistol offhand cost"));
    auto Consume=Dual;Consume.Action=EFPSBodyAction::Consume;Consume.ConsumeHands=3;Consume.bConsumeWeaponsHidden=true;
    Received=Send(Consume);
    Check(Received.ConsumeHands==3&&Received.bConsumeWeaponsHidden&&
        FPSBodyPistolMotion::HandChannel(Received,0)==TEXT("Consume")&&FPSBodyPistolMotion::HandChannel(Received,1)==TEXT("Consume"),
        TEXT("dual two-hand consume owns both hands on relay"));
    Consume.ConsumeHands=2;Received=Send(Consume);
    Check(FPSBodyPistolMotion::HandChannel(Received,0)==TEXT("PistolCarry")&&FPSBodyPistolMotion::HandChannel(Received,1)==TEXT("Consume"),
        TEXT("one-hand drink leaves the other pistol independent"));
    Received=Send(Dual);Check(Received.ConsumeHands==0&&!Received.bConsumeWeaponsHidden,TEXT("consume end clears stow flags"));
    auto HammerState=Configure({Hammer});
    Check(HammerState.Family==TEXT("Tool")&&HammerState.Weapon==TEXT("warhammer"),TEXT("remote hammer retains dedicated identity"));
    auto Attack=HammerState;Attack.Action=EFPSBodyAction::Strike;Attack.ActionVariant=TEXT("WarhammerSlash3");
    Attack.bHasActionProgress=true;Attack.ActionProgress=.6f;Attack.ActionProgressRate=.5f;
    Received=Send(Attack);
    Check(FPSBodyWarhammerMotion::Clip(Received)==TEXT("Warhammer.FullBody.Slash3")&&Received.ActionProgress==.6f,
        TEXT("remote hammer selects restored third cut with source progress"));
    auto OldHammer=Attack;OldHammer.WeaponInstance=TEXT("old-hammer");Received=Send(OldHammer);
    Check(Received.Action==EFPSBodyAction::None,TEXT("different hammer instance cannot inherit attack"));
    int32 Loaded=0;for(const auto& Pair:Body->BodyAnimation->Clips)if(Pair.Key.ToString().StartsWith(TEXT("Warhammer."))&&Pair.Value)++Loaded;
    Check(Loaded==39,TEXT("fresh body initialization loads all 39 restored roles"));
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("cases"),Rows);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetBoolField(TEXT("socket_transport_tested"),false);Report->SetBoolField(TEXT("rendered_multiplayer_tested"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("AnimationHandoffReview20261021/authority.json");FParse::Value(*Params,TEXT("Out="),Out);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Out),true);FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*Out);Model->CurrentPawn.Reset();
    for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())
    {It->RouteEndPlay(EEndPlayReason::Quit);TInlineComponentArray<UActorComponent*> Components;It->GetComponents(Components);for(auto* C:Components)if(C->HasBegunPlay())C->EndPlay(EEndPlayReason::Quit);}
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
