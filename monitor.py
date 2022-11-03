from kodi_six import xbmc

from common import Logger


class Monitor( xbmc.Monitor, Logger ):
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

    def onNotification( self, sender, method, data ):
        if sender == 'plugin.video.jellyfin' and method == 'upnext_data':
            self.log( 'Received notification %s' % str( data ) )
