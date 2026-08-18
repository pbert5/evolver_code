"""Hardware access and commissioning for min-eVOLVER devices.

The public API is deliberately transport-independent: ``LocalSerialBackend`` is
the bring-up backend, while a future hardwared client can implement the same
``HardwareBackend`` protocol and retain exclusive serial-port ownership.
"""

from .model import HardwareTestResult, TestStatus
from .service import HardwareTester, LocalSerialBackend

__all__ = ["HardwareTestResult", "TestStatus", "HardwareTester", "LocalSerialBackend"]
