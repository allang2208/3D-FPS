#pragma once

// No gameplay operations here: choosing/confirming a project must never start its timer.
namespace WoodworkingEntry
{
enum class EScreen {Closed,Selection,Preparing,Workshop};
class FFlow
{
public:
    bool Open(){if(Screen!=EScreen::Closed)return false;Screen=EScreen::Selection;return true;}
    bool Confirm(){if(Screen!=EScreen::Selection)return false;Screen=EScreen::Preparing;return true;}
    bool Prepared(){if(Screen!=EScreen::Preparing)return false;Screen=EScreen::Workshop;return true;}
    bool Back(){if(Screen!=EScreen::Preparing&&Screen!=EScreen::Workshop)return false;Screen=EScreen::Selection;return true;}
    bool Close(){if(Screen==EScreen::Closed)return false;Screen=EScreen::Closed;return true;}
    bool Selecting() const {return Screen==EScreen::Selection;}
    bool Preparing() const {return Screen==EScreen::Preparing;}
    bool InWorkshop() const {return Screen==EScreen::Workshop;}
    bool Closed() const {return Screen==EScreen::Closed;}
private:
    EScreen Screen=EScreen::Closed;
};
}
