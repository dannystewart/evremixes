# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

## [Unreleased]

## [1.0.13] (2025-12-06)

### Fixed

- Adds `urllib3` as explicit dependency to ensure it meets minimum version requirements.

## [1.0.12] (2025-12-06)

### Fixed

- Updates dependencies including `urllib3` to address security vulnerability.

## [1.0.11] (2025-06-25)

### Added

- **New track:** "Whisper" has been added to the collection as track 15.
- Adds preliminary privacy-respecting analytics to track remix downloads, preferences, and platform statistics. Also includes an analytics viewer script.

**NOTE:** The analytics feature is unfinished and does not currently do anything. *If* it's ever finished, it will be in a later release.

### Changed

- Updates collection release year from 2024 to 2025 now that a new track has been added.
- Updates multiple dependencies to their latest versions, including `urllib3` to address a security vulnerability, and removes `pygments` dependency.

### Fixed

- Updates tracklist URL from GitLab to GitHub raw file endpoint to ensure the script is fetching track information from the current repository location.

## [1.0.10] (2025-05-21)

### Changed

- Updates Poetry dependency from 2.1.2 to 2.1.3.
- Updates `polykit` dependency requirement from >=0.10.2 to >=0.11.1.

### Fixed

- Fixes import path for `handle_interrupt` from `polykit.shell` to `polykit.cli`.

## [1.0.9] (2025-04-05)

### Changed

- Updates `polykit` dependency to version 0.7.1, ensuring compatibility with the latest features and fixes.

## [1.0.8] (2025-04-05)

### Changed

- Updates `polykit` to version 0.7.0, including module imports to reflect renamed classes.
- Refactors configuration and logging to use the updated `polykit` API, improving maintainability and compatibility with updated dependencies.

## [1.0.7] (2025-04-04)

### Changed

- Minor dependency updates to `pyproject.toml` and `poetry.lock`.

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
[unreleased]: https://github.com/dannystewart/evremixes/compare/v1.0.13...HEAD
[1.0.13]: https://github.com/dannystewart/evremixes/compare/v1.0.12...v1.0.13
[1.0.12]: https://github.com/dannystewart/evremixes/compare/v1.0.11...v1.0.12
[1.0.11]: https://github.com/dannystewart/evremixes/compare/v1.0.10...v1.0.11
[1.0.10]: https://github.com/dannystewart/evremixes/compare/v1.0.9...v1.0.10
[1.0.9]: https://github.com/dannystewart/evremixes/compare/v1.0.8...v1.0.9
[1.0.8]: https://github.com/dannystewart/evremixes/compare/v1.0.7...v1.0.8
[1.0.7]: https://github.com/dannystewart/evremixes/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/dannystewart/evremixes/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/dannystewart/evremixes/releases/tag/v1.0.5
