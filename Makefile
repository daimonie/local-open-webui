.PHONY: install

install:
	docker pull ghcr.io/open-webui/open-webui:ollama

run:
	docker run -d -p 3000:8080 --gpus=all \
	--network=lantean-network \
	-v ollama:/root/.ollama -v open-webui:/app/backend/data \
	--name open-webui --restart always \
	ghcr.io/open-webui/open-webui:ollama

stop:
	docker stop open-webui
	docker rm open-webui

build-python:
	docker build -t local-ask-llm .

dev-python:
	docker run -v $(PWD)/container/:/opt/container \
	-v $(PWD)/open-webui/:/opt/container/data \
	--network=lantean-network \
	--memory=16g \
	--rm -ti --entrypoint=bash local-ask-llm