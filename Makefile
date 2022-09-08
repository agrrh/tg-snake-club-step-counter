build:
	docker build . -t local/step-counter:dev

publish_prod: build
	docker tag local/step-counter:dev agrrh/tg-step-counter:$$(git describe --tags --abbrev=0)
	docker push agrrh/tg-step-counter:$$(git describe --tags --abbrev=0)
	echo agrrh/tg-step-counter:$$(git describe --tags --abbrev=0)

publish_dev: build
	docker tag local/step-counter:dev agrrh/tg-step-counter:dev-$$(git rev-parse --short HEAD)
	docker push agrrh/tg-step-counter:dev-$$(git rev-parse --short HEAD)
	echo agrrh/tg-step-counter:dev-$$(git rev-parse --short HEAD)

seal:
	test -f kubernetes/config-dev.secret.yml \
	&& kubeseal --controller-name sealed-secrets -o yaml \
		< kubernetes/config-dev.secret.yml \
		> kubernetes/dev/config.sealedsecret.yml
	test -f kubernetes/config-prod.secret.yml \
	&& kubeseal --controller-name sealed-secrets -o yaml \
		< kubernetes/config-prod.secret.yml \
		> kubernetes/prod/config.sealedsecret.yml

apply_dev:
	kubectl apply -R -f kubernetes/dev/

apply_prod:
	kubectl apply -R -f kubernetes/prod/
