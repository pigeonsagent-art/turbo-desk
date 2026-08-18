"""
Secure Wiper - Overwrites files with random data before deletion (DoD 5220.22-M style).
Supports 1-pass, 3-pass, and 7-pass modes.  Also supports drive free-space wiping.
"""
import os
import sys
import struct
import secrets
from pathlib import Path
from typing import Callable, Optional, List, Tuple


PASS_PATTERNS = {
    1: [(None,)],          # 1 random pass
    3: [(0x00,), (0xFF,), (None,)],
    7: [(0x00,), (0xFF,), (None,), (0x92,), (0x49,), (0x24,), (None,)],
}


class SecureWiper:
    def __init__(self, passes: int = 3):
        self.passes = passes if passes in PASS_PATTERNS else 3
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    # ------------------------------------------------------------------ #
    # Wipe a single file
    # ------------------------------------------------------------------ #
    def wipe_file(
        self,
        filepath: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        if not os.path.isfile(filepath):
            return False
        try:
            file_size = os.path.getsize(filepath)
            patterns = PASS_PATTERNS[self.passes]
            with open(filepath, "r+b") as f:
                for pass_num, (pattern,) in enumerate(patterns, 1):
                    if self._cancelled:
                        return False
                    f.seek(0)
                    written = 0
                    chunk = 65536
                    while written < file_size:
                        if self._cancelled:
                            return False
                        to_write = min(chunk, file_size - written)
                        if pattern is None:
                            data = secrets.token_bytes(to_write)
                        else:
                            data = bytes([pattern]) * to_write
                        f.write(data)
                        written += to_write
                        if progress_cb:
                            progress_cb(pass_num, written)
                    f.flush()
                    os.fsync(f.fileno())

            # Rename to random name before delete to obscure original filename
            parent = os.path.dirname(filepath)
            random_name = os.path.join(parent, secrets.token_hex(8))
            os.rename(filepath, random_name)
            os.remove(random_name)
            return True
        except (OSError, PermissionError):
            return False

    # ------------------------------------------------------------------ #
    # Wipe multiple files
    # ------------------------------------------------------------------ #
    def wipe_files(
        self,
        filepaths: List[str],
        progress_cb: Optional[Callable[[str, int, int], None]] = None,
    ) -> Tuple[int, int]:
        wiped = 0
        failed = 0
        for fp in filepaths:
            if self._cancelled:
                break
            if self.wipe_file(fp):
                wiped += 1
            else:
                failed += 1
            if progress_cb:
                progress_cb(fp, wiped, failed)
        return wiped, failed

    # ------------------------------------------------------------------ #
    # Wipe a folder recursively
    # ------------------------------------------------------------------ #
    def wipe_folder(
        self,
        folder: str,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Tuple[int, int]:
        files = []
        for root, _dirs, filenames in os.walk(folder):
            for fname in filenames:
                files.append(os.path.join(root, fname))
        wiped, failed = self.wipe_files(files, None)
        # Remove now-empty directory tree
        import shutil
        try:
            shutil.rmtree(folder, ignore_errors=True)
        except Exception:
            pass
        return wiped, failed

    # ------------------------------------------------------------------ #
    # Wipe free space on a drive
    # ------------------------------------------------------------------ #
    def wipe_free_space(
        self,
        drive: str,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Fill free space with zeros then delete the filler file."""
        import shutil
        filler = os.path.join(drive, "__pcpolish_wipe_temp__.dat")
        chunk = 1024 * 1024  # 1 MB chunks
        try:
            written = 0
            with open(filler, "wb") as f:
                while True:
                    if self._cancelled:
                        break
                    free = shutil.disk_usage(drive).free
                    if free < chunk:
                        break
                    f.write(b"\x00" * chunk)
                    written += chunk
                    if progress_cb:
                        progress_cb(written)
            os.remove(filler)
            return True
        except (OSError, PermissionError):
            try:
                os.remove(filler)
            except Exception:
                pass
            return False

    @staticmethod
    def get_pass_descriptions() -> dict:
        return {
            1: "Quick (1 pass – random overwrite)",
            3: "Standard (3 passes – DoD basic)",
            7: "Advanced (7 passes – DoD 5220.22-M)",
        }
