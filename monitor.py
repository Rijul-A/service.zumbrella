from kodi_six import xbmc

import common


class Monitor( xbmc.Monitor ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.log( 'Instantiating monitor' )
        self.reloadAction = kwargs.get( 'reloadAction' )
        self.screensaverAction = kwargs.get( 'screensaverAction' )

    def onScreensaverActivated( self ):
        if self.screensaverAction:
            self.screensaverAction()

    def onSettingsChanged( self ):
        if self.reloadAction:
            self.reloadAction()

    def log( self, msg ):
        common.log( self.__class__.__name__, msg )
