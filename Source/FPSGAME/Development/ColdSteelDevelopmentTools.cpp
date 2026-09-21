// F6 开发面板的数据入口：等级、技能等级与物品目录。全部走档案的
// SyncRuntime → Snapshot → CommitState 事务，控件不直接改写存档。
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    /** 物品数据只有 category/type，开发面板下拉按它们归纳成玩家能看懂的一类。 */
    void ClassifyItem(const FString& Category,const FString& Type,FString& OutGroup,int32& OutOrder)
    {
        if(Category==TEXT("weapon")||Category==TEXT("weapon_melee")||Category==TEXT("weapon_ranged")||Category==TEXT("weapon_magic"))
        {OutGroup=TEXT("武器");OutOrder=0;return;}
        if(Category==TEXT("material")&&Type==TEXT("弹药")){OutGroup=TEXT("弹药");OutOrder=1;return;}
        if(Category==TEXT("consumable")){OutGroup=TEXT("消耗品");OutOrder=2;return;}
        if(Category==TEXT("material")&&Type==TEXT("建材")){OutGroup=TEXT("建材");OutOrder=4;return;}
        if(Category==TEXT("enhancement")){OutGroup=TEXT("强化材料");OutOrder=5;return;}
        if(Category==TEXT("tribute")){OutGroup=TEXT("祭品");OutOrder=6;return;}
        if(Category==TEXT("gold")){OutGroup=TEXT("货币");OutOrder=7;return;}
        if(Category==TEXT("material")){OutGroup=TEXT("材料");OutOrder=3;return;}
        OutGroup=TEXT("其他");OutOrder=8;
    }
}

const TArray<FName>& UColdSteelStatusModel::SkillCatalog() const
{
    // 顺序即开发面板的技能下拉顺序；与 ColdSteelSkills::Migrate 建立的存档键一一对应。
    static const TArray<FName> Ids={
        TEXT("rifleMastery"),TEXT("pistolMastery"),TEXT("swordMastery"),
        TEXT("machineGunMastery"),TEXT("shotgunMastery"),TEXT("bowMastery"),
        TEXT("heavyStrike"),TEXT("whirlwind"),TEXT("dashAttack"),TEXT("criticalStrike"),TEXT("dodge"),
        TEXT("dexterousHands"),TEXT("fireball"),TEXT("iceSpike"),TEXT("quickCombat")};
    return Ids;
}

const FColdSteelSkillDefinition& UColdSteelStatusModel::DevelopmentSkillDefinition(FName Id) const
{
    // MasteryDefinition 只含步枪／手枪与五个额外武器精通，其余键会回退成步枪；
    // 开发面板要按技能自身定义显示名称、满级与图标。
    if(Id==TEXT("dodge"))return DodgeDefinition();
    if(Id==TEXT("dexterousHands"))return DexterousHandsDefinition();
    if(Id==TEXT("criticalStrike"))return CriticalStrikeDefinition();
    if(Id==TEXT("fireball"))return FireballDefinition();
    if(Id==TEXT("iceSpike"))return IceSpikeDefinition();
    if(Id==TEXT("quickCombat"))return QuickCombatDefinition();
    return MasteryDefinition(Id);
}

bool UColdSteelStatusModel::GrantLevel(int32 Count)
{
    if(Count<=0||Count>1000)return false;
    SyncRuntime();auto Next=Snapshot();
    const int32 Target=FMath::Clamp(Next.Level+Count,1,10000);
    if(Target==Next.Level)return false;
    // 沿用正常升级：每级 3 点属性点，经验必须小于当前等级的门槛，否则存档校验会拒绝。
    Next.Points=FMath::Min(Next.Points+(Target-Next.Level)*3,1000000);
    Next.Level=Target;
    const int64 Need=(20ll+Next.Level*20ll+int64(Next.Level)*Next.Level*12)*8;
    Next.Experience=FMath::Min(Next.Experience,Need-1);
    return CommitState(MoveTemp(Next));
}

bool UColdSteelStatusModel::RaiseSkillLevel(FName Id,int32 Count)
{
    if(Count<=0||!SkillCatalog().Contains(Id))return false;
    const FColdSteelSkillDefinition& Definition=DevelopmentSkillDefinition(Id);
    SyncRuntime();auto Next=Snapshot();
    FColdSteelSkillProgress& Progress=Next.Skills.FindOrAdd(Id);
    if(Progress.Level>=Definition.MaxLevel)return false;
    Progress.Level=FMath::Clamp(Progress.Level+Count,1,Definition.MaxLevel);
    // 满级必须把修炼值清零，与 ColdSteelSkills::Validate 的合同一致。
    if(Progress.Level>=Definition.MaxLevel)Progress.Experience=0;
    return CommitState(MoveTemp(Next));
}

bool UColdSteelStatusModel::MaxSkillLevel(FName Id)
{
    if(!SkillCatalog().Contains(Id))return false;
    const FColdSteelSkillDefinition& Definition=DevelopmentSkillDefinition(Id);
    SyncRuntime();auto Next=Snapshot();
    FColdSteelSkillProgress& Progress=Next.Skills.FindOrAdd(Id);
    if(Progress.Level>=Definition.MaxLevel)return false;
    Progress.Level=Definition.MaxLevel;Progress.Experience=0;
    return CommitState(MoveTemp(Next));
}

const TArray<FColdSteelCatalogEntry>& UColdSteelStatusModel::ItemCatalog() const
{
    if(bItemCatalogBuilt)return ItemCatalogCache;
    bItemCatalogBuilt=true;
    for(const auto& Pair:Definitions)
    {
        if(AmmoType(Pair.Key))continue;
        TSharedPtr<FJsonObject> Object;
        if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Pair.Value),Object)||!Object)continue;
        FColdSteelCatalogEntry Entry;
        Entry.Definition=Pair.Key;
        Object->TryGetStringField(TEXT("name"),Entry.Name);
        if(Entry.Name.IsEmpty())Entry.Name=Pair.Key;
        FString Category,Type;
        Object->TryGetStringField(TEXT("category"),Category);
        Object->TryGetStringField(TEXT("type"),Type);
        ClassifyItem(Category,Type,Entry.Group,Entry.GroupOrder);
        ItemCatalogCache.Add(MoveTemp(Entry));
    }
    for(const auto& Type:AmmoTypes)if(Type.Enabled)
    {FColdSteelCatalogEntry Entry;Entry.Definition=Type.Id;Entry.Name=AmmoLabel(Type.Id);Entry.Group=TEXT("弹药");Entry.GroupOrder=1;ItemCatalogCache.Add(MoveTemp(Entry));}
    // 类别顺序固定，类别内按名称排序；下拉列表按此顺序生成，同类条目连续。
    ItemCatalogCache.Sort([](const FColdSteelCatalogEntry& A,const FColdSteelCatalogEntry& B)
    {
        if(A.GroupOrder!=B.GroupOrder)return A.GroupOrder<B.GroupOrder;
        if(A.Name!=B.Name)return A.Name<B.Name;
        return A.Definition<B.Definition;
    });
    return ItemCatalogCache;
}
