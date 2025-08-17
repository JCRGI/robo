import unittest

from core.adb_manager import AdbManager


class TestAdbManager(unittest.TestCase):
    def test_connect_no_device(self):
        adb = AdbManager()
        try:
            adb.connect_device()
        except Exception as e:
            self.assertEqual(str(e), "Nenhum dispositivo conectado via ADB.")


if __name__ == "__main__":
    unittest.main()
