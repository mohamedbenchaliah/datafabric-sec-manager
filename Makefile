.PHONY: target dev format lint test coverage-html pr build
.PHONY: security-baseline complexity-baseline release-prod release-test release clean

target:
	@$(MAKE) pr

dev:
	pip install --upgrade pip pre-commit poetry==1.1.4
	poetry install --extras "pydantic"
	pre-commit install

format:
	poetry run isort sec_manager tests
	poetry run black sec_manager tests

lint: format
	poetry run flake8 sec_manager/* tests/*

test:
	poetry run pytest -m "not perf" --cov=sec_manager --cov-report=xml

coverage-html:
	poetry run pytest -m "not perf" --cov=sec_manager --cov-report=html

pre-commit:
	pre-commit run --show-diff-on-failure

pr: lint test security-baseline complexity-baseline
#pr: lint pre-commit test security-baseline complexity-baseline

build: pr
	poetry build

security-baseline:
	poetry run bandit --baseline bandit.baseline -r sec_manager

complexity-baseline:
	$(info Maintenability index)
	poetry run radon mi sec_manager
	$(info Cyclomatic complexity index)
	poetry run xenon --max-absolute C --max-modules A --max-average A sec_manager


clean:
	rm -rf ${TO_CLEAN}
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -rf Pipfile.lock \
		   ~/.cache/pip \
		   ~/.cache/pipenv \
		   .pytest_cache/ \
		   pytest.log \
		   .coverage \
	       htmlcov/ \
	       .tox

# Use `poetry version <major>/<minor></patch>` for version bump

release-prod:
	poetry config pypi-token.pypi ${PYPI_TOKEN}
	poetry publish -n

release-test:
	poetry config repositories.testpypi https://test.pypi.org/legacy
	poetry config pypi-token.pypi ${PYPI_TEST_TOKEN}
	poetry publish --repository testpypi -n

release: pr
	poetry build
#	$(MAKE) release-test
#	$(MAKE) release-prod

changelog:
	 @echo "[+] Pre-generating CHANGELOG for tag: $$(git describe --abbrev=0 --tag)"
	 docker run -v ${PWD}:/workdir quay.io/git-chglog/git-chglog $$(git describe --abbrev=0 --tag).. -o TMP_CHANGELOG.md
