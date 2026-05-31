# How a (small) language model walks - local dev
#
# Quick start:
#   make          # serve the app and open it in your browser
#
# Other targets:
#   make serve    # same as `make`: run the local server (Ctrl-C to stop)
#   make build    # produce the static deploy build in out/site/
#   make deps     # install the one optional dependency (beautifulsoup4, URL tab only)
#   make clean    # remove the static build and Python caches

PORT := 8731
URL  := http://localhost:$(PORT)/

# Pick a browser-opener that exists on this platform (macOS: open, Linux: xdg-open).
OPEN := $(shell command -v open >/dev/null 2>&1 && echo open || echo xdg-open)

.PHONY: serve
serve:
	@echo "Serving $(URL)  (Ctrl-C to stop)"
	@# Open the browser shortly after the server comes up, then run the server
	@# in the foreground so Ctrl-C stops everything.
	@( sleep 1 ; $(OPEN) $(URL) >/dev/null 2>&1 || true ) &
	@python3 src/server.py

.PHONY: build
build:
	python3 src/build-static.py
	@echo "Static build written to out/site/"

.PHONY: deps
deps:
	python3 -m pip install beautifulsoup4

.PHONY: clean
clean:
	rm -rf out/site __pycache__ src/__pycache__ .ruff_cache .mypy_cache

# Default target: serve.
.DEFAULT_GOAL := serve
