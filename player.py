from kodi_six import xbmc


class Player( xbmc.Player ):
    def __init__( self, *args, **kwargs ):
        xbmc.Player.__init__( self )
        self.avStartedAction = kwargs.get( 'avStartedAction' )
        self.playBackPausedAction = kwargs.get( 'playBackPausedAction' )
        self.playBackResumedAction = kwargs.get( 'playBackResumedAction' )
        self.playBackEndedAction = kwargs.get( 'playBackEndedAction' )
        self.playBackErrorAction = kwargs.get( 'playBackErrorAction' )
        self.playBackStoppedAction = kwargs.get( 'playBackStoppedAction' )

    def onAVStarted( self ):
        if self.avStartedAction:
            self.avStartedAction()

    def onPlayBackPaused( self ):
        if self.playBackPausedAction:
            self.playBackPausedAction()

    def onPlayBackResumed( self ):
        if self.playBackResumedAction:
            self.playBackResumedAction()

    def onPlayBackEnded( self ):
        if self.playBackEndedAction:
            self.playBackEndedAction()

    def onPlayBackError( self ):
        if self.playBackErrorAction:
            self.playBackErrorAction()

    def onPlayBackStopped( self ):
        if self.playBackStoppedAction:
            self.playBackStoppedAction()
