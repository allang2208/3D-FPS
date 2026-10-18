#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

void AColdSteelPlayerState::ServerSetBowDraw_Implementation(AFPSGAMECharacter* Character,const FString& Weapon,bool bDrawing,float CarriedSeconds)
{
    if (!HasAuthority() || !Character || Character != GetPawn()) return;
    BowDrawStartedAt=-1.;BowDrawPawn.Reset();BowDrawWeapon.Reset();
    if (!bDrawing || !FMath::IsFinite(CarriedSeconds)) return;
    const auto* PC=Cast<APlayerController>(GetOwner());
    const auto* Model=PC&&PC->IsLocalController()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():ShadowModel.Get();
    const auto* Bow=Model?Model->ActiveBow():nullptr;
    const auto* Health=Character->FindComponentByClass<UFPSCombatHealthComponent>();
    if (!Bow || Bow->InstanceId!=Weapon || !Health || Character->IsTraversing()) return;
    // 死亡或弓已卸下时清掉待生效的完美节拍加速，避免重生/换弓后白拿一次加速。
    if (Health->IsDead()) { bBowPerfectSpeedBonus=false; return; }
    BowDrawPawn=Character;BowDrawWeapon=Weapon;
    BowDrawSeconds=float(ColdSteelBow::Evaluate(*Bow,Model).Draw)*ColdSteelBow::DrawSpeedScale(bBowPerfectSpeedBonus);
    // DrawEntry may finish partway through a rendered frame. Bound the carried
    // portion, while retaining the same start as the owner's animation clock.
    BowDrawStartedAt=GetWorld()->GetTimeSeconds()-FMath::Clamp(CarriedSeconds,0.f,.25f);
}

bool AColdSteelPlayerState::ExecuteBowShot(const FColdSteelInventoryRequest& Request,UColdSteelStatusModel* Model,FString& Reason)
{
    // 客户端在完美窗口松手时会先按预测加速下一箭；服务器一旦拒绝本次射击，
    // 必须清掉该预测，否则客户端会永久比服务器快 25%，之后每箭都被判非完美。
    auto Reject=[&](const TCHAR* Why)
    {
        if(Request.BowReleaseElapsed>=0.f)ClientClearBowPerfectSpeedBonus();
        Reason=Why;return false;
    };
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const double DrawAge=GetWorld()->GetTimeSeconds()-BowDrawStartedAt;
    const bool HasDrawSession=BowDrawStartedAt>=0. && BowDrawPawn==Pawn && BowDrawWeapon==Request.Item;
    BowDrawStartedAt=-1.;BowDrawPawn.Reset();BowDrawWeapon.Reset();
    const auto* Bow=Model?Model->ActiveBow():nullptr;
    const FVector Direction=FVector(Request.Direction).GetSafeNormal();
    if(!Pawn||!Bow||Bow->InstanceId!=Request.Item||Pawn->IsTraversing()
        ||!FMath::IsFinite(Request.Charge)||Request.Charge<ColdSteelBow::MinimumFireDrawFraction||Request.Charge>1.f
        ||Request.Eye.ContainsNaN()||Request.Origin.ContainsNaN()||Direction.ContainsNaN()||Direction.IsNearlyZero()
        ||FVector::DistSquared(Request.Eye,Pawn->GetPawnViewLocation())>FMath::Square(150.f)
        ||FVector::DistSquared(Request.Origin,Request.Eye)>FMath::Square(200.f)
        ||FVector::DotProduct(Direction,Pawn->GetBaseAimRotation().Vector())<.7f)
    {return Reject(TEXT("弓或瞄准位置已变化，请重新拉弓"));}
    const FColdSteelItem Fired=*Bow;
    const auto Stats=ColdSteelBow::Evaluate(Fired,Model);
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now-LastBowShotAt<FMath::Max(.1,Stats.Nock*.5))return Reject(TEXT("射击间隔过短"));
    // Both clocks must agree; clients never provide a damage amount or multiplier.
    // The bounded allowance absorbs delivery jitter, not an extra bonus window.
    const bool Perfect=HasDrawSession && Request.Charge>=1.f
        && ColdSteelBow::IsPerfectRelease(Request.BowReleaseElapsed,BowDrawSeconds)
        && FMath::Abs(DrawAge-Request.BowReleaseElapsed)<=.15;
    const FString Ammo=Model->AmmoDefinitionFor(Fired);
    const bool Owned=!Pawn->HasInfiniteReserveAmmoFor(Ammo);
    const float Cost=float(Stats.Stamina)*FMath::Lerp(.4f,1.f,Request.Charge);
    if(!Model->CanSpendStamina(Cost)||(Owned&&Model->PouchCount(Ammo)<1))
    {Reason=TEXT("体力或箭支不足");return Reject(TEXT("体力或箭支不足"));}
    auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto Visual=G?G->ResolveBowVisual(Fired):Fired;
    const auto N=[&](const TCHAR* Key,float Default){return float(ColdSteelInventory::Number(Visual,Key,Default));};
    auto* Shaft=LoadObject<UStaticMesh>(nullptr,*ColdSteelInventory::Text(Visual,TEXT("bow_part_arrow_mesh")));
    const auto HeadPath=ColdSteelInventory::Text(Visual,TEXT("arrow_head_mesh"));
    auto* Head=HeadPath.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*HeadPath);
    FActorSpawnParameters Spawn;Spawn.Owner=Pawn;Spawn.Instigator=Pawn;
    Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Arrow=GetWorld()->SpawnActor<ABowArrow>(Request.Origin,Direction.Rotation(),Spawn);
    if(!Arrow)return Reject(TEXT("箭支生成失败"));
    const auto Before=Model->Snapshot();auto After=Before;
    if(Owned)After.AmmoPouch.FindOrAdd(Ammo)-=1;
    After.Stamina=FMath::Max(0.f,After.Stamina-Cost);
    After.StaminaRecoveryDelay=Model->StaminaTuning.RecoveryDelay;
    if(!Model->CommitCampfireState(After,TEXT("Inventory"),SlotName))
    {Arrow->Destroy();Reason=TEXT("箭支扣除未保存，未发射");return Reject(TEXT("箭支扣除未保存，未发射"));}
    auto Shot=ColdSteelSkills::Snapshot(Pawn,&Fired,true);Shot.DamageContext=Request.Charge;
    Shot.bPerfectBowRelease=Perfect;
    if(N(TEXT("critical_chance"),-1)>=0)Shot.CriticalChance=FMath::Max(Shot.CriticalChance,N(TEXT("critical_chance"),-1));
    if(N(TEXT("toughness_multiplier"),0)>0)Shot.ToughnessDamageMultiplier=N(TEXT("toughness_multiplier"),0);
    const float Damage=(Shot.DamagePanel.Total()>0?Shot.DamagePanel.Total():N(TEXT("full_damage"),69))
        *ColdSteelBow::DrawDamageMultiplier(Request.Charge)*Model->AmmoDamageMultiplier(Fired);
    Arrow->Configure(Damage,float(Stats.Speed)*100.f*FMath::Lerp(FMath::Clamp(N(TEXT("min_speed_ratio"),.35f),0.f,1.f),1.f,Request.Charge),
        N(TEXT("arrow_gravity_cm"),520),N(TEXT("range_cm"),3200),Shot,Shaft,Head,
        N(TEXT("arrow_radius_cm"),.3f),N(TEXT("arrow_length_cm"),76),Ammo,Owned,N(TEXT("arrow_recovery_seconds"),120));
    Arrow->ResolveLaunchObstruction(Request.Eye);LastBowShotAt=Now;
    // 本次命中节拍 → 下一条箭 +25% 拉弓速度；未命中则清除。
    bBowPerfectSpeedBonus=Perfect;
    Reason=TEXT("已发射箭支");return true;
}

void AColdSteelPlayerState::ClientClearBowPerfectSpeedBonus_Implementation()
{
    if (auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn()))
        if (auto* Bow=Pawn->FindComponentByClass<UBowWeaponComponent>())
            Bow->ClearPerfectSpeedPending();
}
