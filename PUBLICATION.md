# Publication Guide

## Current State

`python-drmanhatan` is structured as a standalone PyPI package.

Current coordinates:

- package: `python-drmanhatan`
- version: `0.1.1`
- repository: `github.com/animalab-netizen/python-drmanhatan`

## Distribution Model

The package is intended for:

- direct PyPI distribution as the public Python DrManhatan runtime
- consumption by validation projects and service-side examples
- installation without any private registry requirement

## Installation

```bash
pip install python-drmanhatan
```

## Release Checklist

1. Run `python3 -m unittest discover tests`
2. Build a wheel with `python3 -m pip wheel . --no-build-isolation --no-deps -w /tmp/python-drmanhatan-dist`
3. Update `CHANGELOG.md`
4. Confirm version in `pyproject.toml`
5. Commit release metadata
6. Create and push tag `v0.1.1`
7. Publish with the correct PyPI owner credentials
