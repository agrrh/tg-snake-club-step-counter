build:
	docker build . -t local/step-counter:dev

run_reminder: build
	docker run --rm -ti \
		--env-file dev.env \
		-v $$(pwd)/config:/opt/app/config:ro \
		local/step-counter:dev bot_reminder.py

run_webhook: build
	docker run --rm -ti \
		--env-file dev.env \
		-v $$(pwd)/config:/opt/app/config:ro \
		local/step-counter:dev bot_webhook.py
