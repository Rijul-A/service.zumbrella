import xbmc
import xbmcgui

class CustomDialog(xbmcgui.WindowXMLDialog):
    ACTION_PLAYER_STOP = 13
    ACTION_NAV_BACK = 92

    __INVALID_BUTTON_ID__  = -1
    __LEFT_BUTTON_ID__     = 3012
    __MIDDLE_BUTTON_ID__   = 3014
    __RIGHT_BUTTON_ID__    = 3013
    __PERCENT_CONTROL_ID__ = 3015


    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.lastControlClicked = CustomDialog.__INVALID_BUTTON_ID__

    def onInit(self):
        self.percentControl = self.getControl(CustomDialog.__PERCENT_CONTROL_ID__)

    def set_label(self, label):
        self.setProperty('label', label)

    def update_progress(self, percent):
        self.percentControl.setPercent(round(percent * 100, 0))

    def onClick(self, controlId):
        self.lastControlClicked = controlId
        self.close()

    def reset(self):
        self.lastControlClicked = CustomDialog.__INVALID_BUTTON_ID__
        self.percentControl.setPercent(100)

    def onAction(self, action):
        if action in [CustomDialog.ACTION_PLAYER_STOP, CustomDialog.ACTION_NAV_BACK]:
            self.close()
            self.reset()
