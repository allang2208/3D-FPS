#include "SkillNetworkAuditCommandlet.h"
#include "FPSIceArmorComponent.h"
#include "EnemyAttackDamage.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

int32 USkillNetworkAuditCommandlet::RunIceArmorAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Ice_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("IceArmorAuthorityAudit"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const TCHAR* Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("ICE_ARMOR_AUDIT %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveProductionTool.Reset();Seed.ActiveWeaponSlot=6;Seed.DungeonRun={};
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:Seed.QuickBindings)Binding={};
    Seed.IceArmorCooldown=Seed.IceArmorCooldownDuration=0;Seed.Skills.FindOrAdd(TEXT("iceArmor"))={};Seed.NetworkProfileId=FGuid::NewGuid();
    auto* Shadow=Host->CreateShadowModel(Seed);
    Shadow->Current.Mana=Shadow->Derived(TEXT("maxMp"));
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;
    auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=Health->MaxHealth;
    auto* Ice=Pawn->FindComponentByClass<UFPSIceArmorComponent>();
    Check(Ice&&Pawn->HasAuthority()&&!Pawn->IsLocallyControlled(),TEXT("remote authority fixture"));
    const auto Stats=Shadow->IceArmorStats();const float Mana=Shadow->Snapshot().Mana,HostMana=Host->Snapshot().Mana;
    const float Defense=Shadow->Derived(TEXT("def")),MagicDefense=Shadow->Derived(TEXT("mdef"));
    FColdSteelNetCastRequest Request;Request.SkillId=TEXT("iceArmor");Request.SourcePawn=Pawn;Request.Sequence=Request.CastId=101;
    PS->ExecuteCastRequest(Request);
    Check(PS->PendingIdentifiedCastId==101&&FMath::IsNearlyEqual(Shadow->Snapshot().Mana,Mana-Stats.ManaCost),TEXT("prepare without staff pays guest mana"));
    Request.Phase=1;Request.Sequence=102;PS->ExecuteCastRequest(Request);
    const uint32 Serial=Ice->State.Serial;
    Check(Ice->State.bActive&&Ice->State.CastId==101&&!PS->PendingIdentifiedCastId,TEXT("release activates matching cast once"));
    Check(FMath::IsNearlyEqual(Shadow->Derived(TEXT("def"))-Defense,Stats.PhysicalDefense)&&FMath::IsNearlyEqual(Shadow->Derived(TEXT("mdef"))-MagicDefense,Stats.MagicDefense),TEXT("defense belongs to guest runtime pawn"));
    PS->ExecuteCastRequest(Request);
    Check(Ice->State.Serial==Serial&&FMath::IsNearlyEqual(Shadow->Snapshot().Mana,Mana-Stats.ManaCost),TEXT("duplicate release cannot restart or charge twice"));
    Check(Host->Snapshot().Mana==HostMana,TEXT("guest cast leaves host mana unchanged"));

    auto* Enemy=World->SpawnActor<ANurseZombie>(FVector(100,0,500),FRotator::ZeroRotator);Enemy->Health=Enemy->MaxHealth=10000;
    Ice->ObserveAcceptedDamage(Enemy,GetDefault<UEnemyMeleeDamage>(),5);
    const int32 FirstXP=Ice->Experience;
    Ice->ObserveAcceptedDamage(Enemy,GetDefault<UEnemyMeleeDamage>(),5);
    Check(FirstXP==Stats.CastExperience+Stats.MeleeExperience&&Ice->Experience==FirstXP,TEXT("same-source melee training is throttled"));
    Ice->TrainingSources.Reset();Ice->ObserveAcceptedDamage(Enemy,GetDefault<UEnemyRangedDamage>(),5);
    Check(Ice->Experience==FirstXP+Stats.RangedExperience,TEXT("accepted ranged hit trains ice armor"));
    const int32 Earned=Ice->Experience,HostXP=Host->MasteryProgress(TEXT("iceArmor")).Experience;
    Pawn->NetShadowProfile=nullptr;PS->ShadowModel=nullptr;Ice->FinishForRemoval();Ice->FinishForRemoval();
    Check(Shadow->MasteryProgress(TEXT("iceArmor")).Experience==Earned&&Host->MasteryProgress(TEXT("iceArmor")).Experience==HostXP,TEXT("removal settles original guest once after detachment"));
    Check(!Ice->State.bActive&&Ice->DefenseBonus(false)==0&&Ice->BodyShells.IsEmpty()&&!Ice->Lens,TEXT("removal clears defense and presentation"));
    Pawn->NetShadowProfile=Shadow;PS->ShadowModel=Shadow;

    Shadow->Current.IceArmorCooldown=Shadow->Current.IceArmorCooldownDuration=0;
    Request.Phase=0;Request.Sequence=Request.CastId=201;PS->ExecuteCastRequest(Request);
    Request.Phase=2;Request.CastId=101;Request.Sequence=202;PS->ExecuteCastRequest(Request);
    Check(PS->PendingIdentifiedCastId==201,TEXT("old cancel cannot cancel new reservation"));
    const float Paid=Shadow->Snapshot().Mana;Request.CastId=201;Request.Sequence=203;PS->ExecuteCastRequest(Request);
    const float Refunded=Shadow->Snapshot().Mana;PS->ExecuteCastRequest(Request);
    Check(!PS->PendingIdentifiedCastId&&FMath::IsNearlyEqual(Refunded,Paid+Stats.ManaCost)&&Shadow->Snapshot().Mana==Refunded,TEXT("matching cancel refunds once"));

    auto* Replica=World->SpawnActor<AFPSGAMECharacter>();Replica->SwapRoles();
    auto* Remote=Replica->FindComponentByClass<UFPSIceArmorComponent>();
    Remote->State.Cast=Stats;Remote->State.CastId=301;Remote->State.Serial=1;Remote->State.bActive=true;Remote->State.StartedAt=Remote->Clock()-Stats.Duration*.5;
    Remote->OnRep_State();
    Check(!Replica->HasAuthority()&&FMath::IsNearlyEqual(Remote->Remaining(),Stats.Duration*.5f)&&!Remote->Lens,TEXT("late remote state keeps remaining duration and no owner lens"));
    Remote->LocalCastId=302;Remote->Prediction=Remote->State;Remote->Prediction.CastId=302;Remote->Prediction.StartedAt=Remote->Clock();Remote->bAwaiting=true;
    Remote->OnRep_State();Check(Remote->bAwaiting&&Remote->View().CastId==302,TEXT("old state cannot erase newer prediction"));
    Remote->State=Remote->Prediction;Remote->OnRep_State();
    Check(!Remote->bAwaiting&&Remote->ConfirmedCastId==302,TEXT("matching state confirms prediction without replay"));
    Remote->State.bActive=false;Remote->OnRep_State();Check(Remote->Remaining()==0,TEXT("inactive state removes remaining effect"));

    FFPSBodyState Body;Body.Action=EFPSBodyAction::Cast;Body.ActionVariant=TEXT("Release");Body.Contacts.Channel=TEXT("Cast");
    Body.PresentationSampledAt=10;Body.ReleaseFraction=.48f;Body.CastPalmProgressRate=4;Body.bHasActionProgress=true;Body.ActionProgress=.1f;Body.ActionProgressRate=2;
    UFPSPlayerBodyComponent::AdvanceBodyPresentation(Body,10.04f);
    Check(FMath::IsNearlyEqual(Body.ReleaseFraction,.64f,.0001f)&&FMath::IsNearlyEqual(Body.ActionProgress,.18f,.0001f),TEXT("remote palm and action advance between packets"));
    Body.ReleaseFraction=.8f;Body.PresentationSampledAt=10;UFPSPlayerBodyComponent::AdvanceBodyPresentation(Body,20);
    Check(Body.ReleaseFraction==1.f,TEXT("long packet gap clamps extrapolation and palm range"));
    Body.Action=EFPSBodyAction::HeavyStrike;Body.ReleaseFraction=.7f;UFPSPlayerBodyComponent::AdvanceBodyPresentation(Body,20);
    Check(Body.ReleaseFraction==.7f,TEXT("melee timing threshold is never extrapolated"));
    Body.Action=EFPSBodyAction::Cast;Body.Contacts.Channel=TEXT("StaffCast");UFPSPlayerBodyComponent::AdvanceBodyPresentation(Body,20);
    Check(Body.ReleaseFraction==.7f,TEXT("staff timeline remains independently owned"));

    Enemy->Destroy();Replica->Destroy();
    auto Root=MakeShared<FJsonObject>();Root->SetStringField(TEXT("mode"),TEXT("offline authority and replica fixtures; no socket network or rendering"));
    Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);Root->SetArrayField(TEXT("results"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    FString Path;if(!FParse::Value(*Params,TEXT("AuditOutput="),Path))Path=FPaths::ProjectSavedDir()/TEXT("IceArmorNetworkReview20261018/authority-result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
