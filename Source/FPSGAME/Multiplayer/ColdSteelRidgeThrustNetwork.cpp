#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

void AColdSteelPlayerState::ServerBeginRidgeStrike_Implementation(APawn* ActionPawn,const FString& Weapon,uint32 Serial,uint8 Meta,double ClientStartedAt)
{
    using namespace HighlandRidgeThrust;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Item=ShadowModel&&!ShadowModel->ActiveProductionTool()?ShadowModel->Equipped():nullptr;
    if(!Pawn||Pawn!=ActionPawn||!Serial||!Installed(GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item)||
        Item->InstanceId!=Weapon||(Meta!=1&&Meta!=2&&!IsStrikeMeta(Meta)&&!IsHeavyMeta(Meta)))return;
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();if(!Sword)return;
    const double Now=GetWorld()->GetTimeSeconds();
    // Match hit reports' server-synchronized clock. Different transit delays
    // between two legitimate swings must not shorten their combo interval.
    if(!FMath::IsFinite(ClientStartedAt)||ClientStartedAt<=0.||ClientStartedAt>Now+.1||Now-ClientStartedAt>.9)return;
    const double StartedAt=FMath::Min(ClientStartedAt,Now);
    const bool SamePawn=RidgeStrike.Pawn.Get()==Pawn;
    if(SamePawn&&(int32(Serial-RidgeStrike.Serial)<=0||StartedAt<=RidgeStrike.StartedAt))return;
    if(SamePawn&&Weapon==RidgeStrike.Weapon&&Meta>=3&&StartedAt<RidgeStrike.HitUntil)return;
    const bool Chain=SamePawn&&Weapon==RidgeStrike.Weapon&&StartedAt<=RidgeStrike.ChainUntil;
    if((Meta==2||Meta==3)&&(!Chain||Meta!=RidgeStrike.NextStage||StartedAt+.12<RidgeStrike.NextSwingAt))return;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,ShadowModel);
    const bool Normal=Meta<=3;
    const double Rate=FMath::Max(.01,Normal?Stats.AttackRate*(Meta==3?FinisherPlaybackRate:1.f):double(LightningHaste::ActionSpeed(Pawn)));
    const float Lead=Meta==0x10?0.f:CounterLead;
    const double Duration=Meta<=2?Stats.AttackSeconds:ToWall(Lead+ReleaseSeconds,Lead,Rate);
    RidgeStrike.Pawn=Pawn;RidgeStrike.Weapon=Weapon;RidgeStrike.Serial=Serial;RidgeStrike.Meta=Meta;
    if(Meta!=0x16)RidgeStrike.NextStage=(Meta==1||IsHeavyMeta(Meta))?2:Meta==2?3:1;
    else if(!Chain)RidgeStrike.NextStage=1;
    RidgeStrike.StartedAt=StartedAt;RidgeStrike.NextSwingAt=StartedAt+Duration;
    RidgeStrike.ChainUntil=RidgeStrike.NextSwingAt+1.05;
    RidgeStrike.Targets.Reset();
    if(Meta<=2)return;
    RidgeStrike.HitFrom=StartedAt+(Lead+ContactStart)/Rate-.15;
    RidgeStrike.HitUntil=StartedAt+(Lead+ContactEnd)/Rate+.30;
    const double Length=Meta==3?Stats.ThrustReach:Meta==0x16?ShadowModel->DashAttackStats().RangeCM:
        Stats.SlashReach*Stats.Modifiers.MartialRange*ReachScale;
    RidgeStrike.Length=Length*Sword->ActiveRidgeRangeScale();
    RidgeStrike.DashForward=Pawn->GetBaseAimRotation().Vector().GetSafeNormal2D();
}
