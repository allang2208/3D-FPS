#pragma once
#include "CoreMinimal.h"
#include "LMGStabilityGrip.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

// Extends the existing opt-in wrist review, never a gameplay branch.
namespace LMGGripReview
{
inline bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("LMGGripReview"));}
inline FString Definition(int32 Case)
{return Case<4?TEXT("ue_m249"):Case<6?TEXT("ue_lmg201"):TEXT("ue_pkm_lowpoly");}
inline FString Variant(int32 Case){return Case<2?TEXT("false"):LMGStabilityGrip::Id;}
inline FString Profile(int32 Case)
{return Case<2?LMGStabilityGrip::HandguardProfile:Case<4?TEXT("/Game/Weapons/M249/Bipod/DA_M249_SupportGrip"):LMGStabilityGrip::ProfilePath(Definition(Case));}
inline int32 Count(){return Enabled()?8:12;}
}
