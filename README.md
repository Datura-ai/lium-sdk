# Lium SDK

A Python SDK for interacting with the Lium API.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [License](#license)
- [Changelog](#changelog)
- [Support](#support)

## Installation

```bash
pip install .
```

## Usage

```python
import lium

with lium.Client(api_key="your-key") as client:
    pods = client.pods.list()
```

## Development

To set up the development environment, clone the repository and install the dependencies:

```bash
git clone https://github.com/your-username/lium-sdk.git
cd lium-sdk
pip install -e .
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Changelog

All notable changes to this project will be documented in the [CHANGELOG.md](CHANGELOG.md) file.

## Support

If you have any issues or questions, please open an issue on GitHub.