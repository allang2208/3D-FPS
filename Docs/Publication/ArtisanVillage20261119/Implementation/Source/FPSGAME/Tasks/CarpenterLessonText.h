#pragma once

#include "CoreTypes.h"

namespace CarpenterLessonText
{
inline const TCHAR* Quality()
{
    return TEXT("先做一把学徒长杖。")
        TEXT("木芯定底子，走锯干净，做成的杖就能多几分魔法攻击。")
        TEXT("换好芯、把边缘修准，木芯和加工加在一起，最高能多 25%。");
}

inline const TCHAR* Materials()
{
    return TEXT("两份木材，一枚原木芯，这份留给你。")
        TEXT("在一楼木工台选「法杖 · 学徒长杖」，装上原木芯，再开始加工。");
}

inline const TCHAR* Working()
{
    return TEXT("浅色是杖身，要留，先让红色虚线落在外面的废料上。")
        TEXT("用 Q、E 转木板，按空格开锯，再按住左键慢慢送板。")
        TEXT("要换个角度就按空格停锯，稳了再走，别锯断连接处。");
}

inline const TCHAR* Finish()
{
    return TEXT("外圈清干净、杖身留完整，点「完成加工」看结果。")
        TEXT("等合格的长杖进了你的背包，这门手艺就算入门了。")
        TEXT("失手可以拆料重来，每种实付材料退一半，零头舍去。");
}
}
