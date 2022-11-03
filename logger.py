from kodi_six import xbmc

__PLUGIN_ID__ = 'service.zumbrella'
__PLUGIN_VERSION__ = 'v0.0.5-matrix'


class Logger:
    LOG_MODE = xbmc.LOGINFO

    def __init__( self, tag ):
        self.tag = tag or self.__class__.__name__

    def log( self, msg, mode = None ):
        # allow for mode overrides
        mode = mode or Logger.LOG_MODE
        xbmc.log(
            "[{}_{}]: {} - {}".format(
                __PLUGIN_ID__,
                __PLUGIN_VERSION__,
                self.tag if hasattr( self,
                                     'tag' ) else self.__class__.__name__,
                msg
            ),
            mode
        )

    @staticmethod
    def set_log_mode( mode ):
        Logger.LOG_MODE = mode
