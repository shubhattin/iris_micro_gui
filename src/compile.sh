#!/usr/bin/env bash

# confirm

rm -rf dist build
pyinstaller main.py

# the __file__ seems to be pointing into _internal, thus
cp -r resources/ dist/main/_internal/resources
cd dist && tar -czf iris_micro_gui.tar.gz -C main $(ls main)