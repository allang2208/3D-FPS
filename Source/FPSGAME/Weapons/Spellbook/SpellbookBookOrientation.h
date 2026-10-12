#pragma once
#include "SpellbookAuthoredGrip.h"
#include "SpellbookAuthoredOpening.h"

namespace SpellbookBookOrientation
{
// Reverse the book's top/bottom around its spine-to-edge axis. The grip
// origin, occupied closed-book volume and every arm key remain unchanged.
inline const FTransform HalfTurn(FQuat(1,0,0,0));
inline FTransform InHand() { return HalfTurn*SpellbookAuthoredGrip::BookInHand; }
inline FTransform ReadingSurface()
{
    // V27 root tracks conjugate the V24 alignment by HalfTurn. The open
    // surface keeps its position/normal, with its printed top reversed.
    return FTransform(FQuat(0,0,1,0))*SpellbookAuthoredOpening::ReadingSurfaceInBook*HalfTurn;
}
}
