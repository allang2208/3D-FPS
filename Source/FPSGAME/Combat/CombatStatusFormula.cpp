#include "CombatStatusFormula.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Skills/FireballDamage.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Monsters/PoisonMaggotProjectile.h"
#include "../Monsters/HandBrainFearComponent.h"
UCombatStatusFormula::UCombatStatusFormula(){PrimaryComponentTick.bCanEverTick=true;}
UCombatStatusFormula* UCombatStatusFormula::GetOrAdd(AActor* Target)
{
    if(!IsValid(Target))return nullptr;
    auto* C=Target->FindComponentByClass<UCombatStatusFormula>();
    if(!C){C=NewObject<UCombatStatusFormula>(Target);Target->AddInstanceComponent(C);C->RegisterComponent();}return C;
}
void UCombatStatusFormula::AddCorrosion(int32 Stacks,float Seconds,float Reduction)
{
    if(IsImmune()||Stacks<=0)return;
    CorrosionStacks+=Stacks;CorrosionDuration=FMath::Max(.001f,Seconds);CorrosionTime=CorrosionDuration;
    CorrosionReduction=FMath::Max(CorrosionReduction,Reduction);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("corrosion"),CorrosionTime,CorrosionStacks);
}
void UCombatStatusFormula::AddMagicResistanceShred(float Ratio,float Seconds)
{
    if(IsImmune()||Seconds<=0||Ratio<=0)return;
    Shred=FMath::Max(ShredTime>0?Shred:0,FMath::Clamp(Ratio,0.f,.95f));ShredTime=FMath::Max(ShredTime,Seconds);
}
void UCombatStatusFormula::AddHolyWard(float Multiplier,float Seconds)
{
    if(Seconds>0){Ward=FMath::Min(WardTime>0?Ward:1,FMath::Clamp(Multiplier,.05f,1.f));WardTime=FMath::Max(WardTime,Seconds);
        UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("holyWard"),WardTime);}
}
void UCombatStatusFormula::AddMagicVulnerability(int32 Stacks)
{if(!IsImmune()&&Stacks>0){VulnerabilityStacks+=Stacks;VulnerabilityTime=5;}}
void UCombatStatusFormula::AddRuneMagicVulnerability(float Ratio,float Seconds)
{
    if(IsImmune()||Ratio<=0||Seconds<=0)return;
    RuneVulnerability=Ratio;RuneVulnerabilityTime=Seconds;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("runeMagicVulnerability"),Seconds,1);
}
void UCombatStatusFormula::AddBleeding(AActor* Source,int32 Stacks)
{if(!IsImmune()&&Stacks>0){BleedStacks+=Stacks;BleedTime=10;if(BleedTick<=0)BleedTick=1;BleedSource=Source;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("bleed"),BleedTime,BleedStacks);}}
void UCombatStatusFormula::GrantRiposteGuard(float Seconds,float AttackSpeed,float Stamina)
{
    if(Seconds<=0)return;
    RiposteTime=Seconds;RiposteSpeed=AttackSpeed;RiposteStamina=Stamina;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("riposteInspiration"),Seconds,1);
}
void UCombatStatusFormula::AddBurn(AActor* Source,float Matk,int32 Stacks,float Seconds,float Multiplier,float TickSeconds)
{
    if(IsImmune()||Stacks<=0||Seconds<=0||TickSeconds<=0)return;
    for(int32 I=0;I<Stacks;++I)Burns.Add({Source,FMath::Max(1.f,FMath::FloorToFloat(Matk*Multiplier)),Seconds});
    BurnInterval=TickSeconds;if(BurnTick<=0)BurnTick=BurnInterval;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("burn"),Seconds,Burns.Num());
}
void UCombatStatusFormula::SetStatusImmune(bool Immune)
{
    bImmune=Immune;
    if(Immune)UStatusEffectsComponent::GetOrCreate(GetOwner())->SetPersistent(TEXT("statusImmune"));
    else UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("statusImmune"));
}
void UCombatStatusFormula::AddStatusImmune(float Seconds)
{
    if(Seconds<=0)return;
    ImmuneTime=FMath::Max(ImmuneTime,Seconds);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("statusImmune"),Seconds);
}
void UCombatStatusFormula::InterruptOwnerActions(float Seconds)
{
    // 玩家侧统一走破防输入锁（它自带 stun 卡片与输入恢复），怪物侧沿用与冻结一致的四类中断链。
    if(auto* W=Cast<AWolfMonster>(GetOwner()))W->InterruptAttack(Seconds);
    if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->InterruptAttack(Seconds);
    if(auto* N=Cast<ANurseZombie>(GetOwner()))N->InterruptAttack(Seconds);
    if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->InterruptAttack(Seconds);
}
void UCombatStatusFormula::AddStun(float Seconds)
{
    if(IsImmune()||Seconds<=0)return;
    StunTime=FMath::Max(StunTime,Seconds);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("stun"),Seconds);
    if(auto* Character=Cast<ACharacter>(GetOwner()))
        if(const auto* Pawn=Cast<APawn>(Character);Pawn&&Pawn->IsPlayerControlled())
            if(auto* Lock=Character->FindComponentByClass<UPlayerGuardBreakComponent>()){Lock->Apply(Seconds);return;}
    InterruptOwnerActions(Seconds);
}
void UCombatStatusFormula::AddBind(float Seconds)
{
    if(IsImmune()||Seconds<=0)return;
    BindTime=FMath::Max(BindTime,Seconds);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("bind"),Seconds);
}
void UCombatStatusFormula::AddSlow(float Seconds,float Percent)
{
    if(IsImmune()||Seconds<=0)return;
    SlowPct=FMath::Max(SlowTime>0?SlowPct:0,FMath::Clamp(Percent,0.f,.95f));SlowTime=FMath::Max(SlowTime,Seconds);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("slow"),Seconds);
}
void UCombatStatusFormula::AddCripple(float Seconds)
{
    // 旧 gamedev：致残复用 slow 计时语义，仅 HUD 显示借用 🦴/致残/#8a8a7a。
    if(IsImmune()||Seconds<=0)return;
    SlowPct=FMath::Max(SlowTime>0?SlowPct:0,.5f);SlowTime=FMath::Max(SlowTime,Seconds);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimedDisplay(TEXT("slow"),Seconds,-1,TEXT("致残"),TEXT("🦴"),TEXT("#8a8a7a"));
}
void UCombatStatusFormula::AddWaxSeal(float Seconds,float Percent)
{
    if(IsImmune()||Seconds<=0)return;
    WaxPct=FMath::Clamp(Percent,0.f,.9f);WaxTime=Seconds; // 重复命中只刷新时间，不叠层
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("waxSealSlow"),Seconds);
}
void UCombatStatusFormula::AddWeaponHaste(float Seconds,float Percent)
{
    if(IsImmune()||Seconds<=0)return;
    WeaponHasteMul=1+FMath::Max(0.f,Percent);WeaponHasteTime=Seconds; // 只刷新持续时间
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("weaponHaste"),Seconds);
}
void UCombatStatusFormula::AddPetrify(float Seconds,float MagicTakenMul)
{
    if(IsImmune()||Seconds<=0)return;
    PetrifyTime=FMath::Max(PetrifyTime,Seconds);PetrifyMul=FMath::Max(1.f,MagicTakenMul);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("petrified"),Seconds,1);
    if(auto* Character=Cast<ACharacter>(GetOwner()))
        if(const auto* Pawn=Cast<APawn>(Character);Pawn&&Pawn->IsPlayerControlled())
            if(auto* Lock=Character->FindComponentByClass<UPlayerGuardBreakComponent>()){Lock->Apply(Seconds);return;}
    InterruptOwnerActions(Seconds);
}
void UCombatStatusFormula::AddMarked(float Seconds,float Value)
{
    if(IsImmune()||Seconds<=0)return;
    MarkedValue=FMath::Max(MarkedTime>0?MarkedValue:0,FMath::Max(0.f,Value));MarkedTime=FMath::Max(MarkedTime,Seconds);
}
void UCombatStatusFormula::AddInspire(float Seconds,float SpeedMul,float AtkMul)
{
    if(IsImmune()||Seconds<=0)return;
    // 旧口径：已激励只刷新时长；首次才乘算一次数值。UE 用瞬时乘区，效果等价且不会漂移。
    InspireTime=Seconds;
    if(InspireSpeed<=1){InspireSpeed=SpeedMul;InspireAtk=AtkMul;}
    else{InspireSpeed=FMath::Max(InspireSpeed,SpeedMul);InspireAtk=FMath::Max(InspireAtk,AtkMul);}
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("inspire"),Seconds);
}
void UCombatStatusFormula::AddCamelFright(float Seconds,float Reduction)
{
    if(IsImmune()||Seconds<=0)return;
    const float Value=FMath::Max(0.f,FMath::Min(.9f,Reduction));
    CamelReduction=FMath::Max(CamelTime>0?CamelReduction:0,Value);CamelTime=FMath::Max(CamelTime,Seconds);
}
void UCombatStatusFormula::AddMinePoison(float RefreshSeconds,float LingerSeconds)
{
    if(IsImmune()||RefreshSeconds<=0)return;
    MineTime=FMath::Max(MineTime,RefreshSeconds);MineLinger=FMath::Max(.001f,LingerSeconds);
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("minePoison"),MineLinger);
}
void UCombatStatusFormula::AddDroneMark(FName SourceId,float DamageBonusPercent,float CritBonusPercent,float Seconds,AActor* MarkOwner)
{
    if(IsImmune()||SourceId.IsNone()||Seconds<=0)return;
    FDroneMark* Existing=Drones.Find(SourceId);
    const FDroneMark Prev=Existing?*Existing:FDroneMark{};
    FDroneMark& Mark=Drones.FindOrAdd(SourceId);Mark.SourceId=SourceId;
    Mark.DamagePercent=FMath::Max(0.f,DamageBonusPercent);Mark.CritPercent=FMath::Max(0.f,CritBonusPercent);
    Mark.Remaining=FMath::Max(0.f,Seconds);Mark.Owner=MarkOwner;
    if(Prev.Remaining>0&&Prev.DamagePercent==Mark.DamagePercent&&Prev.CritPercent==Mark.CritPercent)Mark.Owner=Prev.Owner.IsValid()?Prev.Owner:Mark.Owner;
    auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
    float MaxRemaining=0;for(const auto& Pair:Drones)MaxRemaining=FMath::Max(MaxRemaining,Pair.Value.Remaining);
    Display->SetTimed(TEXT("droneVulnerability"),MaxRemaining,1);
}
void UCombatStatusFormula::RemoveDroneMark(FName SourceId,bool bImmediate)
{
    if(SourceId.IsNone())Drones.Empty();
    else if(bImmediate)Drones.Remove(SourceId);
    else if(auto* Mark=Drones.Find(SourceId))Mark->Remaining=FMath::Min(Mark->Remaining,.2f); // 回收宽限：短暂延迟仍归零
    float MaxRemaining=0;for(const auto& Pair:Drones)MaxRemaining=FMath::Max(MaxRemaining,Pair.Value.Remaining);
    auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
    if(Drones.IsEmpty())Display->Remove(TEXT("droneVulnerability"));else Display->SetTimed(TEXT("droneVulnerability"),MaxRemaining,1);
}
static bool IsDroneBeneficiary(const AActor* Attacker)
{
    if(!Attacker)return false; // 无来源（毒、环境）不享受易伤加成，与旧版阵营门槛一致
    const auto* Pawn=Cast<APawn>(Attacker);
    if(Pawn&&Pawn->IsPlayerControlled())return true;
    return Attacker->ActorHasTag(TEXT("Summoned"))||Attacker->ActorHasTag(TEXT("Companion"))||Attacker->ActorHasTag(TEXT("Ally"));
}
float UCombatStatusFormula::DroneDamageMultiplier(const AActor* Attacker)const
{
    if(Drones.IsEmpty()||!IsDroneBeneficiary(Attacker))return 1.f;
    const FDroneMark* Best=nullptr;
    for(const auto& Pair:Drones)if(Pair.Value.Remaining>0)
        if(!Best||Pair.Value.DamagePercent>Best->DamagePercent||(Pair.Value.DamagePercent==Best->DamagePercent&&Pair.Value.CritPercent>Best->CritPercent))Best=&Pair.Value;
    return Best?1+Best->DamagePercent*.01f:1.f;
}
float UCombatStatusFormula::DroneCritBonusPercent(const AActor* Attacker)const
{
    if(Drones.IsEmpty()||!IsDroneBeneficiary(Attacker))return 0.f;
    const FDroneMark* Best=nullptr;
    for(const auto& Pair:Drones)if(Pair.Value.Remaining>0)
        if(!Best||Pair.Value.DamagePercent>Best->DamagePercent||(Pair.Value.DamagePercent==Best->DamagePercent&&Pair.Value.CritPercent>Best->CritPercent))Best=&Pair.Value;
    return Best?Best->CritPercent:0.f;
}
float UCombatStatusFormula::OutgoingDamageMultiplier()const
{
    float Multiplier=(CamelTime>0?1-CamelReduction:1)*(InspireTime>0?InspireAtk:1);
    const auto* Pawn=Cast<APawn>(GetOwner());
    return Multiplier;
}
float UCombatStatusFormula::MovementMultiplier()const
{
    if(FrozenTime>0||StunTime>0||BindTime>0||PetrifyTime>0)return 0.f;
    float Mul=FMath::Max(.01f,1-ChillStacks*ChillSlow)*(1+.1f*HasteStacks);
    if(SlowTime>0)Mul*=FMath::Max(0.f,1-SlowPct);
    if(WaxTime>0)Mul*=FMath::Max(0.f,1-WaxPct);
    if(WeaponHasteTime>0)Mul*=WeaponHasteMul;
    if(InspireTime>0)Mul*=InspireSpeed;
    return Mul;
}
void UCombatStatusFormula::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);
    const bool WardWas=WardTime>0;ShredTime=FMath::Max(0.f,ShredTime-Delta);WardTime=FMath::Max(0.f,WardTime-Delta);
    if(WardWas&&WardTime<=0)UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("holyWard"));
    auto Expire=[&](float& Time,int32& Stacks,FName Name){if(Time<=0)return;Time=FMath::Max(0.f,Time-Delta);if(Time==0){Stacks=0;UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(Name);}};
    auto ExpireT=[&](float& Time,FName Name){if(Time<=0)return;Time=FMath::Max(0.f,Time-Delta);if(Time==0)UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(Name);};
    Expire(ChillTime,ChillStacks,TEXT("chill"));Expire(HasteTime,HasteStacks,TEXT("haste"));Expire(ChainTime,ChainStacks,TEXT("chainSpell"));
    Expire(ElectrifiedTime,ElectrifiedStacks,TEXT("electrified"));
    ExpireT(StunTime,TEXT("stun"));ExpireT(BindTime,TEXT("bind"));
    ExpireT(PetrifyTime,TEXT("petrified"));ExpireT(InspireTime,TEXT("inspire"));
    ExpireT(SlowTime,TEXT("slow"));ExpireT(WaxTime,TEXT("waxSealSlow"));
    ExpireT(WeaponHasteTime,TEXT("weaponHaste"));ExpireT(MarkedTime,TEXT("marked"));
    ExpireT(CamelTime,TEXT("camelFright"));ExpireT(ImmuneTime,TEXT("statusImmune"));
    FrozenTime=FMath::Max(0.f,FrozenTime-Delta);
    RuneVulnerabilityTime=FMath::Max(0.f,RuneVulnerabilityTime-Delta);
    RiposteTime=FMath::Max(0.f,RiposteTime-Delta);
    if(CorrosionStacks>0){const int32 Before=CorrosionStacks;CorrosionTime-=Delta;while(CorrosionTime<=0&&CorrosionStacks>0){--CorrosionStacks;CorrosionTime+=CorrosionDuration;}
        if(const int32 Now2=CorrosionStacks;Now2!=Before) // 事件式刷新：只在层数变化时更新卡片，倒计时由 End 自然同步
        {auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
         if(Now2>0)Display->SetTimed(TEXT("corrosion"),CorrosionTime,Now2);else Display->Remove(TEXT("corrosion"));}}
    if(VulnerabilityStacks>0){VulnerabilityTime-=Delta;while(VulnerabilityTime<=0&&VulnerabilityStacks>0){--VulnerabilityStacks;VulnerabilityTime+=5;}}
    if(!Drones.IsEmpty())
    {
        float MaxRemaining=0;TArray<FName> Dead;
        for(auto& Pair:Drones){Pair.Value.Remaining=FMath::Max(0.f,Pair.Value.Remaining-Delta);
            if(Pair.Value.Remaining<=0)Dead.Add(Pair.Key);else MaxRemaining=FMath::Max(MaxRemaining,Pair.Value.Remaining);}
        // 旧口径：击杀时统一释放全部无人机来源标记；由来源系统在击杀钩子调用 RemoveDroneMark(NAME_None)。
        for(const auto& Id:Dead)Drones.Remove(Id);
        if(!Dead.IsEmpty()) // 卡片倒计时靠 End 自然同步，仅在标记集合变化时重发布
        {
            auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
            if(Drones.IsEmpty())Display->Remove(TEXT("droneVulnerability"));else Display->SetTimed(TEXT("droneVulnerability"),MaxRemaining,1);
        }
    }
    // 状态跳伤（流血、灼烧、矿毒）不进入硬直闸门：伤害类型保持不变以避免影响减伤公式，
    // 只在怪物受击端把反应倍率临时压到 0。玩家目标没有该组件时按原样结算。
    auto Apply=[&](float Damage,AActor* Source,UClass* DamageClass){
        const auto* Pawn=Cast<APawn>(Source);
        auto Deal=[&](){ return UGameplayStatics::ApplyDamage(GetOwner(),Damage,Pawn?Pawn->GetController():nullptr,Source,DamageClass); };
        if(auto* Combat=GetOwner()->FindComponentByClass<UMonsterCombatComponent>())Combat->ApplyHitWithReactionScale(0.f,Deal);else Deal();
    };
    auto OwnerHealth=[&](float& Health,float& MaxHealth)
    {Health=0;MaxHealth=0;
        if(const auto* N=Cast<ANurseZombie>(GetOwner())){Health=N->Health;MaxHealth=N->MaxHealth;}
        else if(const auto* H=Cast<AHandBrainMonster>(GetOwner())){Health=H->Health;MaxHealth=H->MaxHealth;}
        else if(const auto* M=Cast<APoisonMaggotMonster>(GetOwner())){Health=M->Health;MaxHealth=M->MaxHealth;}
        else if(const auto* W=Cast<AWolfMonster>(GetOwner())){Health=W->Health;MaxHealth=W->MaxHealth;}
        else if(const auto* C=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>()){Health=C->Health;MaxHealth=C->MaxHealth;}
    };
    if(BleedStacks>0)
    {
        BleedTime-=Delta;BleedTick-=Delta;
        while(BleedTick<=0)
        {
            float Health=0,MaxHealth=0;OwnerHealth(Health,MaxHealth);
            if(Health>0)Apply(FMath::Max(1.f,FMath::FloorToFloat(Health*.01f*BleedStacks)),BleedSource.Get(),UCombatDirectDamage::StaticClass());BleedTick+=1;
        }
        const bool Had=BleedStacks>0;
        while(BleedTime<=0&&BleedStacks>0){--BleedStacks;BleedTime+=10;}
        if(Had)
        {
            auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
            if(BleedStacks>0)Display->SetTimed(TEXT("bleed"),BleedTime,BleedStacks);else Display->Remove(TEXT("bleed"));
        }
    }
    if(!Burns.IsEmpty())
    {
        BurnTick-=Delta;for(auto& B:Burns)B.Remaining-=Delta;
        const int32 Before=Burns.Num();Burns.RemoveAll([](const auto& B){return B.Remaining<=0;});
        if(Burns.IsEmpty())BurnTick=0;
        else while(BurnTick<=0){float Damage=0;AActor* Source=nullptr;for(const auto& B:Burns){Damage+=B.Damage;if(!Source)Source=B.Source.Get();}Apply(Damage,Source,UFireballDamage::StaticClass());BurnTick+=BurnInterval;}
        if(const int32 After=Burns.Num();After!=Before) // 层数变化才重发布；剩余时间由卡片 End 自然倒数
        {
            auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
            if(After==0)Display->Remove(TEXT("burn"));
            else{float Longest=0;for(const auto& B:Burns)Longest=FMath::Max(Longest,B.Remaining);Display->SetTimed(TEXT("burn"),Longest,After);}
        }
    }
    else if(BurnTick!=0)BurnTick=0;
    if(MineTime>0)
    {
        MineTime-=Delta;MineTick-=Delta;
        while(MineTime>0&&MineTick<=0)
        {
            float Health=0,MaxHealth=0;OwnerHealth(Health,MaxHealth);
            // 旧口径：每秒结算 floor(maxHp*0.005) 魔法伤害，不足 1 也保底 0.1（<1 会被防御下限吸收为 0，不强制保底 1）。
            if(MaxHealth>0&&Health>0)Apply(FMath::Max(.1f,FMath::FloorToFloat(MaxHealth*.005f)),nullptr,UStatusMagicDamage::StaticClass());
            MineTick+=1;
        }
        if(MineTime<=0)
        {MineTime=0;MineTick=0;UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("minePoison"));}
    }
}

void UCombatStatusFormula::AddChill(int32 Stacks,float Seconds,float SlowPerStack)
{
    if(IsImmune()||FrozenTime>0||Stacks<=0||Seconds<=0)return;
    if(ChillStacks==0)ChillSlow=SlowPerStack;
    ChillStacks+=Stacks;ChillTime+=Seconds;
    if(ChillStacks>=20)
    {
        ChillStacks-=10;FrozenTime=Seconds;
        InterruptOwnerActions(Seconds);
        UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("frozen"),Seconds,1);
    }
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("chill"),ChillTime,ChillStacks);
}
bool UCombatStatusFormula::AddElectrified(int32 Stacks,float Seconds,int32 OverloadThreshold,float BonusPerStack)
{
    if(IsImmune()||Stacks<=0||Seconds<=0)return false;
    ElectrifiedStacks+=Stacks;ElectrifiedTime+=Seconds;ElectrifiedBonus=BonusPerStack;
    auto* Display=UStatusEffectsComponent::GetOrCreate(GetOwner());
    if(ElectrifiedStacks>=FMath::Max(1,OverloadThreshold))
    {ElectrifiedStacks=0;ElectrifiedTime=0;Display->Remove(TEXT("electrified"));return true;}
    Display->SetTimed(TEXT("electrified"),ElectrifiedTime,ElectrifiedStacks);return false;
}
void UCombatStatusFormula::AddHaste(int32 Stacks,float Seconds)
{
    if(IsImmune()||Stacks<=0||Seconds<=0)return;HasteStacks+=Stacks;HasteTime+=Stacks*Seconds;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("haste"),HasteTime,HasteStacks);
}
void UCombatStatusFormula::AddChainSpell()
{
    if(IsImmune())return;++ChainStacks;ChainTime+=10;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("chainSpell"),ChainTime,ChainStacks);
}
void UCombatStatusFormula::ConsumeChainSpell()
{ChainTime=0;ChainStacks=0;UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("chainSpell"));}
void UCombatStatusFormula::ShowProcTile(FName Type,float Seconds)
{if(Seconds>0)UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(Type,Seconds,1);}
void UCombatStatusFormula::PurgeTransient()
{
    ChillStacks=HasteStacks=ChainStacks=ElectrifiedStacks=CorrosionStacks=VulnerabilityStacks=BleedStacks=0;
    ChillTime=HasteTime=ChainTime=ElectrifiedTime=CorrosionTime=VulnerabilityTime=BleedTime=BurnTick=0;
    FrozenTime=StunTime=BindTime=SlowTime=WaxTime=WeaponHasteTime=PetrifyTime=MarkedTime=InspireTime=0;
    CamelTime=ImmuneTime=MineTime=MineTick=RuneVulnerabilityTime=RiposteTime=ShredTime=WardTime=0;
    Ward=1;SlowPct=WaxPct=CamelReduction=0;WeaponHasteMul=InspireSpeed=InspireAtk=1;MarkedValue=.15f;
    Burns.Empty();BleedSource.Reset();Drones.Empty();
    if(auto* Display=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())
        for(FName Type:{TEXT("chill"),TEXT("frozen"),TEXT("haste"),TEXT("chainSpell"),TEXT("electrified"),TEXT("corrosion"),
            TEXT("bleed"),TEXT("burn"),TEXT("stun"),TEXT("bind"),TEXT("slow"),TEXT("waxSealSlow"),TEXT("weaponHaste"),
            TEXT("petrified"),TEXT("marked"),TEXT("inspire"),TEXT("camelFright"),TEXT("statusImmune"),TEXT("minePoison"),
            TEXT("droneVulnerability"),TEXT("holyWard"),TEXT("holyRenewal"),TEXT("runeMagicVulnerability"),TEXT("riposteInspiration")})Display->Remove(Type);
}
int32 UCombatStatusFormula::CleanseDebuffs(int32 Count)
{
    // 旧 holy-light-system.js:47-50 白名单顺序：poison→bleed→fear→chill→frozen→slow→waxSealSlow→bind→magicVulnerability→droneVulnerability→electrified。
    AActor* Owner=GetOwner();auto* Display=Owner->FindComponentByClass<UStatusEffectsComponent>();
    int32 Cleansed=0;
    auto Take=[&](){return Cleansed<Count;};
    auto Clear=[&](FName Tile){if(Display)Display->Remove(Tile);};
    if(Take())if(auto* P=Owner->FindComponentByClass<UMaggotPoisonComponent>();P&&P->Stacks>0){P->ClearPoison();++Cleansed;}
    if(Take())if(BleedStacks>0){BleedStacks=0;BleedTime=BleedTick=0;BleedSource.Reset();Clear(TEXT("bleed"));++Cleansed;}
    if(Take())if(auto* F=Owner->FindComponentByClass<UHandBrainFearComponent>();F&&F->Stacks>0){F->Cleanse();++Cleansed;}
    if(Take())if(ChillStacks>0||ChillTime>0){ChillStacks=0;ChillTime=0;Clear(TEXT("chill"));++Cleansed;}
    if(Take())if(FrozenTime>0){FrozenTime=0;Clear(TEXT("frozen"));++Cleansed;}
    if(Take())if(SlowTime>0){SlowTime=0;SlowPct=0;Clear(TEXT("slow"));++Cleansed;}
    if(Take())if(WaxTime>0){WaxTime=0;WaxPct=0;Clear(TEXT("waxSealSlow"));++Cleansed;}
    if(Take())if(BindTime>0){BindTime=0;Clear(TEXT("bind"));++Cleansed;}
    if(Take())if(VulnerabilityStacks>0){VulnerabilityStacks=0;VulnerabilityTime=0;++Cleansed;}
    if(Take())if(!Drones.IsEmpty()){Drones.Empty();Clear(TEXT("droneVulnerability"));++Cleansed;}
    if(Take())if(ElectrifiedStacks>0||ElectrifiedTime>0){ElectrifiedStacks=0;ElectrifiedTime=0;Clear(TEXT("electrified"));++Cleansed;} // 旧口径：净化感电须硬置层数归零
    return Cleansed;
}
