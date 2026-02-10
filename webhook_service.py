import requests
import xbmc

from logger import Logger


class WebhookControl( Logger ):
    def __init__( self, url ):
        self.url = url.rstrip( '/' )

    def run( self, method ):
        if method == 'onScreensaverActivated':
            url = self.url + '/onScreensaverActivated'
        elif method == 'onScreensaverDeactivated':
            url = self.url + '/onScreensaverDeactivated'
        else:
            self.log( f'Invalid method: {method}', xbmc.LOGERROR )
            xbmc.executebuiltin(
                f'Notification(Zumbrella Warning, Invalid method: {method}, 5000)'
            )
            return None
        try:
            response = requests.get( url, timeout = 10 )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log( f'Error sending webhook to {url}: {e}', xbmc.LOGERROR )
            return None
