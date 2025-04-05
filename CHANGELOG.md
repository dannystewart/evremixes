# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [1.0.6] (2025-04-04)

### Changed

- Updates import statements across multiple modules (`MenuHelper` and `TrackDownloader`) to use `polykit` instead of older dependencies like `textparse` and `shelper`.
- Updates `pyproject.toml` to include the latest dependency versions.
- Updates `poetry.lock` with new package versions and adds `polykit`.
- Updates `ruff.toml` with a newer config version and adjusted section names.

## [1.0.5] (2025-04-02)

### Added

- Adds a quit option to the version selection prompt in `MenuHelper`.

### Changed

- Updates dependencies in `pyproject.toml` to the latest compatible versions.

<!-- Links -->
[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[unreleased]: https://github.com/dannystewart/evremixes/compare/v1.0.6...HEAD
[1.0.6]: https://github.com/dannystewart/evremixes/releases/tag/v1.0.6
[1.0.5]: https://github.com/dannystewart/evremixes/compare/v1.0.6...v1.0.5
