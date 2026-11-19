#pragma once

#include "CoreTypes.h"

namespace BlacksmithLessonText
{
inline const TCHAR* Quality()
{
    return TEXT("来，第一炉打把唐刀，料算我的！")
        TEXT("挑我架上的刀，看看「锻造伤害修正」。")
        TEXT("同是一把唐刀，有的比底子低 25%，有的能高出 5%。")
        TEXT("自己开炉，铁锭从原样起步，换金锭还能先添 10%。");
}

inline const TCHAR* Materials()
{
    return TEXT("一块锻造合金坯、两份木材、六块铁锭，我给你备齐了。")
        TEXT("对准铸造台按 E，挑唐刀，选铁锭，再点「开始锻造」。");
}

inline const TCHAR* Hammering()
{
    return TEXT("刀坯一亮蓝圈，就把白圈挪过去，点左键落锤。")
        TEXT("一炉有二十处落点，锤锤命中能多 15%。")
        TEXT("你得亲手敲到刀坯，这炉才算修炼。没敲准蓝圈也别慌，下一锤再来！");
}

inline const TCHAR* Finish()
{
    return TEXT("等刀淬好，回铸造台点「领取成品」。")
        TEXT("你亲手打的第一把唐刀，当然归你，这就算出师了！")
        TEXT("要是决定拆掉重打，每种用过的料能收回一半，零头舍去。");
}
}
