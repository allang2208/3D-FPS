// F6 开发面板的数据入口：等级、技能等级与物品目录。全部走档案的
// SyncRuntime → Snapshot → CommitState 事务，控件不直接改写存档。
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
    /** 大类沿用目录顺序，武器与消耗品的真实类型形成独立子标题。 */
    void ClassifyItem(const FString& Category,const FString& Type,const FString& WeaponType,
        const FString& WeaponTag,FColdSteelCatalogEntry& Entry)
    {
        if(Category==TEXT("weapon")||Category==TEXT("weapon_melee")||Category==TEXT("weapon_ranged")||
            Category==TEXT("weapon_magic")||Category==TEXT("weapon_bow"))
        {
            Entry.Group=TEXT("武器");Entry.GroupOrder=0;
            Entry.Subgroup=TEXT("其他武器");Entry.SubgroupOrder=8;
            if(WeaponType==TEXT("pistol")){Entry.Subgroup=TEXT("手枪");Entry.SubgroupOrder=0;}
            else if(WeaponType==TEXT("rifle")){Entry.Subgroup=TEXT("步枪");Entry.SubgroupOrder=1;}
            else if(WeaponType==TEXT("shotgun")){Entry.Subgroup=TEXT("霰弹枪");Entry.SubgroupOrder=2;}
            else if(WeaponType==TEXT("machineGun")){Entry.Subgroup=TEXT("机枪");Entry.SubgroupOrder=3;}
            else if(WeaponType==TEXT("sword")||Category==TEXT("weapon_melee")){Entry.Subgroup=TEXT("近战武器");Entry.SubgroupOrder=4;}
            else if(WeaponType==TEXT("bow")||Category==TEXT("weapon_bow")){Entry.Subgroup=TEXT("弓");Entry.SubgroupOrder=5;}
            else if(WeaponType==TEXT("staff")||Category==TEXT("weapon_magic")){Entry.Subgroup=TEXT("魔法武器");Entry.SubgroupOrder=6;}
            if(!WeaponTag.IsEmpty())Entry.Subgroup=WeaponTag;
            return;
        }
        if(Category==TEXT("material")&&Type==TEXT("弹药"))
        {Entry.Group=TEXT("弹药");Entry.GroupOrder=1;Entry.Subgroup=TEXT("枪械弹药");return;}
        if(Category==TEXT("consumable"))
        {
            Entry.Group=TEXT("消耗品");Entry.GroupOrder=2;
            Entry.Subgroup=Type.IsEmpty()||Type==TEXT("消耗品")?TEXT("常用消耗品"):Type;
            Entry.SubgroupOrder=Type==TEXT("食物")?1:0;
            return;
        }
        if(Category==TEXT("material")&&Type==TEXT("建材")){Entry.Group=TEXT("建材");Entry.GroupOrder=4;}
        else if(Category==TEXT("enhancement")){Entry.Group=TEXT("强化道具");Entry.GroupOrder=5;Entry.SubgroupOrder=Type==TEXT("附魔卷轴")?1:0;}
        else if(Category==TEXT("tribute")){Entry.Group=TEXT("祭品");Entry.GroupOrder=6;}
        else if(Category==TEXT("gold")){Entry.Group=TEXT("货币");Entry.GroupOrder=7;}
        else if(Category==TEXT("material")){Entry.Group=TEXT("材料");Entry.GroupOrder=3;}
        else if(Category==TEXT("equipment")){Entry.Group=TEXT("装备");Entry.GroupOrder=8;}
        else {Entry.Group=TEXT("其他");Entry.GroupOrder=9;}
        if(!Type.IsEmpty()&&Type!=Entry.Group)Entry.Subgroup=Type;
    }
}

const TArray<FName>& UColdSteelStatusModel::SkillCatalog() const
{
    // 顺序即开发面板的技能下拉顺序；与 ColdSteelSkills::Migrate 建立的存档键一一对应。
    static const TArray<FName> Ids={
        TEXT("rifleMastery"),TEXT("pistolMastery"),TEXT("swordMastery"),
        TEXT("machineGunMastery"),TEXT("shotgunMastery"),TEXT("bowMastery"),
        TEXT("heavyStrike"),TEXT("whirlwind"),TEXT("dashAttack"),TEXT("criticalStrike"),TEXT("dodge"),
        TEXT("dexterousHands"),TEXT("fireball"),TEXT("iceSpike"),TEXT("lightningStrike"),TEXT("stormDomain"),TEXT("thunderLance"),TEXT("holyLight"),TEXT("quickCombat")};
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
    if(Id==TEXT("lightningStrike"))return LightningDefinition();
    if(ElectricMagic::IsSkill(Id))return ElectricMagicDefinition(Id);
    if(Id==TEXT("holyLight"))return HolyLightDefinition();
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
        FString Category,Type,WeaponType,WeaponTag;
        Object->TryGetStringField(TEXT("category"),Category);
        Object->TryGetStringField(TEXT("type"),Type);
        Object->TryGetStringField(TEXT("weaponType"),WeaponType);
        Object->TryGetStringField(TEXT("weaponTypeTag"),WeaponTag);
        ClassifyItem(Category,Type,WeaponType,WeaponTag,Entry);
        ItemCatalogCache.Add(MoveTemp(Entry));
    }
    for(const auto& Type:AmmoTypes)if(Type.Enabled)
    {FColdSteelCatalogEntry Entry;Entry.Definition=Type.Id;Entry.Name=AmmoLabel(Type.Id);Entry.Group=TEXT("弹药");Entry.GroupOrder=1;Entry.Subgroup=Type.Group==TEXT("arrow")?TEXT("箭矢（弹药袋）"):TEXT("枪械弹药");Entry.SubgroupOrder=Type.Group==TEXT("arrow")?1:0;ItemCatalogCache.Add(MoveTemp(Entry));}
    // 大类、子类分别连续，名称重名时按真实 definition 稳定排序。
    ItemCatalogCache.Sort([](const FColdSteelCatalogEntry& A,const FColdSteelCatalogEntry& B)
    {
        if(A.GroupOrder!=B.GroupOrder)return A.GroupOrder<B.GroupOrder;
        if(A.Group!=B.Group)return A.Group<B.Group;
        if(A.SubgroupOrder!=B.SubgroupOrder)return A.SubgroupOrder<B.SubgroupOrder;
        if(A.Subgroup!=B.Subgroup)return A.Subgroup<B.Subgroup;
        if(A.Name!=B.Name)return A.Name<B.Name;
        return A.Definition<B.Definition;
    });
    return ItemCatalogCache;
}
