#include "CoreFormulaAuditCommandlet.h"
#include "CoreCombatFormula.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "../Monsters/FatZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Skills/FireballDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "CombatFormulaRuntime.h"
int32 UCoreFormulaAuditCommandlet::Main(const FString& Params)
{
    FString Text;TSharedPtr<FJsonObject> Root;
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("CoreFormulaAudit");
    if(!FFileHelper::LoadFileToString(Text,*(Dir/TEXT("reference.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return 2;
    int32 Passed=0,Failed=0;
    const auto Check=[&](double Actual,double Expected,const TCHAR* Field=TEXT("")){if(FMath::Abs(Actual-Expected)<1.e-8)++Passed;else{++Failed;UE_LOG(LogTemp,Error,TEXT("FORMULA_MISMATCH actual=%.12f expected=%.12f field=%s"),Actual,Expected,Field);}};
    struct FPlayerField
    {
        const TCHAR* Name;
        double CoreCombatFormula::Stats::* Member;
        int32 ReferenceIndex=INDEX_NONE;
    };
    FPlayerField PlayerFields[]={
        {TEXT("atk"),&CoreCombatFormula::Stats::Atk},{TEXT("def"),&CoreCombatFormula::Stats::Def},
        {TEXT("matk"),&CoreCombatFormula::Stats::Matk},{TEXT("mdef"),&CoreCombatFormula::Stats::Mdef},
        {TEXT("crit"),&CoreCombatFormula::Stats::Crit},{TEXT("critRes"),&CoreCombatFormula::Stats::CritRes},
        {TEXT("aspd"),&CoreCombatFormula::Stats::AttackSpeed},{TEXT("speed"),&CoreCombatFormula::Stats::Speed},
        {TEXT("maxHp"),&CoreCombatFormula::Stats::MaxHp},{TEXT("maxMp"),&CoreCombatFormula::Stats::MaxMp},
        {TEXT("mpRegen"),&CoreCombatFormula::Stats::MpRegen}};
    const auto& ReferenceFields=Root->GetArrayField(TEXT("fields"));
    for(auto& Field:PlayerFields)
    {
        Field.ReferenceIndex=ReferenceFields.IndexOfByPredicate([&](const auto& V){return V->AsString()==Field.Name;});
        if(Field.ReferenceIndex==INDEX_NONE)
        {
            UE_LOG(LogTemp,Error,TEXT("FORMULA_REFERENCE_MISSING_FIELD %s"),Field.Name);return 2;
        }
    }
    int32 ExcludedPlayerFields=0;
    for(const auto& Value:ReferenceFields)
    {
        const FString Name=Value->AsString();
        // The FPS uses collision hits and movement dodges, not the legacy rolls.
        // Report these reference-only stats as excluded, never as passing tests.
        if(Name==TEXT("hit")||Name==TEXT("dodge"))
        {
            ++ExcludedPlayerFields;
            UE_LOG(LogTemp,Display,TEXT("PLAYER_FORMULA_EXCLUDED field=%s (legacy probability stat)"),*Name);
        }
    }
    for(const auto& Value:Root->GetArrayField(TEXT("players")))
    {
        const auto O=Value->AsObject();const auto& A=O->GetArrayField(TEXT("attrs"));
        const auto S=CoreCombatFormula::Player({A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber(),A[3]->AsNumber(),A[4]->AsNumber(),A[5]->AsNumber()},O->GetIntegerField(TEXT("level")));
        const auto& E=O->GetArrayField(TEXT("expected"));
        if(E.Num()!=ReferenceFields.Num()){UE_LOG(LogTemp,Error,TEXT("FORMULA_REFERENCE_FIELD_COUNT_MISMATCH"));return 2;}
        for(const auto& Field:PlayerFields)Check(S.*(Field.Member),E[Field.ReferenceIndex]->AsNumber(),Field.Name);
    }
    for(const auto& Value:Root->GetArrayField(TEXT("cases")))
    {
        const auto O=Value->AsObject();
        Check(CoreCombatFormula::Defense(O->GetNumberField(TEXT("damage")),O->GetNumberField(TEXT("def")),O->GetBoolField(TEXT("magic")),O->GetNumberField(TEXT("penetration")),O->GetNumberField(TEXT("shred")),O->GetNumberField(TEXT("corrosion"))),O->GetNumberField(TEXT("expected")));
    }
    for(const auto& Value:Root->GetArrayField(TEXT("weaponCases")))
    {
        const auto O=Value->AsObject();std::vector<CoreCombatFormula::WeaponTerm> Terms;
        for(const auto& V:O->GetArrayField(TEXT("terms"))){const auto& T=V->AsArray();Terms.push_back({T[0]->AsNumber(),T[1]->AsNumber(),T[2]->AsNumber()});}
        Check(CoreCombatFormula::Weapon(O->GetNumberField(TEXT("base")),O->GetNumberField(TEXT("flat")),O->GetNumberField(TEXT("level")),Terms),O->GetNumberField(TEXT("expected")));
    }
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CoreFormulaAuditWorld"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    // Actual TakeDamage entry points, isolated from player saves and map BeginPlay.
    auto Monster=[&](auto* Target,double Physical,double Magic)
    {
        if(!Target){Check(0,1);return;}
        Target->Health=10000;
        FDamageEvent PhysicalEvent;FDamageEvent MagicEvent(UFireballDamage::StaticClass());
        Check(Target->TakeDamage(100,PhysicalEvent,nullptr,nullptr),Physical);
        Check(Target->Health,10000-Physical);
        Check(Target->TakeDamage(100,MagicEvent,nullptr,nullptr),Magic);
        Check(Target->Health,10000-Physical-Magic);
        Check(Target->TakeDamage(.5f,PhysicalEvent,nullptr,nullptr),0);
        const CombatFormulaRuntime::MagicHit Critical{1000,.5,0};
        TGuardValue<const CombatFormulaRuntime::MagicHit*> Scope(CombatFormulaRuntime::ActiveMagicHit,&Critical);
        Check(Target->TakeDamage(100,MagicEvent,nullptr,nullptr),std::floor(Magic*1.5));
        Target->Destroy();
    };
    Monster(World->SpawnActor<ANurseZombie>(),100,100);
    Monster(World->SpawnActor<AFatZombie>(),63,93);
    Monster(World->SpawnActor<AHandBrainMonster>(),44,48);
    Monster(World->SpawnActor<APoisonMaggotMonster>(),63,62);
    FColdSteelProfile Profile;Profile.Level=3;Profile.Attributes={{TEXT("con"),10},{TEXT("wis"),10},{TEXT("intt"),10}};
    Check(UColdSteelStatusModel::ResourceMaximum(Profile,false),220);
    Check(UColdSteelStatusModel::ResourceMaximum(Profile,true),270);
    FColdSteelItem Armor;Armor.Place=1;Armor.Data=TEXT("{\"enhanceLevel\":2,\"bonusStats\":{\"con\":3,\"maxHp\":20},\"bonusPerEnhance\":{\"con\":0.5}}");Profile.Items.Add(Armor);
    Check(UColdSteelStatusModel::ResourceMaximum(Profile,false),280);
    Check(CoreCombatFormula::CriticalChance(25,40),0);Check(CoreCombatFormula::CriticalChance(45,40),5);
    World->DestroyWorld(false);
    const FString Result=FString::Printf(TEXT("{\"passed\":%d,\"failed\":%d,\"playerFieldsComparedPerCase\":%d,\"playerFieldsExcludedPerCase\":%d}"),Passed,Failed,int32(UE_ARRAY_COUNT(PlayerFields)),ExcludedPlayerFields);
    FFileHelper::SaveStringToFile(Result,*(Dir/TEXT("result.json")));
    UE_LOG(LogTemp,Display,TEXT("CORE_FORMULA_AUDIT %s"),*Result);return Failed?1:0;
}
