# 文件说明（中文）：第三方库兼容层，处理 bleak/toio 在 Windows 下的版本差异。
# File Description (EN): Compatibility layer for third-party libs on Windows (bleak/toio version differences).

def apply_bleak_winrt_compat() -> None:
    """
    Compatibility shim for toio.py 1.1.0 + bleak 2.x on Windows.
    toio imports "_RawAdvData", but bleak 2.x exposes "RawAdvData".
    """
    try:
        from bleak.backends.winrt import scanner as _winrt_scanner

        if not hasattr(_winrt_scanner, "_RawAdvData") and hasattr(
            _winrt_scanner, "RawAdvData"
        ):
            _winrt_scanner._RawAdvData = _winrt_scanner.RawAdvData
    except Exception:
        pass
