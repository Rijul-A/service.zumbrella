import xbmc

from logger import Logger


class Monitor( xbmc.Monitor, Logger ):
    def __init__( self, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.log( 'Instantiating monitor' )
        self.reloadAction = kwargs.get( 'reloadAction' )
        self.screensaverAction = kwargs.get( 'screensaverAction' )
        self.descreensaverAction = kwargs.get( 'descreensaverAction' )
        self.notificationAction = kwargs.get( 'notificationAction' )

    def onScreensaverActivated( self ):
        self.log( 'onScreensaverActivated' )
        if self.screensaverAction:
            self.screensaverAction()

    def onScreensaverDeactivated( self ):
        self.log( 'onScreensaverDeactivated' )
        if self.descreensaverAction:
            self.descreensaverAction()

    def onSettingsChanged( self ):
        if self.reloadAction:
            self.reloadAction()

    def onNotification( self, sender, method, data ):
        if sender == 'xbmc' and method == 'GUI.OnDPMSActivated':
            if self.screensaverAction:
                self.screensaverAction()
        else:
            if self.notificationAction:
                self.notificationAction( sender, method, data )
