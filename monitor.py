import xbmc

from common import Logger


class Monitor( xbmc.Monitor, Logger ):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.log( 'Instantiating monitor' )
        self.reloadAction = kwargs.get( 'reloadAction' )
        self.screensaverAction = kwargs.get( 'screensaverAction' )

    def onScreensaverActivated( self ):
        self.log( 'onScreensaverActivated' )
        if self.screensaverAction:
            self.screensaverAction()

    def onSettingsChanged( self ):
        if self.reloadAction:
            self.reloadAction()

    def onNotification( self, sender, method, data ):
        self.log(
            "sender %s - method: %s  - data: %s" % ( sender,
                                                     method,
                                                     data )
        )
        # the opposite method is GUI.OnScreensaverDeactivated
        if sender == 'xbmc' and method == 'GUI.OnDPMSActivated':
            if self.screensaverAction:
                self.screensaverAction()
