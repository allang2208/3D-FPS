#include "FPSCombatHealthComponent.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotMonster.h"
#include "PoisonMaggotProjectile.h"
#include "../Skills/CorrosivePusDamage.h"
#include "../Skills/LightningDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameModeBase.h"
#include "Camera/PlayerCameraManager.h"
#include "TimerManager.h"
#include "../Movement/FPSCharacterMovementComponent.h"

bool UFPSCombatHealthComponent::IsInvulnerable() const
{
    const auto* Character=Cast<ACharacter>(GetOwner());
    if (UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Character, EDevelopmentTuningOption::Invincible)) return true;
    const auto* Move=Character?Cast<UFPSCharacterMovementComponent>(Character->GetCharacterMovement()):nullptr;
    return Move && Move->IsDodging();
}

void UFPSCombatHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    Health = MaxHealth;
    GetOwner()->OnTakeAnyDamage.AddDynamic(this, &UFPSCombatHealthComponent::OnDamage);
}

float UFPSCombatHealthComponent::DamageAfterArmor(float Damage,const UDamageType* Type,AActor* Attacker) const
{
    if(Type&&Type->IsA<UCombatDirectDamage>())return Damage;
    const bool bMagic=CombatFormulaRuntime::IsMagic(Type);
    const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
    const auto* AttackerStatus=Attacker?Attacker->FindComponentByClass<UCombatStatusFormula>():nullptr;
    UColdSteelStatusModel* Model=nullptr;
    if(GetWorld()->GetNetMode()==NM_Standalone&&GetWorld()->GetGameInstance())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model&&!(Type&&Type->IsA<UMaggotPoisonDamage>())) // 旧口径：蛆毒直接结算，不过防御
        Damage=CoreCombatFormula::Defense(Damage,Model->Derived(bMagic?TEXT("mdef"):TEXT("def")),bMagic,0,Status?Status->MagicShred():0,Status?Status->CorrosionMultiplier():1);
    // 旧链顺序：魔法易伤→石化→感电→无人机易伤→献祭怪物攻击削弱→冻结→来源减伤→标记→圣佑→金刚石上限。
    if(bMagic&&Status)Damage=FMath::FloorToFloat(Damage*Status->MagicVulnerabilityMultiplier());
    if(bMagic&&Status)Damage=FMath::FloorToFloat(Damage*Status->PetrifiedMagicMultiplier());
    if(Type&&Type->IsA<ULightningDamage>()&&Status)Damage=FMath::FloorToFloat(Damage*Status->ElectricMultiplier());
    if(Status)Damage=FMath::FloorToFloat(Damage*Status->DroneDamageMultiplier(Attacker));
    if(Model)if(const auto* AttackerPawn=Cast<APawn>(Attacker);Attacker&&(!AttackerPawn||!AttackerPawn->IsPlayerControlled()))
        Damage=FMath::FloorToFloat(Damage*Model->TributeEffect(TEXT("monsterAtkDownPercent"))); // 旧口径：仅敌方来源攻击触发削弱
    if(!bMagic&&Status&&Status->FrozenRemaining()>0)Damage=FMath::FloorToFloat(Damage*1.5f);
    if(AttackerStatus)Damage=FMath::FloorToFloat(Damage*AttackerStatus->OutgoingDamageMultiplier());
    if(Status)Damage=FMath::FloorToFloat(Damage*Status->MarkedMultiplier());
    if(Status)Damage=FMath::FloorToFloat(Damage*Status->FinalMultiplier());
    if(Model)if(const double CapRatio=Model->TributeSpecial(TEXT("surviveCapPercent"));CapRatio>0)
        Damage=FMath::Min(Damage,FMath::Max(1.f,FMath::FloorToFloat(MaxHealth*float(CapRatio)/100.f))); // 金刚石：单次承伤封顶
    return Damage;
}

void UFPSCombatHealthComponent::OnDamage(AActor* Actor, float Damage, const UDamageType* Type, AController* Instigator, AActor* Causer)
{
    if (!Actor->HasAuthority() || IsDead() || Damage <= 0.f) return;
    auto* Model=GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    // 月影庇护：参战（首次受击）触发短暂无敌，窗口内全部承伤无效（旧 moonstone special）。
    if(Model)
    {
        if(Model->IsMoonshadowActive())return;
        const double A=Model->TryActivateMoonshadow();
        if(A>0&&Model->IsMoonshadowActive())
        {
            UE_LOG(LogTemp, Display, TEXT("MOONSHADOW_INVULN until=%.2f"), A);
            return;
        }
    }
    if(IsInvulnerable() && (!(Type&&Type->IsA<UCombatDirectDamage>())||UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Cast<APawn>(Actor),EDevelopmentTuningOption::Invincible)))return;
    AActor* Attacker=Causer?Causer:(Instigator?Instigator->GetPawn():nullptr);
    if(!Actor->IsA<AFPSGAMECharacter>())Damage=DamageAfterArmor(Damage,Type,Attacker);
    Health = FMath::Max(0.f, Health - Damage);
    UE_LOG(LogTemp, Display, TEXT("PLAYER_DAMAGE amount=%.1f health=%.1f"), Damage, Health);
    if (GEngine) GEngine->AddOnScreenDebugMessage(91401, 3.f, FColor::Red,
        FString::Printf(TEXT("HP %.0f / %.0f%s"), Health, MaxHealth, IsDead() ? TEXT(" - Respawning...") : TEXT("")));
    ACharacter* Character = Cast<ACharacter>(Actor);
    APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
    if (PC && PC->PlayerCameraManager)
        PC->PlayerCameraManager->StartCameraFade(.3f, 0.f, .3f, FLinearColor(.6f,0,0), false, false);
    if (IsDead() && Character && PC)
    {
        // 蟠桃续命：一次生命机会，原地以复活比例站起并清算中毒/控制（旧 _reviveInPlace），不走重生换 pawn。
        double ReviveRatio=0;
        if(Model&&Model->ConsumePeachRevive(ReviveRatio))
        {
            Health=FMath::Max(1.f,FMath::FloorToFloat(MaxHealth*(ReviveRatio>0?ReviveRatio:.3f)));
            if(auto* Poison=Actor->FindComponentByClass<UMaggotPoisonComponent>())Poison->ClearPoison();
            if(auto* S=Actor->FindComponentByClass<UCombatStatusFormula>())S->PurgeTransient();
            UE_LOG(LogTemp, Display, TEXT("PEACH_REVIVE hp=%.0f ratio=%.2f"), Health, ReviveRatio);
            if(GEngine) GEngine->AddOnScreenDebugMessage(91402, 3.f, FColor(255, 215, 0), TEXT("蟠桃续命：原地复活"));
            return;
        }
        Character->DisableInput(PC);
        Character->GetCharacterMovement()->StopMovementImmediately();
        Character->GetCharacterMovement()->DisableMovement();
        Character->SetActorTickEnabled(false); // Stops held-fire and movement updates until the new pawn exists.
        GetWorld()->GetTimerManager().SetTimer(RespawnTimer, this, &UFPSCombatHealthComponent::Respawn, 2.f, false);
    }
}

void UFPSCombatHealthComponent::Respawn()
{
    APawn* Pawn = Cast<APawn>(GetOwner());
    AController* Controller = Pawn ? Pawn->GetController() : nullptr;
    AGameModeBase* Mode = GetWorld()->GetAuthGameMode();
    if (!Pawn || !Controller || !Mode) return;
    Controller->UnPossess();
    Pawn->Destroy();
    Mode->RestartPlayer(Controller);
}

void UFPSCombatHealthComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorld()->GetTimerManager().ClearTimer(RespawnTimer);
    Super::EndPlay(Reason);
}
