# Vedro Unittest

[![Codecov](https://img.shields.io/codecov/c/github/vedro-universe/vedro-unittest/main.svg?style=flat-square)](https://codecov.io/gh/vedro-universe/vedro-unittest)
[![PyPI](https://img.shields.io/pypi/v/vedro-unittest.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-unittest/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vedro-unittest?style=flat-square)](https://pypi.python.org/pypi/vedro-unittest/)
[![Python Version](https://img.shields.io/pypi/pyversions/vedro-unittest.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-unittest/)

[vedro-unittest](https://pypi.org/project/vedro-unittest/) allows running unittest test cases within the Vedro framework. This plugin seamlessly integrates unittest test cases, converting them into Vedro scenarios to leverage the powerful features of the Vedro testing framework.

## Installation

<details open>
<summary>Quick</summary>
<p>

For a quick installation, you can use a plugin manager as follows:

```shell
$ vedro plugin install vedro-unittest
```

</p>
</details>

<details>
<summary>Manual</summary>
<p>

To install manually, follow these steps:

1. Install the package using pip:

```shell
$ pip3 install vedro-unittest
```

2. Next, activate the plugin in your `vedro.cfg.py` configuration file:

```python
# ./vedro.cfg.py
import vedro
import vedro_unittest

class Config(vedro.Config):

    class Plugins(vedro.Config.Plugins):

        class VedroUnitTest(vedro_unittest.VedroUnitTest):
            enabled = True
```

</p>
</details>

## Usage

To use the plugin, create your unittest test cases as usual:

```python
# ./scenarios/test_base64.py
import unittest
from base64 import b64encode, b64decode

class TestBase64Encoding(unittest.TestCase):
    def test_encode_banana_to_base64(self):
        result = b64encode(b"banana")
        self.assertEqual(result, b"YmFuYW5h")

    def test_decode_banana_from_base64(self):
        result = b64decode(b"YmFuYW5h")
        self.assertEqual(result, b"banana")
```

Then run your tests using Vedro:

```shell
$ vedro run
```

This will automatically detect and run your unittest test cases as Vedro scenarios, allowing you to take advantage of Vedro's rich feature set.
