#include "RuneboundReviewFixture.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerModificationAuditCommandlet.h"
#include "../Production/FinalTollHeavyMotion.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "Animation/AnimSequence.h"
#include "Materials/Material.h"
#include "Net/UnrealNetwork.h"

ARuneboundReviewTarget::ARuneboundReviewTarget()
{
    AutoPossessAI=EAutoPossessAI::Disabled;PrimaryActorTick.bStartWithTickEnabled=false;
    Health=MaxHealth=10000000;SetReplicates(true);bAlwaysRelevant=true;
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetCapsuleComponent()->SetCollisionObjectType(ECC_Pawn);
    GetCapsuleComponent()->SetCollisionResponseToAllChannels(ECR_Block);
}
void ARuneboundReviewTarget::BeginPlay()
{
    ACharacter::BeginPlay();SetActorTickEnabled(false);
    GetCharacterMovement()->DisableMovement();GetCharacterMovement()->SetComponentTickEnabled(false);
}
float ARuneboundReviewTarget::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Source)
{
    if(Event.DamageTypeClass&&Event.DamageTypeClass->IsChildOf(UStatusMagicDamage::StaticClass()))Magic.Add(Damage);
    else Physical.Add(Damage);
    return Damage;
}

int32 URuneboundReviewAuditCommandlet::Main(const FString& Params)
{
    FString Output;if(!FParse::Value(*Params,TEXT("Report="),Output))return 2;
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Rune_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("RuneboundReviewAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("RuneboundReviewWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 3;
    World->InitializeActorsForPlay(FURL());
    bool Passed=true;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name){RuneboundReview::Check(Rows,Passed,OK,Name);};
    const auto Pump=[&](float Delta){++GFrameCounter;World->GetTimerManager().Tick(Delta);};
    Pump(.001f);
    const FString Instance=TEXT("RuneboundReviewGuest");
    auto Seed=RuneboundReview::Seed(Host,Instance,RuneboundHammer::FinalTollHead);
    auto* Shadow=Host->CreateShadowModel(Seed);auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->AttachPawn(Pawn);RuneboundReview::Freeze(Pawn);
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;
    auto* Target=World->SpawnActor<ARuneboundReviewTarget>(FVector(150,0,500),FRotator::ZeroRotator);
    auto* Other=World->SpawnActor<ARuneboundReviewTarget>(FVector(150,90,500),FRotator::ZeroRotator);
    uint32 Serial=1000;
    const auto Reset=[&](const FString& Head,const FString& Rune=TEXT(""))
    {
        Tool->CancelUse();Seed=RuneboundReview::Seed(Host,Instance,Head,Rune);Shadow->AdoptNetMirror(Seed);
        Tool->Kind=TEXT("warhammer");Tool->EquippedId=Instance;Tool->ApplyToolStats(Shadow->ActiveProductionTool(),Shadow);
        Tool->BluntServerReadyAt=0.;Tool->RuneboundInstance.Reset();Tool->TickRunebound(0);
        Target->State=Other->State=ENurseState::Idle;Target->ResetDamage();Other->ResetDamage();
    };
    const auto Shot=[&]()
    {
        auto S=ColdSteelSkills::Snapshot(Pawn,Shadow->ActiveProductionTool());S.MasteryAttackSerial=++Serial;S.bMelee=true;S.AttackForm=EMonsterAttackForm::Blunt;return S;
    };
    const auto Awake=[&](){Tool->RuneboundActiveUntil=Tool->RuneboundClock()+20.;};
    const auto HeavyHit=[&](ARuneboundReviewTarget* Victim)
    {
        auto S=Shot();Tool->FinalTollHeavySerial=S.MasteryAttackSerial;Tool->FinalTollCommitUntil=Tool->RuneboundClock()+2.;
        Tool->RecordRuneboundHit(S,RuneboundReview::Hit(Victim));return S;
    };
    Reset(RuneboundHammer::FinalTollHead);
    Check(ColdSteelAuthority::ForPawn(Pawn)==Shadow&&Shadow!=Host,TEXT("remote authority uses guest profile"));
    const float HostStamina=Host->Stamina();
    for(int32 I=0;I<9;++I){auto S=Shot();Tool->RecordRuneboundHit(S,RuneboundReview::Hit(Target));Tool->RecordRuneboundHit(S,RuneboundReview::Hit(Other));}
    Check(Tool->RuneboundCharge==9&&!Tool->IsRuneboundAwakened(*Shadow->ActiveProductionTool()),TEXT("native charge counts one per attack across targets"));
    HeavyHit(Target);Check(Tool->RuneboundCharge==10&&Tool->IsRuneboundAwakened(*Shadow->ActiveProductionTool()),TEXT("native awakening on tenth hit"));
    Reset(RuneboundHammer::FinalTollHead,TEXT("swift_mana_rune"));
    for(int32 I=0;I<5;++I){auto S=Shot();Tool->RecordRuneboundHit(S,RuneboundReview::Hit(Target));}
    Check(Tool->RuneboundCharge==5&&Tool->IsRuneboundAwakened(*Shadow->ActiveProductionTool()),TEXT("swift awakening on fifth hit"));
    const auto SwiftStats=Tool->ToolStats;
    Reset(RuneboundHammer::FinalTollHead);const auto BaseStats=Tool->ToolStats;
    Check(SwiftStats.SwingSeconds<BaseStats.SwingSeconds,TEXT("swift ordinary attack speed applied"));
    for(const FString Rune:{FString(),FString(TEXT("destruction_mana_rune"))})
    {
        Reset(RuneboundHammer::FinalTollHead,Rune);Awake();const float Expected=Shadow->Derived(TEXT("matk"))*(Rune.IsEmpty()?3.5:7.);
        const auto First=HeavyHit(Target);Tool->RecordRuneboundHit(First,RuneboundReview::Hit(Target));
        Check(Tool->FinalTollMarks.Num()==1&&Tool->FinalTollSealState.Marks.Num()==1,TEXT("persistent seal published once ")+Rune);
        auto Next=Shot();Tool->FinalTollHeavySerial=Next.MasteryAttackSerial;
        Check(Tool->FinalTollToughnessMultiplier(Next,Target)==2.f&&Tool->FinalTollToughnessMultiplier(Next,Other)==1.f,TEXT("completion doubles toughness on marked target only ")+Rune);
        auto Wrong=Next;Wrong.ItemInstance=TEXT("stale-instance");
        Check(Tool->FinalTollToughnessMultiplier(Wrong,Target)==1.f,TEXT("stale instance has no toughness bonus"));
        Tool->RecordRuneboundHit(Next,RuneboundReview::Hit(Target));
        Tool->RecordRuneboundHit(Next,RuneboundReview::Hit(Target));Tool->RecordRuneboundHit(First,RuneboundReview::Hit(Target));
        Pump(.01f);
        Check(Tool->FinalTollMarks.IsEmpty()&&Target->Magic.Num()==1&&FMath::IsNearlyEqual(Target->Magic[0],Expected,.01f)&&Other->Magic.IsEmpty(),TEXT("completion magic once, exact scale, single target, replay safe ")+Rune);
        HeavyHit(Target);Tool->FinalTollMarks[0].Expires=-1.;Tool->TickRunebound(0);
        Check(Tool->FinalTollMarks.IsEmpty()&&Tool->FinalTollSealState.Marks.IsEmpty(),TEXT("expiry removes replicated seal"));
        HeavyHit(Target);Target->State=ENurseState::Dead;Tool->TickRunebound(0);
        Check(Tool->FinalTollSealState.Marks.IsEmpty(),TEXT("death removes replicated seal"));Target->State=ENurseState::Idle;
    }
    Reset(RuneboundHammer::FinalTollHead);Awake();HeavyHit(Target);
    Tool->FinalTollVisualMarks.Reset();Tool->OnRep_FinalTollSeals();Tool->ReconcileFinalTollSeals(false);Tool->ReconcileFinalTollSeals(true);
    Check(Tool->FinalTollVisualMarks.Num()==1,TEXT("seal reconstructs after awake property arrives later"));
    Shadow->AdoptNetMirror(RuneboundReview::Seed(Host,Instance,TEXT("")));Tool->TickRunebound(0);
    Check(Tool->FinalTollSealState.Marks.IsEmpty(),TEXT("same-instance head removal clears replicated seals"));
    for(int32 Mode=0;Mode<3;++Mode)
    {
        Reset(RuneboundHammer::FinalTollHead);Awake();const uint32 Id=++Serial;
        Tool->ServerBeginBluntCharge(Id);Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-Tool->BluntChargeSeconds-.1f;
        Tool->ServerBeginBluntAttack(Id,true,false);
        const float Paid=100.f-Shadow->Stamina();
        Tool->ServerBeginBluntAttack(Id,true,false);
        Check(FMath::IsNearlyEqual(Paid,float(Tool->ToolStats.HeavyReleaseStaminaCost),.01f)&&FMath::IsNearlyEqual(100.f-Shadow->Stamina(),Paid,.01f),TEXT("double heavy pays release once despite replay"));
        if(Mode==1)Shadow->AdoptNetMirror(RuneboundReview::Seed(Host,Instance,TEXT("")));
        if(Mode==2)Tool->ServerCancelBluntAttack(Id);
        Pump(.13f);
        if(Mode==0)Check(Target->Physical.Num()==1,TEXT("first committed heavy contact"));
        Pump(.4f);Pump(.01f);
        Check(Mode==0?Target->Physical.Num()==2&&Target->Magic.Num()==1:Target->Physical.IsEmpty()&&Target->Magic.IsEmpty(),
            Mode==0?TEXT("two authority contacts and one independent finisher"):Mode==1?TEXT("same-instance head swap aborts both committed contacts"):TEXT("cancel aborts both timers"));
    }
    Check(Host->Stamina()==HostStamina,TEXT("guest transactions leave host stamina unchanged"));
    const auto BaseSeed=RuneboundReview::Seed(Host,Instance,TEXT(""));Shadow->AdoptNetMirror(BaseSeed);
    const double BaseMatk=Shadow->Derived(TEXT("matk")),BaseAtk=Shadow->Derived(TEXT("atk"));
    for(const FString Rune:{FString(),FString(TEXT("destruction_mana_rune"))})
    {
        Reset(RuneboundHammer::StarOathHead,Rune);Awake();
        const float Expected=Shadow->Derived(TEXT("matk"))*(Rune.IsEmpty()?2.:4.);
        if(Rune.IsEmpty())Check(FMath::IsNearlyEqual(Shadow->Derived(TEXT("matk")),BaseMatk*1.1,.01)&&FMath::IsNearlyEqual(Shadow->Derived(TEXT("atk")),BaseAtk*1.1,.01),TEXT("star oath adds ten percent active physical and magic attack"));
        auto* Far=World->SpawnActor<ARuneboundReviewTarget>(FVector(650,0,500),FRotator::ZeroRotator);
        for(int32 I=0;I<2;++I){auto S=Shot();Tool->RecordRuneboundHit(S,RuneboundReview::Hit(Target));Tool->RecordRuneboundHit(S,RuneboundReview::Hit(Other));}
        Pump(.01f);Check(Target->Magic.IsEmpty(),TEXT("star oath no explosion before third distinct attack ")+Rune);
        auto Third=Shot();Tool->RecordRuneboundHit(Third,RuneboundReview::Hit(Target));Tool->RecordRuneboundHit(Third,RuneboundReview::Hit(Other));Pump(.01f);
        Check(Target->Magic.Num()==1&&Other->Magic.Num()==1&&Far->Magic.IsEmpty()&&FMath::IsNearlyEqual(Target->Magic[0],Expected,.01f),TEXT("star oath third hit exact magic scale, nearby only, once per actor ")+Rune);
        Far->Destroy();
    }
    UProductionToolComponent::StaticClass()->SetUpRuntimeReplicationData();TArray<FLifetimeProperty> Props;Tool->GetLifetimeReplicatedProps(Props);
    auto* SealProperty=FindFProperty<FProperty>(UProductionToolComponent::StaticClass(),TEXT("FinalTollSealState"));
    Check(SealProperty&&SealProperty->HasAllPropertyFlags(CPF_Net|CPF_RepNotify)&&Props.ContainsByPredicate([&](const FLifetimeProperty& P){return P.RepIndex==SealProperty->RepIndex;}),TEXT("seal snapshot registered for network replication"));
    auto* Clip=LoadObject<UAnimSequence>(nullptr,FinalTollHeavy::Asset);
    Check(Clip&&FMath::IsNearlyEqual(Clip->GetPlayLength(),1.25f,.005f),TEXT("saved first-person double heavy duration"));
    for(const FString Body:{FString(TEXT("Default")),FString(TEXT("kaitlin"))})
    {
        const FString Path=FString(TEXT("/Game/Weapons/RuneboundWarhammer20261022/FinalTollV1/A_Runebound_FinalToll_Body_"))+Body+TEXT(".A_Runebound_FinalToll_Body_")+Body;
        auto* BodyClip=LoadObject<UAnimSequence>(nullptr,*Path);
        Check(BodyClip&&FMath::IsNearlyEqual(BodyClip->GetPlayLength(),1.25f,.005f),TEXT("saved fullbody double heavy duration ")+Body);
    }
    Check(LoadObject<UMaterial>(nullptr,RuneboundHammer::Hud)!=nullptr,TEXT("current symmetric HUD material saved and loadable"));
    Tool->CancelUse();RuneboundReview::Save(Rows,Passed,TEXT("isolated authority, no sockets"),Output);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Passed?0:1;
}
