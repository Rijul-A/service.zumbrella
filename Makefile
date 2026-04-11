.PHONY: all package clean

ZIP_NAME ?= service.zumbrella.zip

all: package

package:
	zip -r $(ZIP_NAME) . -x '*.git*' -x 'bravia_server.py' -x 'media_launcher.sh' -x '$(ZIP_NAME)'

clean:
	rm -f $(ZIP_NAME)
