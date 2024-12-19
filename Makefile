.PHONY: install

install:
	docker pull ghcr.io/open-webui/open-webui:main

run:
	docker run -d -p 3000:8080 -v local:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main