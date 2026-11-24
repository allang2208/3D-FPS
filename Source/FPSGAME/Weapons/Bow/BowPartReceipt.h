#pragma once
#include "../GunsmithSystem.h"

namespace BowPartReceipt
{
inline bool CanMerge(const UGunsmithSystem& Catalog,const FString& Bow,const FString& Slot,const FString& Before,const FString& After)
{
    if(Before==After)return false;
    const auto* Old=Catalog.Option(Bow,Slot,Before);
    const auto* New=Catalog.Option(Bow,Slot,After);
    return Old&&New&&Old->RequiredItem.IsEmpty()&&New->RequiredItem.IsEmpty();
}
}
