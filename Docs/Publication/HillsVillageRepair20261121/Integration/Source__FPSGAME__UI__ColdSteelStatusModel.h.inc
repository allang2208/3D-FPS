// Source/FPSGAME/UI/ColdSteelStatusModel.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 296-296 | class FPSGAME_API UColdSteelStatusModel : public UGameInstanceSubsystem
    bool TakeInteractionNotice(FColdSteelProgressNotice& Out);

// Lines 444-444 | class FPSGAME_API UColdSteelStatusModel : public UGameInstanceSubsystem
    /** 普通交互共用一个即时反馈位置，新的结果覆盖尚未显示的旧结果。 */

// Lines 681-682 | class FPSGAME_API UColdSteelStatusModel : public UGameInstanceSubsystem
    TOptional<FColdSteelProgressNotice> PendingInteractionNotice;
    double InteractionNoticeExpiresAt=0.;
