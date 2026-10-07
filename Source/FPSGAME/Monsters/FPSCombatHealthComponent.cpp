#include "FPSCombatHealthComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "Net/UnrealNetwork.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "HandBrainMonster.h"
#include "M10HowlDamage.h"
#include "MantisM27AttackDamage.h"
#include "M09ResonanceDamage.h"
#include "PoisonMaggotMonster.h"
#include "PoisonMaggotProjectile.h"
#include "../Skills/CorrosivePusDamage.h"
#include "../Skills/LightningDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/GameStateBase.h"
#include "Camera/PlayerCameraManager.h"
#include "TimerManager.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"

bool UFPSCombatHealthComponent::IsInvulnerable() const
{
    const auto* Character=Cast<ACharacter>(GetOwner());
    if (UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Character, EDevelopmentTuningOption::Invincible)) return true;
    const auto* Move=Character?Cast<UFPSCharacterMovementComponent>(Character->GetCharacterMovement()):nullptr;
    return Move && Move->IsDodging();
}

void UFPSCombatHealthComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UFPSCombatHealthComponent, Health);
    DOREPLIFETIME(UFPSCombatHealthComponent, MaxHealth);
}
void UFPSCombatHealthComponent::OnRep_Health()
{
    // M3：客户端侧观察到的权威血量变化（怪物掉血/玩家 HP）。测试期留一条可见日志。
    UE_LOG(LogTemp, Warning, TEXT("MPTEST Health replicated: %s -> %.1f (dead=%d)"), *GetNameSafe(GetOwner()), Health, IsDead() ? 1 : 0);
    // 联机：服务端判死的本地 pawn 停止本地移动预测——否则死亡窗口内客户端继续走动，
    // 与服务端副本位置硬发散，直到 Respawn 换 pawn 才收束。重生销毁本 pawn，无需恢复。
    if (IsDead() && GetOwner() && !GetOwner()->HasAuthority())
    {
        if (auto* Character = Cast<ACharacter>(GetOwner()))
        {
            if (auto* Move = Character->GetCharacterMovement())
            {
                Move->StopMovementImmediately();
                Move->DisableMovement();
            }
        }
    }
}
void UFPSCombatHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    SetIsReplicated(true); // M3: 血量/上限走服务器权威复制（拥有者 actor 本身可复制）
    Health = MaxHealth;
    GetOwner()->OnTakeAnyDamage.AddDynamic(this, &UFPSCombatHealthComponent::OnDamage);
    // 联机权威端才录制位姿历史——rewind 命中校验的唯一消费者是服务端。
    if (GetOwner() && GetOwner()->HasAuthority() && GetWorld() && GetWorld()->GetNetMode() != NM_Standalone)
    {
        PrimaryComponentTick.bCanEverTick = true;
        SetComponentTickInterval(LagPoseInterval);
        SetComponentTickEnabled(true);
        RecordLagPose();
    }
}

void UFPSCombatHealthComponent::TickComponent(float DeltaTime, ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    if (GetOwner() && GetOwner()->HasAuthority()) RecordLagPose();
}

void UFPSCombatHealthComponent::RecordLagPose()
{
    AActor* Owner = GetOwner();
    UWorld* World = GetWorld();
    if (!Owner || !World) return;
    FFPSLagPose Pose;
    Pose.Time = World->GetTimeSeconds();
    FVector Top = Owner->GetActorLocation();
    if (const UCapsuleComponent* Capsule = Owner->FindComponentByClass<UCapsuleComponent>())
    {
        Pose.Center = Capsule->GetComponentLocation();
        Top = Pose.Center + FVector(0.f, 0.f, Capsule->GetScaledCapsuleHalfHeight());
    }
    else Pose.Center = Top;
    // 骨骼网格有 head 槽位时取更准的爆头参考点（怪物通用；玩家胶囊顶也够）。
    if (const USkeletalMeshComponent* Mesh = Owner->FindComponentByClass<USkeletalMeshComponent>())
        if (Mesh->DoesSocketExist(TEXT("head"))) Top = Mesh->GetSocketLocation(TEXT("head"));
    Pose.Top = Top;
    if (LagPoses.Num() >= MaxLagPoseEntries) LagPoses.RemoveAt(0, 1, EAllowShrinking::No);
    LagPoses.Add(Pose);
}

bool UFPSCombatHealthComponent::GetLagPose(double ServerTime, FVector& OutCenter, FVector& OutTop) const
{
    if (LagPoses.IsEmpty()) return false;
    if (ServerTime <= LagPoses[0].Time)
    {
        OutCenter = LagPoses[0].Center; OutTop = LagPoses[0].Top; return true;
    }
    if (ServerTime >= LagPoses.Last().Time)
    {
        OutCenter = LagPoses.Last().Center; OutTop = LagPoses.Last().Top; return true;
    }
    for (int32 i = 1; i < LagPoses.Num(); ++i)
    {
        if (LagPoses[i].Time >= ServerTime)
        {
            const FFPSLagPose& A = LagPoses[i - 1];
            const FFPSLagPose& B = LagPoses[i];
            const float T = static_cast<float>((ServerTime - A.Time) / FMath::Max(UE_DOUBLE_SMALL_NUMBER, B.Time - A.Time));
            OutCenter = FMath::Lerp(A.Center, B.Center, T);
            OutTop = FMath::Lerp(A.Top, B.Top, T);
            return true;
        }
    }
    return false;
}

float UFPSCombatHealthComponent::DamageAfterArmor(float Damage,const UDamageType* Type,AActor* Attacker) const
{
    if(Type&&Type->IsA<UCombatDirectDamage>())return Damage;
    const bool bMagic=CombatFormulaRuntime::IsMagic(Type);
    const auto* Status=GetOwner()->FindComponentByClass<UCombatStatusFormula>();
    const auto* AttackerStatus=Attacker?Attacker->FindComponentByClass<UCombatStatusFormula>():nullptr;
    // 联机：远端玩家的防御走影子档案；主机玩家（监听服下 NetShadowProfile 恒空）/单机回退单例。
    UColdSteelStatusModel* Model=nullptr;
    if(const auto* NetCharacter=Cast<AFPSGAMECharacter>(GetOwner()))Model=NetCharacter->GetNetShadowProfile();
    if(!Model&&GetWorld()&&GetWorld()->GetGameInstance())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
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
    const bool bSurvivalLoss=Type&&Type->IsA<UFPSSurvivalDamage>();
    // 联机：远端玩家的防御/续命判定走其影子档案，主机/单机回退 GameInstance 单例。
    UColdSteelStatusModel* Model=nullptr;
    if(const auto* NetCharacter=Cast<AFPSGAMECharacter>(Actor))Model=NetCharacter->GetNetShadowProfile();
    if(!Model&&GetWorld()->GetGameInstance())Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    // 月影庇护：参战（首次受击）触发短暂无敌，窗口内全部承伤无效（旧 moonstone special）。
    if(Model&&!bSurvivalLoss)
    {
        if(Model->IsMoonshadowActive())return;
        const double A=Model->TryActivateMoonshadow();
        if(A>0&&Model->IsMoonshadowActive())
        {
            UE_LOG(LogTemp, Display, TEXT("MOONSHADOW_INVULN until=%.2f"), A);
            return;
        }
    }
    if(bSurvivalLoss?UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Cast<APawn>(Actor),EDevelopmentTuningOption::Invincible):
        IsInvulnerable() && (!(Type&&Type->IsA<UCombatDirectDamage>())||UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Cast<APawn>(Actor),EDevelopmentTuningOption::Invincible)))return;
    AActor* Attacker=Causer?Causer:(Instigator?Instigator->GetPawn():nullptr);
    if(!Actor->IsA<AFPSGAMECharacter>())Damage=DamageAfterArmor(Damage,Type,Attacker);
    Health = FMath::Max(0.f, Health - Damage);
    if(!IsDead()&&!bSurvivalLoss&&!(Type&&Type->IsA<UMaggotPoisonDamage>()))
        if(auto* Body=Actor->FindComponentByClass<UFPSPlayerBodyComponent>())
            Body->RecordAcceptedHit(Instigator&&Instigator->GetPawn()?Instigator->GetPawn():Attacker,Damage,MaxHealth);
    // One roll per accepted M27 blade/landing hit. DoT ticks use a different
    // damage type, so they cannot proc themselves or refresh the cripple.
    if(Type&&Type->IsA<UMantisM27MeleeDamage>()&&Damage>0.f&&!IsDead())
        if(const auto* Pawn=Cast<APawn>(Actor);Pawn&&Pawn->IsPlayerControlled())
            if(auto* Status=UCombatStatusFormula::GetOrAdd(Actor);Status&&!Status->IsImmune())
            {
                const bool bPounce=Type->IsA<UMantisM27PounceDamage>();
                const bool bBleeding=FMath::FRand()<UMantisM27MeleeDamage::BleedChance;
                if(bPounce)Status->AddCripple(UMantisM27PounceDamage::CrippleSeconds);
                if(bBleeding)Status->AddBleeding(Attacker,1);
                if(!Pawn->IsLocallyControlled()&&(bPounce||bBleeding))
                    ClientApplyM27HitStatus(Attacker,bPounce,bBleeding,GetWorld()->GetTimeSeconds());
            }
    if(Type&&Type->IsA<UM10HowlDamage>())
    {
        // Exactly five SAN per accepted pulse; replaces the attacker's generic
        // SAN loss, and cannot fire on a dodged/immune hit rejected above.
        if(auto* Survival=Actor->FindComponentByClass<UFPSSurvivalComponent>())Survival->ApplySanityDamage(UM10HowlDamage::SanityLoss);
        if(!IsDead())if(auto* Status=UCombatStatusFormula::GetOrAdd(Actor);Status&&!Status->IsImmune())
        {
            Status->AddCripple(UM10HowlDamage::CrippleSeconds);
            if(const auto* Pawn=Cast<APawn>(Actor);Pawn&&Pawn->IsPlayerControlled()&&!Pawn->IsLocallyControlled())
                ClientApplyM10HowlCripple(GetWorld()->GetTimeSeconds()+UM10HowlDamage::CrippleSeconds);
        }
    }
    else if(Type&&Type->IsA<UM09ResonanceDamage>())
    {
        // A fixed two SAN replaces generic monster SAN loss for this accepted hit.
        // Dodge, invulnerability and rejected damage have already returned above.
        if(auto* Survival=Actor->FindComponentByClass<UFPSSurvivalComponent>())Survival->ApplySanityDamage(UM09ResonanceDamage::SanityLoss);
        if(!IsDead())if(auto* Status=UCombatStatusFormula::GetOrAdd(Actor))Status->AddSlow(.45f,.15f);
    }
    else if(!bSurvivalLoss)if(auto* Survival=Actor->FindComponentByClass<UFPSSurvivalComponent>())Survival->ApplySanityAttack(Attacker);
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
            if(auto* Survival=Actor->FindComponentByClass<UFPSSurvivalComponent>())
            {
                auto State=Survival->GetState();
                State.Hunger=State.Hydration=State.Sanity=60.f;
                Survival->RestoreState(State);
            }
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
    if(IsDead())ColdSteelSkills::NotifyKillByOwner(GetWorld()->GetGameInstance(),Instigator,Actor);
}

void UFPSCombatHealthComponent::ApplySurvivalDamage(float Amount)
{
    if(GetOwner()&&FMath::IsFinite(Amount)&&Amount>0.f)
        OnDamage(GetOwner(),Amount,GetDefault<UFPSSurvivalDamage>(),nullptr,nullptr);
}

void UFPSCombatHealthComponent::ClientApplyM10HowlCripple_Implementation(double ServerExpiresAt)
{
    if(!GetOwner()||GetOwner()->HasAuthority()||IsDead())return;
    const auto* GS=GetWorld()->GetGameState();
    const float Remaining=GS?FMath::Clamp(float(ServerExpiresAt-GS->GetServerWorldTimeSeconds()),0.f,UM10HowlDamage::CrippleSeconds):UM10HowlDamage::CrippleSeconds;
    if(Remaining>0.f)UCombatStatusFormula::GetOrAdd(GetOwner())->AddCripple(Remaining);
}

void UFPSCombatHealthComponent::ClientApplyM27HitStatus_Implementation(AActor* Source, bool bPounce, bool bBleeding, double ServerHitAt)
{
    if(!GetOwner()||GetOwner()->HasAuthority()||IsDead())return;
    auto* Status=UCombatStatusFormula::GetOrAdd(GetOwner());
    const auto* GS=GetWorld()->GetGameState();
    const float Age=GS?FMath::Max(0.f,float(GS->GetServerWorldTimeSeconds()-ServerHitAt)):0.f;
    if(bPounce)Status->AddCripple(FMath::Max(0.f,UMantisM27PounceDamage::CrippleSeconds-Age));
    // The server owns the chance roll and damage; the owning client mirrors
    // the existing status clock/HUD, without a second random roll.
    if(bBleeding)Status->AddBleeding(Source,1);
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
