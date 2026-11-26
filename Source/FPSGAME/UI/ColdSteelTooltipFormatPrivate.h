#pragma once
#include "ColdSteelItemTooltipData.h"
#include "Dom/JsonObject.h"

namespace ColdSteelTooltipPrivate
{
using J=TSharedPtr<FJsonObject>;
inline J Object(const J& O,const TCHAR* Key){const J* V=nullptr;return O&&O->TryGetObjectField(Key,V)?*V:nullptr;}
inline FString String(const J& O,const TCHAR* Key,const FString& Default=TEXT("")){FString V;return O&&O->TryGetStringField(Key,V)?V:Default;}
inline double Number(const J& O,const TCHAR* Key,double Default=0){double V;return O&&O->TryGetNumberField(Key,V)?V:Default;}
inline FString N(double V){FString S=FString::Printf(TEXT("%.2f"),V);while(S.EndsWith(TEXT("0")))S.LeftChopInline(1);if(S.EndsWith(TEXT(".")))S.LeftChopInline(1);return S==TEXT("-0")?TEXT("0"):S;}
inline FString Signed(double V,const TCHAR* Unit=TEXT("")){return (V>0?TEXT("+"):TEXT(""))+N(V)+Unit;}
inline void Row(FColdSteelTooltipCard& C,const FString& Label,const FString& Val,int32 Tone=0){if(!Val.IsEmpty())C.Rows.Add({Label,Val,Tone,false});}
inline void Note(FColdSteelTooltipCard& C,const FString& Label,const FString& Val,int32 Tone=0){if(Val.IsEmpty())return;C.Rows.Add({TEXT(""),Label.IsEmpty()?Val:Label+TEXT("：")+Val,Tone});}
TArray<FColdSteelTooltipRow> AppendCraftQuality(const FColdSteelItem& Item,UColdSteelStatusModel* Model,const J& Data,FColdSteelTooltipContent& Out);
}
