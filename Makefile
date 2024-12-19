.PHONY: install

install:
	docker pull ghcr.io/open-webui/open-webui:cuda

run:
	docker run -d -p 3000:8080 --gpus all -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:cuda

stop:
	docker stop open-webui
	docker rm open-webui