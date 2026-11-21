// Source/FPSGAME/UI/ColdSteelVillageTree.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 36-36 | struct FProject
        if(Id==TEXT("high_wall"))return bComplete ? TEXT("已升级") : bAvailable ? TEXT("可升级") : TEXT("需先修复围墙");

// Lines 49-57 | struct FProject
        {TEXT("wall"), TEXT("defense"), TEXT("修复围墙"), TEXT("墙"), TEXT("村庄防御"),
            TEXT("补齐村庄外围的残墙与墙柱，清理坍塌缺口的碎石，为留下的居民恢复完整的防护边界。"),
            TEXT("整圈残破围墙切换为修复后的围墙，恢复墙体碰撞，保留原有城门通道。")},
        {TEXT("high_wall"), TEXT("defense"), TEXT("升级石砌高墙"), TEXT("垛"), TEXT("村庄防御"),
            TEXT("沿原有墙线加筑高墙与城垛。东西门楼下设升降铁闸，二层守望平台与墙顶步道相通。"),
            TEXT("村庄围墙升级为带步道的高墙，两处入口装上升降铁闸。"),false,TEXT("wall")},
        {TEXT("village_construction"), TEXT("defense"), TEXT("村庄修建"), TEXT("建"), TEXT("村庄建筑"),
            TEXT("学会砌筑围墙、城门和登墙石阶，为村庄增设防线与出入口。"),
            TEXT("按 B 打开「村庄建筑」，可自行放置石头围墙、木质大门、石砌高墙、升降铁闸门和城墙石阶。"),true},

// Lines 218-218 | TSharedRef<SWidget> UColdSteelNpcDialogue::VillageDetail()
    const bool Upgrade=Selected==TEXT("high_wall");
