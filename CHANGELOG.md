# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-10

### Changed
- **BREAKING**: Complete API redesign for cleaner, Unix-style interface
- **BREAKING**: Removed `lium.Client` class, now use `from lium_sdk import Lium` directly
- **BREAKING**: Changed method signatures to be more pythonic
- Improved PEP 8 compliance throughout codebase
- Moved constants to module level
- Enhanced type hints with proper return types
- Simplified error handling and removed hacky fallbacks
- Consolidated duplicate code (ls() now uses _dict_to_executor_info)

### Fixed
- SSH port property now has proper error handling
- Template auto-selection now uses object attributes correctly
- Wait ready method now properly returns None instead of bare return

### Removed
- Removed demo() function in favor of inline __main__ code
- Removed backward compatibility for dict-based executors

## [0.1.3] - Previous Release

- Initial public release
- Basic pod management functionality