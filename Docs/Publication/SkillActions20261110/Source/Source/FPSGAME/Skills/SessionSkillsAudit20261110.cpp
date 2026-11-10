#include "SkillNetworkAuditCommandlet.h"
#include "ChainSlashMotion.h"
#include "ChainSlashAssets.h"
#include "PlayerSkillPreparation.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSBodySwordMotion.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"

int32 USkillNetworkAuditCommandlet::RunSessionSkillsAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("SessionSkillsAudit"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failures=0;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("SESSION_SKILLS %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    Seed.Stamina=150;Seed.bSprintExhausted=false;Seed.ChainSlashCooldown=Seed.ChainSlashCooldownDuration=0;
    Seed.NetworkProfileId=FGuid::NewGuid();
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto Item=Host->CreateItem(TEXT("ue_rune_sword"));Item.Place=1;Item.Cell=6;Seed.Items.Add(Item);
    auto* Shadow=Host->CreateShadowModel(Seed);auto* PC=World->SpawnActor<ASkillAuditRemoteController>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;
    Pawn->FindComponentByClass<UFPSCombatHealthComponent>()->Health=150;
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    Body->Character=Pawn;Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();Sword->InstanceId=Item.InstanceId;
    Sword->Viewmodel=NewObject<USkeletalMeshComponent>(Pawn);Pawn->AddInstanceComponent(Sword->Viewmodel);
    Sword->Viewmodel->SetupAttachment(Sword->Camera.Get());Sword->Viewmodel->RegisterComponent();
    Sword->Viewmodel->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny")));
    Sword->Animations.Add(TEXT("Idle"),LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle")));
    TArray<TStrongObjectPtr<UObject>> Assets;
    for(const TCHAR* Id:{TEXT("chainSlash"),TEXT("leapStrike"),TEXT("flameArmor"),TEXT("elementalArrow"),TEXT("magicArrowRain")})
    {
        Check(Host->SkillCatalog().Contains(Id),FString(TEXT("catalog "))+Id);
        TArray<FSoftObjectPath> Paths;PlayerSkillAssets::Gather(Id,Seed,Paths);
        Check(!Paths.IsEmpty(),FString(TEXT("prepared asset list "))+Id);
        for(const auto& Path:Paths)
        {auto* A=Path.TryLoad();Check(A!=nullptr,FString(TEXT("saved asset "))+Path.ToString());if(A)Assets.Emplace(A);}
    }
    const FSoftObjectPath OriginalChargeFire(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103/NS_StarMarrowDenseBladeFire.NS_StarMarrowDenseBladeFire"));
    auto* ChargeFire=OriginalChargeFire.TryLoad();Check(ChargeFire!=nullptr,TEXT("original StarMarrow blue charge fire saved asset resolves"));
    if(ChargeFire)Assets.Emplace(ChargeFire);
    const auto Low=ChainSlash::Evaluate(FChainSlashTuning(),1),High=ChainSlash::Evaluate(FChainSlashTuning(),20);
    Check(Low.DamageMultiplier==.4f&&Low.StaminaCost==40&&Low.CooldownSeconds==25,TEXT("chain level 1: 40 percent / 40 stamina / 25 s"));
    Check(High.DamageMultiplier==1.2f&&High.StaminaCost==60&&High.CooldownSeconds==15,TEXT("chain level 20: 120 percent / 60 stamina / 15 s"));
    const float HostStamina=Host->Stamina(),Cost=Shadow->ChainSlashStats().StaminaCost;
    const bool Started=Sword->StartChainSlash();
    Check(Started,TEXT("remote authority starts equipped chain slash"));
    Check(Started&&FMath::IsNearlyEqual(Shadow->Stamina(),150-Cost)&&Host->Stamina()==HostStamina,TEXT("guest pays before action without charging host"));
    const float Paid=Shadow->Stamina();
    Check(!Sword->StartChainSlash()&&Shadow->Stamina()==Paid,TEXT("busy duplicate start cannot pay twice"));
    if(Started)
    {
        Sword->ServerSetSwordGuard_Implementation(Item.InstanceId,true,77);
        Check(!Sword->IsGuarding()&&Sword->IsChainSlashActive(),TEXT("server rejects guard during active chain slash"));
        for(int32 I=0;I<4;++I)
        {
            Sword->Elapsed=Sword->ChainSlashContacts[I];Sword->SweepHitPause=0.f;
            const auto State=Body->SampleLocalState();
            Check(State.ActionVariant==ChainSlashMotion::Variant(I)&&State.Action!=EFPSBodyAction::None&&
                FMath::IsNearlyEqual(State.ActionProgress,State.ContactFraction,.001f)&&!FPSBodySwordMotion::Clip(State).IsNone(),
                FString::Printf(TEXT("cut %d publishes matching world-body contact and clip"),I+1));
            Sword->SweepHitPause=.05f;
            Check(Body->SampleLocalState().ActionProgressRate==0.f,FString::Printf(TEXT("cut %d world-body clock pauses at hitstop"),I+1));
        }
        Sword->SweepHitPause=0;Sword->CancelAction();
        const auto XP=Shadow->MasteryProgress(TEXT("chainSlash")).Experience;
        Sword->FinishChainSlashTraining();
        Check(XP>0&&Shadow->MasteryProgress(TEXT("chainSlash")).Experience==XP,TEXT("cancel settles release training once"));
    }
    bool Clock=true;
    for(float T=0;T<5.f;T+=.003f)Clock&=FMath::IsNearlyEqual(T,ChainSlashMotion::PlaybackTime(ChainSlashMotion::SourceTime(T)),.00001f);
    Check(Clock,TEXT("accelerated opening clock preserves authored times"));
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("passed"),Failures==0);Root->SetNumberField(TEXT("failures"),Failures);Root->SetArrayField(TEXT("cases"),Rows);
    Root->SetStringField(TEXT("scope"),TEXT("saved assets, isolated remote-authority methods and body sampling; not UDP or rendered acceptance"));
    FString Json,Out;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    if(!FParse::Value(*Params,TEXT("Output="),Out))Out=FPaths::ProjectSavedDir()/TEXT("SessionSkillsAudit20261110/native.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Out),true);const bool Saved=FFileHelper::SaveStringToFile(Json,*Out);
    Shadow->CurrentPawn.Reset();Pawn->NetShadowProfile=nullptr;PS->ShadowModel=nullptr;
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures||!Saved?1:0;
}
