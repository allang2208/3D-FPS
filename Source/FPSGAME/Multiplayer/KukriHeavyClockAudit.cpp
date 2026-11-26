#include "KukriNetworkAuditCommandlet.h"
#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "Engine/World.h"
#include "Serialization/JsonSerializer.h"
#include <limits>

void UKukriNetworkAuditCommandlet::CheckHeavyClock(AColdSteelPlayerState* PS,AFPSGAMECharacter* Pawn,
    TFunctionRef<void(bool,const TCHAR*)> Check)
{
    auto* Model=PS->ShadowModel.Get();auto* K=Pawn->FindComponentByClass<UKukriWeaponComponent>();auto* World=Pawn->GetWorld();
    Check(K&&!Pawn->IsLocallyControlled(),TEXT("heavy fixture uses a remote authority pawn"));if(!K)return;
    const auto Base=Model->Snapshot();
    for(const TCHAR* Definition:{TEXT("ue_kukri"),TEXT("ue_tactical_hatchet")})
    {
        const auto Assert=[&](bool OK,const TCHAR* Name){Check(OK,*(FString(Definition)+TEXT(" ")+Name));};
        auto Main=Model->CreateItem(Definition);Main.Place=1;Main.Cell=6;
        auto Off=Model->CreateItem(Definition);Off.Place=1;Off.Cell=8;
        auto Seed=Base;Seed.Items={Main};Seed.Stamina=100.f;
        const auto Reset=[&](bool Dual=false)
        {
            Seed.Items=Dual?TArray<FColdSteelItem>{Main,Off}:TArray<FColdSteelItem>{Main};Model->AdoptNetMirror(Seed);
            K->bServerHeavyCharging=false;K->ServerHeavyStartedAt=K->ServerHeavyReceivedAt=K->ServerHeavyLastStartedAt=-1.;
            K->NetworkHeavyReleaseUntil=-1.;K->ServerHeavyWeapon.Reset();K->ServerHeavyOffhandWeapon.Reset();World->TimeSeconds=10.;
        };
        const auto Start=[&](double Stamp,bool Dual=false)
        {K->ServerSetKukriHeavyCharge_Implementation(Main.InstanceId,true,false,Dual,Stamp);};
        const auto Stop=[&](bool Release)
        {K->ServerSetKukriHeavyCharge_Implementation(Main.InstanceId,false,Release,false,World->GetTimeSeconds());};
        // Deterministic clock/resource fixture: debit exactly the observed interval.
        // The separate UDP fixture exercises FPSStaminaModel's actual frame ticks.
        const auto Advance=[&](double Seconds)
        {Model->SpendStamina(Seconds*Model->HeavyChargeStaminaPerSecond());World->TimeSeconds+=Seconds;};
        Reset();Assert(K->Animations.IsEmpty(),TEXT("authority holds no first-person animations"));
        for(const double Stamp:{9.,10.5,std::numeric_limits<double>::quiet_NaN()})
        {Start(Stamp);Assert(!K->bServerHeavyCharging&&Model->Stamina()==100.f,TEXT("stale future or NaN start rejected without payment"));}
        Start(9.6);Assert(K->bServerHeavyCharging&&FMath::IsNearlyEqual(K->ServerHeavyStartedAt,9.6),TEXT("delayed begin retains bounded input time"));
        Start(9.3);Assert(FMath::IsNearlyEqual(K->ServerHeavyStartedAt,9.6),TEXT("duplicate begin cannot backdate active charge"));
        K->ServerSetKukriHeavyCharge_Implementation(TEXT("wrong weapon"),false,true,false,10.);
        Assert(K->bServerHeavyCharging,TEXT("foreign weapon stop cannot erase charge"));
        Advance(.2);Stop(true);
        Assert(!K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId)&&!K->ConsumeNetworkHeavyChargeForRelease(Main.InstanceId),TEXT("premature release and later hit cannot commit"));
        Start(9.6);Assert(!K->bServerHeavyCharging,TEXT("replayed cancelled begin cannot reopen charge"));
        Reset();Start(9.6);Stop(false);
        Assert(Model->Stamina()==100.f&&!K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId),TEXT("tap cancellation does not bill network transit or release"));
        for(const bool Dual:{false,true})
        {
            Reset(Dual);Start(9.6,Dual);
            const double Rate=Model->HeavyChargeStaminaPerSecond(),Required=K->ServerHeavyRequired;
            const double Cost=ColdSteelMelee::HeavyReleaseStamina(Model->ActiveKukriWeapon(),Model,Dual);
            Advance(Required-.4);
            // A PlayerState hit can beat the component stop RPC: payment is still once.
            Assert(K->ConsumeNetworkHeavyChargeForRelease(Main.InstanceId),TEXT("delayed single or paired release commits without loaded clips"));
            Assert(FMath::IsNearlyEqual(double(Model->Stamina()),100.-Required*Rate-Cost,.001),TEXT("hidden charge time plus release billed exactly once"));
            const float Paid=Model->Stamina();const uint32 Serial=K->NetworkHeavyReleaseSerial;
            Stop(true);Stop(true);
            Assert(Model->Stamina()==Paid&&Serial==K->NetworkHeavyReleaseSerial,TEXT("late and duplicate release cannot debit twice"));
            Assert(K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId)&&(!Dual||K->IsNetworkHeavyReleaseWindowOpen(Off.InstanceId)),TEXT("released blade identities retained"));
            K->RecordNetworkHeavyTarget(Main.InstanceId,Pawn);
            Assert(!K->IsNetworkHeavyTargetNew(Main.InstanceId,Pawn),TEXT("duplicate contact remains rejected"));
            World->TimeSeconds+=1.;Assert(!K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId),TEXT("receipt still expires"));
        }
        Reset();Start(10.);const double Rate=Model->HeavyChargeStaminaPerSecond(),Required=K->ServerHeavyRequired;
        const double Cost=ColdSteelMelee::HeavyReleaseStamina(Model->ActiveKukriWeapon(),Model,false);
        Advance(Required);Stop(true);
        Assert(FMath::IsNearlyEqual(double(Model->Stamina()),100.-Required*Rate-Cost,.001),TEXT("normal delivery retains original total cost"));
        Reset();Start(9.6);Advance(K->ServerHeavyRequired-.4);
        auto Low=Model->Snapshot();Low.Stamina=ColdSteelMelee::HeavyReleaseStamina(Model->ActiveKukriWeapon(),Model,false);Model->AdoptNetMirror(Low);Stop(true);
        Assert(!K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId)&&Model->Stamina()==Low.Stamina,TEXT("release must afford both catchup and strike atomically"));
        Reset(true);Start(9.6,true);Advance(K->ServerHeavyRequired-.4);
        auto Removed=Model->Snapshot();Removed.Items.RemoveAll([&](const FColdSteelItem& Item){return Item.InstanceId==Off.InstanceId;});Model->AdoptNetMirror(Removed);Stop(true);
        Assert(!K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId),TEXT("offhand removal invalidates paired release"));
        Reset();Start(9.6);Advance(K->ServerHeavyRequired-.4);
        Removed=Model->Snapshot();Removed.Items.Reset();Model->AdoptNetMirror(Removed);Stop(true);
        Assert(!K->IsNetworkHeavyReleaseWindowOpen(Main.InstanceId),TEXT("main weapon removal invalidates release"));

        Reset(true);
        const double BaseCharge=ColdSteelMelee::HeavyChargeSeconds(Main,Model,true);
        const auto Untuned=ColdSteelMelee::Evaluate(Main,Model);
        const auto SetPommel=[](FColdSteelItem& Blade,const TCHAR* Id)
        {
            TSharedPtr<FJsonObject> Data;
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Blade.Data),Data);
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("pommel"),Id);
            Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
            Blade.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Blade.Data));
        };
        SetPommel(Main,TEXT("knife_pommel_chenheng"));SetPommel(Off,TEXT("knife_pommel_yangu"));
        Reset(true);
        const auto Chenheng=ColdSteelMelee::Evaluate(Main,Model);
        const auto Yangu=ColdSteelMelee::Evaluate(Off,Model);
        Assert(FMath::IsNearlyEqual(Chenheng.Modifiers.PhysicalDamage,1.10)&&FMath::IsNearlyEqual(Chenheng.HeavyMultiplier,Untuned.HeavyMultiplier*1.25)
            &&FMath::IsNearlyEqual(Chenheng.Modifiers.Stamina,1.10),TEXT("Chenheng physical, heavy damage and stamina use the installed hand"));
        Assert(FMath::IsNearlyEqual(Yangu.Modifiers.AttackSpeed,1.15)&&FMath::IsNearlyEqual(Yangu.Modifiers.Stamina,.85)
            &&FMath::IsNearlyEqual(Yangu.HeavyChargeSeconds,BaseCharge/1.20),TEXT("Yangu speed, stamina and single-blade charge"));
        Start(10.,true);
        Assert(FMath::IsNearlyEqual(K->ServerHeavyRequired,(BaseCharge+Yangu.HeavyChargeSeconds)*.5,.001),TEXT("mixed pommels get no pair bonus on authority"));
        SetPommel(Main,TEXT("knife_pommel_yangu"));Reset(true);Start(10.,true);
        Assert(FMath::IsNearlyEqual(K->ServerHeavyRequired,BaseCharge/1.20/1.10,.001),TEXT("dual Yangu pair bonus applies once on authority"));
        if(Main.Definition==TEXT("ue_tactical_hatchet"))
        {
            auto Old=Main;Old.Place=0;Old.Cell=7;Old.bRotated=true;Old.Width=3;Old.Height=2;
            TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Old.Data),Data);
            Data->SetNumberField(TEXT("grid_w"),2);Data->SetNumberField(TEXT("grid_h"),3);
            Old.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Old.Data));
            bool Changed=false;FString Reason;
            Assert(ColdSteelInventory::MigrateAuthoredItemFootprint(Old,Changed,Reason)&&Changed&&Old.bRotated&&Old.Width==3&&Old.Height==1
                &&Old.Cell==7&&Old.InstanceId==Main.InstanceId&&Old.Data.Contains(TEXT("knife_pommel_yangu")),
                TEXT("old rotated 2x3 axe shrinks to 3x1 without losing its cell or installed pommel"));
            Assert(Model->SanitizeNetworkItem(Old)&&Old.Width==3&&Old.Height==1&&ColdSteelInventory::BaseFootprint(Old)==FIntPoint(1,3),
                TEXT("validated rotated guest axe remains a canonical 1x3 item"));
        }
    }
}
