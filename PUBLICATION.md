# Publication Guide

## Current State

`python-drmanhattan` is structured as a standalone PyPI package.

Current coordinates:

- package: `python-drmanhattan`
- version: `0.1.2`
- repository: `github.com/animalab-netizen/python-drmanhattan`

## Distribution Model

The package is intended for:

- direct PyPI distribution as the public Python DrManhattan runtime
- consumption by validation projects and service-side examples
- installation without any private registry requirement

## Installation

```bash
pip install python-drmanhattan
```

## Release Checklist

1. Run `python3 -m unittest discover tests`
2. Build a wheel with `python3 -m pip wheel . --no-build-isolation --no-deps -w /tmp/python-drmanhattan-dist`
3. Update `CHANGELOG.md`
4. Confirm version in `pyproject.toml`
5. Commit release metadata
6. Create and push tag `v0.1.2`
7. Publish with the correct PyPI owner credentials
