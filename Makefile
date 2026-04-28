.PHONY: all package clean

ADDON_NAME = service.zumbrella
ZIP_NAME ?= $(ADDON_NAME).zip

all: package

package: clean
	zip -r $(ZIP_NAME) . -x '*.git*' -x 'bravia_server.py' -x 'media_launcher.sh' -x '$(ZIP_NAME)'

clean:
	rm -f $(ZIP_NAME)
