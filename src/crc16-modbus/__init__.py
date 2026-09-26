"""CRC-16/Modbus — pure-Python reference implementation.

Width: 16
Poly: 0x8005 (reflected = 0xA001)
Init: 0xFFFF
RefIn: True
RefOut: True
XorOut: 0x0000
Check (RevEng): 0x4B37 on ASCII "123456789"
"""

__version__ = "0.1.0"
