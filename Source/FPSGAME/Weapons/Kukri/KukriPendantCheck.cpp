#include "KukriRelentlessComponent.h"
#include "KukriDecisiveComponent.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/StatusEffectsComponent.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "../../Monsters/WolfMonster.h"
#include "../../Monsters/MonsterCombatComponent.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"

#if !UE_BUILD_SHIPPING
namespace
{
// Explicit, isolated developer check. Never runs on startup or uses the player's live profile.
void CheckKukriPendants()
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_KukriPendant_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("KukriPendantCheck -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("KukriPendantCheck"));
    FCommandLine::Set(*Original);
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    ON_SCOPE_EXIT {GI->Shutdown();if(World){GEngine->DestroyWorldContext(World);World->DestroyWorld(false);}GI->RemoveFromRoot();};
    if(!World||!Model||!Model->IsAudit()){UE_LOG(LogTemp,Error,TEXT("Kukri pendant check requires isolated audit profile"));return;}
    World->TimeSeconds=10.f;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    auto Main=Model->CreateItem(TEXT("ue_kukri"));Main.Place=1;Main.Cell=6;
    TSharedPtr<FJsonObject> ItemData;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Main.Data),ItemData);
    if(!ItemData)ItemData=MakeShared<FJsonObject>();
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("lanyard"),TEXT("kukri_lanyard_relentless"));
    ItemData->SetObjectField(TEXT("gunsmith_parts"),Parts);Main.Data.Reset();
    FJsonSerializer::Serialize(ItemData,TJsonWriterFactory<>::Create(&Main.Data));Seed.Items={Main};
    Model->AdoptNetMirror(Seed);
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator,Spawn);
    auto* PC=World->SpawnActor<APlayerController>();PC->SetPlayer(NewObject<ULocalPlayer>(GEngine));PC->Possess(Pawn);
    Model->AttachPawn(Pawn);
    auto* Pendant=Pawn->FindComponentByClass<UKukriRelentlessComponent>();Pendant->Configure(Model);
    auto* Target=World->SpawnActor<AWolfMonster>(FVector(300,0,500),FRotator::ZeroRotator,Spawn);
    Target->MaxHealth=Target->Health=100000.f;Target->PhysicalDefense=Target->MagicDefense=0.f;
    auto* Combat=Target->Combat.Get();Combat->ToughnessThreshold=100000.f;Combat->BladeResistance=0.f;Combat->bAllowSubthresholdStagger=false;
    auto* Status=UStatusEffectsComponent::GetOrCreate(Pawn);
    TArray<TSharedPtr<FJsonValue>> Checks,Hits;int32 Failures=0;
    const auto Check=[&](bool OK,const FString& Name)
    {auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("case"),Name);O->SetBoolField(TEXT("passed"),OK);Checks.Add(MakeShared<FJsonValueObject>(O));Failures+=!OK;};
    const auto Snapshot=[&]()
    {
        auto Shot=ColdSteelSkills::Snapshot(Pawn,Model->Equipped());Shot.CriticalChance=0.f;Shot.CriticalRoll=1.f;
        Shot.WeakpointPercent=0.f;Shot.DamagePanel={100,0,0,0};return Shot;
    };
    const auto Contact=[&](const FColdSteelSkillShot& Shot,FWeaponDamageResult& Receipt)
    {
        FHitResult Hit(Target,Target->GetCapsuleComponent(),Target->GetActorLocation(),-FVector::ForwardVector);
        return ColdSteelSkills::ApplyHit(Pawn,Hit,100.f,FVector::ForwardVector,Shot,&Receipt);
    };
    Check(UKukriRelentlessComponent::Installed(*Model->Equipped(),Model),TEXT("real installed option recognized"));
    Check(Pawn->IsLocallyControlled(),TEXT("isolated controller resolves its own authority profile"));
    float FirstDamage=0.f,FirstToughness=0.f;
    for(int32 I=0;I<=10;++I)
    {
        const auto Shot=Snapshot();const auto Mult=UKukriDecisiveComponent::Multipliers(Shot,Model);
        Check(Shot.bMelee&&Shot.MasteryAttackSerial!=0,TEXT("fixture preserves weapon classification and action identity"));
        Check(FMath::IsNearlyEqual(Mult.X,1.+.03*I,.0001),FString::Printf(TEXT("attack %d frozen multiplier"),I+1));
        FWeaponDamageResult Receipt;const float Applied=Contact(Shot,Receipt);
        if(I==0){FirstDamage=Applied;FirstToughness=Combat->LastToughnessDamage;}
        auto O=MakeShared<FJsonObject>();O->SetNumberField(TEXT("attack"),I+1);O->SetNumberField(TEXT("stacks_at_start"),I);
        O->SetNumberField(TEXT("before_defense"),Receipt.BeforeDefense.Total());O->SetNumberField(TEXT("applied"),Applied);
        O->SetNumberField(TEXT("toughness"),Combat->LastToughnessDamage);Hits.Add(MakeShared<FJsonValueObject>(O));
        Check(FMath::IsNearlyEqual(Receipt.BeforeDefense.Total(),100.+3.*I,.001),FString::Printf(TEXT("attack %d damage reaches actual transaction"),I+1));
        int32 Count=0;float Remaining=0.f,Duration=0.f;
        Check(Pendant->GetBuff(false,Count,Remaining,Duration)&&Count==FMath::Min(I+1,10),FString::Printf(TEXT("attack %d grants one visible stack"),I+1));
        // Repeating a target/contact in the same swing must not grant another stack.
        Pendant->ConfirmHit(Shot,10.f);int32 After=0;Pendant->GetBuff(false,After,Remaining,Duration);Check(After==Count,TEXT("same swing deduplicated"));
        if(I==10)
        {
            Check(FirstDamage>0.f&&FMath::IsNearlyEqual(Applied/FirstDamage,1.3f,.015f),TEXT("actual health loss grows by thirty percent"));
            Check(FirstToughness>0.f&&FMath::IsNearlyEqual(Combat->LastToughnessDamage/FirstToughness,1.6f,.015f),TEXT("actual toughness grows by sixty percent without double scaling"));
        }
    }
    auto Views=Status->Snapshot();const auto* Buff=Views.FindByPredicate([](const auto& V){return V.Type==TEXT("kukriRelentlessMain");});
    Check(Buff&&Buff->Stacks==10&&Buff->Description.Contains(TEXT("30%"))&&Buff->Description.Contains(TEXT("60%")),TEXT("HUD adapter shares damage state and actual bonuses"));
    for(uint8 Meta:{uint8(0),uint8(0x10),uint8(0x14),uint8(0x16),uint8(0x20),uint8(0x80)})
    {
        auto Shot=Snapshot();Shot.AttackMeta=Meta;FWeaponDamageResult Receipt;Contact(Shot,Receipt);
        Check(FMath::IsNearlyEqual(Receipt.BeforeDefense.Total(),130.,.001),FString::Printf(TEXT("attack family %02x applies full-stack damage"),Meta));
    }
    auto Secondary=Snapshot();Secondary.bRicochet=true;
    Check(UKukriDecisiveComponent::Multipliers(Secondary,Model).Equals(FVector2D(1,1),.0001),TEXT("secondary damage excluded"));
    for(int32 Family=0;Family<5;++Family)
    {
        Pendant->PrepareServerAttack(Family);auto Shot=Snapshot();Shot.MasteryAttackSerial=900000+Family;
        Pendant->BindServerAttack(Family,Shot.MasteryAttackSerial);
        Check(FMath::IsNearlyEqual(UKukriDecisiveComponent::Multipliers(Shot,Model).X,1.3,.0001),FString::Printf(TEXT("server family %d binds accepted snapshot"),Family));
    }
    World->TimeSeconds+=4.6f;int32 Count=0;float Remaining=0.f,Duration=0.f;
    Check(Pendant->GetBuff(false,Count,Remaining,Duration)&&Count==9&&Remaining<=.5f,TEXT("four-second grace then decay reaches HUD"));
    auto Off=Model->CreateItem(TEXT("ue_kukri"));Off.Place=1;Off.Cell=8;Off.Data=Main.Data;
    Seed.Items={Main,Off};Model->AdoptNetMirror(Seed);Pendant->Configure(Model);
    for(int32 I=0;I<5;++I){const auto Shot=Snapshot();FWeaponDamageResult Receipt;Contact(Shot,Receipt);}
    auto Left=ColdSteelSkills::Snapshot(Pawn,Model->Equipped(8));Left.CriticalChance=0.f;Left.CriticalRoll=1.f;Left.DamagePanel={100,0,0,0};
    FWeaponDamageResult LeftReceipt;Contact(Left,LeftReceipt);
    Check(Pendant->GetBuff(false,Count,Remaining,Duration)&&Count==5,TEXT("dual main retains own five stacks"));
    Check(Pendant->GetBuff(true,Count,Remaining,Duration)&&Count==1,TEXT("dual offhand gains its own stack"));
    auto Paired=Snapshot();Paired.AttackMeta=0x16;const auto PairBonus=UKukriDecisiveComponent::Multipliers(Paired,Model);
    Check(FMath::IsNearlyEqual(PairBonus.X,1.09,.0001)&&FMath::IsNearlyEqual(PairBonus.Y,1.18,.0001),TEXT("paired dash weights independent blade bonuses"));
    Views=Status->Snapshot();Check(Views.ContainsByPredicate([](const auto& V){return V.Type==TEXT("kukriRelentlessMain")&&V.Stacks==5;})&&Views.ContainsByPredicate([](const auto& V){return V.Type==TEXT("kukriRelentlessOffhand")&&V.Stacks==1;}),TEXT("both blade buffs reach HUD independently"));
    auto Away=Seed;Away.ActiveWeaponSlot=9;Model->AdoptNetMirror(Away);Pendant->Configure(Model);
    Check(!Pendant->GetBuff(false,Count,Remaining,Duration),TEXT("switch clears buff"));
    auto Result=MakeShared<FJsonObject>();Result->SetArrayField(TEXT("checks"),Checks);Result->SetArrayField(TEXT("hits"),Hits);
    Result->SetNumberField(TEXT("failures"),Failures);Result->SetBoolField(TEXT("isolated_no_player_save"),true);
    Result->SetBoolField(TEXT("gameplay_input_or_network_tested"),false);
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    const FString Out=FPaths::ProjectSavedDir()/TEXT("KukriPendantFix20261030/damage-check.json");
    FFileHelper::SaveStringToFile(Json,*Out);UE_LOG(LogTemp,Display,TEXT("KUKRI_PENDANT_CHECK failures=%d output=%s"),Failures,*Out);
}
FAutoConsoleCommand PendantCheck(TEXT("ColdSteel.CheckKukriPendants"),TEXT("Explicit isolated pendant damage and HUD check; does not use player saves."),FConsoleCommandDelegate::CreateStatic(CheckKukriPendants));
}
#endif
