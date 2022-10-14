from kodi_six import xbmcgui


class CustomDialog( xbmcgui.WindowXMLDialog ):
    ACTION_PLAYER_STOP = 13
    ACTION_NAV_BACK = 92

    __INVALID_BUTTON_ID__ = -1
    __LEFT_BUTTON_ID__ = 3012
    __MIDDLE_BUTTON_ID__ = 3014
    __RIGHT_BUTTON_ID__ = 3013
    __PERCENT_CONTROL_ID__ = 3015

    __STRING_PLAY__ = 32036
    __STRING_PAUSE__ = 32037

    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
        self.lastControlClicked = CustomDialog.__INVALID_BUTTON_ID__
        self.onClickCallback = kwargs.get( 'onClick' )
        self.visible = False

    def onInit( self ):
        self.percentControl = self.getControl(
            CustomDialog.__PERCENT_CONTROL_ID__
        )

    def set_label( self, label ):
        self.setProperty( 'label', label )

    def update_progress( self, percent ):
        try:
            self.percentControl.setPercent( round( percent * 100, 0 ) )
        except AttributeError:
            pass

    def set_left_button_text( self, text ):
        # according to the docs, Python API is not complete
        # so you can't instantitate a ControlButton and use `setLabel`
        self.setProperty( 'left_button_label', text )

    def onClick( self, controlId ):
        self.lastControlClicked = controlId
        if self.onClickCallback:
            self.onClickCallback( controlId )

    def onAction( self, action ):
        if action in [
            CustomDialog.ACTION_PLAYER_STOP,
            CustomDialog.ACTION_NAV_BACK
        ]:
            self.close()

    def close( self ):
        self.visible = False
        return super( xbmcgui.WindowXMLDialog, self ).close()

    def show( self ):
        self.visible = True
        return super( xbmcgui.WindowXMLDialog, self ).show()
