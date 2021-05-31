# =======
# General
# =======
# - `make tests` runs all the unit-tests using tox and pytest
# - `make build` creates environment, runs tests, and builds the package
# - `make clean` deletes all the build artifacts

tests: env test fmt clean
.phony: tests

build: env package
.phony: build


# ---------------------  build env --------------------#

env:
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pip install -r requirements.txt
	pip install -e .
.PHONY: env

# ---------------------  run tests --------------------#

test:
	@tox --recreate -e test --develop
.PHONY: test

fmt:
	@tox -e fmt --develop
.PHONY: fmt

# ----------------  Build the package  ----------------#

package:
	# build the wheel
	rm -rf *.egg-info build
	python3 setup.py bdist_wheel
	#python3 setup.py sdist
	# Creation a zip with all packages
#	pip install -r requirements.txt -t ./build
#	mkdir ./build/sec-manager/
#	find . -name '__pycache__' -exec rm -fr {} +
#	cp ./src/* ./build/sec-manager && rm -rf ./build/lib && rm -rf ./build/bdist.macosx-*
#	$(eval VERSION = $(shell python -c 'from src.__version__ import __version__; print(__version__)'))
#	cd ./build/ && zip -r ../dist/dapspark-$(VERSION)-packages.zip .
.PHONY: package

# ----------------  Clean the project and Dev Env ----------------#

TO_CLEAN  = build pip-wheel-metadata/

clean:
	rm -rf ${TO_CLEAN}
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '*.xml' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -rf Pipfile.lock \
		   ~/.cache/pip \
		   ~/.cache/pipenv \
		   .pytest_cache/ \
		   pytest.log \
		   .coverage \
		   coverage \
	       htmlcov/ \
	       .tox
.PHONY: clean
