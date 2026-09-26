"""Run ``python -m crc16_modbus_pure`` to execute the self-test."""

import sys

from .cli import main_self_test

if __name__ == "__main__":
    sys.exit(main_self_test())
