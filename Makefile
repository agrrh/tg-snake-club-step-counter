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

publish: build
	docker tag local/step-counter:dev agrrh/tg-step-counter:$$(git describe --tags --abbrev=0)
	docker push agrrh/tg-step-counter:$$(git describe --tags --abbrev=0)

seal:
	test -f kubernetes/config.secret.yml \
	&& kubeseal --controller-name sealed-secrets -o yaml \
		< kubernetes/config.secret.yml \
		> kubernetes/config.sealedsecret.yml

apply: seal
	kubectl apply -f kubernetes/namespace.yml
	kubectl apply -f kubernetes/config.sealedsecret.yml
	kubectl apply -R -f kubernetes/reminder/
	kubectl apply -R -f kubernetes/webhook/
