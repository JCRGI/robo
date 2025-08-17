class CoreError(Exception):
    pass


class ADBError(CoreError):
    pass


class EmulatorError(CoreError):
    pass


class OCRError(CoreError):
    pass
