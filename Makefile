REBUILD_FLAG =
VENV=env
BIN=$(VENV)/bin
ACTIVATE=source $(BIN)/activate

.PHONY: all
all: test build

$(VENV): $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	test -d $(VENV) || virtualenv -p /usr/bin/python3 $(VENV)
	$(ACTIVATE); pip install -r requirements.txt
	touch $(BIN)/activate


.PHONY: test
test: $(VENV)
	$(ACTIVATE); tox $(REBUILD_FLAG)

dist/*.whl: setup.py httpupload/*.py
	python setup.py bdist_wheel

dist/*.tar.gz: setup.py httpupload/*.py
	python setup.py sdist bdist

.PHONY: wheel
wheel: dist/*.whl

.PHONY: dist
dist: dist/*.tar.gz

.PHONY: build
build: wheel dist

.PHONY: upload
upload: clean
	python setup.py sdist bdist bdist_wheel upload

.PHONY: clean
clean:
	find . -iname '*.pyc' | xargs rm -f
	find . -iname '__pycache__' -type d | xargs rm -rf
	rm -rf .tox
	rm -rf build
	rm -rf dist
	rm -rf $(VENV)
