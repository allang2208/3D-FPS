#pragma once

#include "CoreTypes.h"

namespace BlacksmithLessonText
{
inline const TCHAR* Quality()
{
    return TEXT("来，我教你从矿石到成剑。先收下这把十字镐，跟着地图找矿。等你带回矿石，合金胚和烧炉的木材由我出。")
        TEXT("看看我架上的兵器，留意「锻造伤害修正」。")
        TEXT("同样的兵器，有的比底子低 25%，有的能高出 5%。")
        TEXT("自己开炉，铁锭从原样起步，换金锭还能先添 10%。");
}

inline const TCHAR* Mining()
{
    return TEXT("地图上标的是离铺子最近、还有矿可采的露天铁矿脉。装备十字镐，把带铁纹的岩块敲开，再拾取掉下的铁矿石。攒够十块就回来。");
}

inline const TCHAR* Delivery()
{
    return TEXT("十块铁矿石带在身上了吗？交给我。我从里面挑三块让你练冶炼，再给你木材和一块合金胚。");
}

inline const TCHAR* Smelting()
{
    return TEXT("先去铺子西边，靠城门的布棚里有两座高炉，挑一座就行。")
        TEXT("给炉子添一份木材，选铁矿，把数量调到三份，开始冶炼。等炼好点领取，把三块铁锭带回铺子。");
}

inline const TCHAR* Materials()
{
    return TEXT("打一把剑要一块合金胚，加三块同种金属锭，锭的种类由你挑。")
        TEXT("对准铺里的铸造台按 E，挑锻钢双手剑。第一把可以用刚炼好的三块铁锭，选好后点「开始锻造」。");
}

inline const TCHAR* Hammering()
{
    return TEXT("剑坯一亮蓝圈，就把白圈挪过去，点左键落锤。")
        TEXT("一炉有二十处落点，锤锤命中能多 15%。")
        TEXT("你得亲手敲到剑坯，这炉才算修炼。没敲准蓝圈也别慌，下一锤再来！");
}

inline const TCHAR* Finish()
{
    return TEXT("等剑淬好，回铸造台点「领取成品」。")
        TEXT("你亲手打的第一把锻钢双手剑，当然归你，这就算出师了！")
        TEXT("要是决定拆掉重打，每种用过的料能收回一半，零头舍去。");
}
}
