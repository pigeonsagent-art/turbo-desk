"""
Browser Cleaner - Cleans cache, history, cookies, downloads list,
saved passwords, autofill data, and session data for Chrome, Firefox, and Edge.
"""
import os
import shutil
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


BROWSERS: Dict[str, Dict] = {
    "Google Chrome": {
        "base": str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"),
        "profiles": ["Default", "Profile 1", "Profile 2", "Profile 3"],
        "cache_dirs": ["Cache", "Code Cache", "GPUCache", "Media Cache", "ShaderCache"],
        "data_files": {
            "History": "History",
            "Cookies": "Cookies",
            "Favicons": "Favicons",
            "Login Data": "Login Data",
            "Web Data": "Web Data",
            "Visited Links": "Visited Links",
            "Last Session": "Last Session",
            "Last Tabs": "Last Tabs",
            "Top Sites": "Top Sites",
        },
    },
    "Microsoft Edge": {
        "base": str(Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"),
        "profiles": ["Default", "Profile 1", "Profile 2"],
        "cache_dirs": ["Cache", "Code Cache", "GPUCache", "Media Cache"],
        "data_files": {
            "History": "History",
            "Cookies": "Cookies",
            "Login Data": "Login Data",
            "Web Data": "Web Data",
            "Visited Links": "Visited Links",
        },
    },
    "Mozilla Firefox": {
        "base": str(Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"),
        "profiles": [],  # dynamic
        "cache_base": str(Path(os.environ.get("LOCALAPPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"),
        "cache_dirs": ["cache2"],
        "data_files": {
            "Places (History/Bookmarks)": "places.sqlite",
            "Cookies": "cookies.sqlite",
            "Form History": "formhistory.sqlite",
            "Session Store": "sessionstore.jsonlz4",
            "Downloads": "downloads.sqlite",
        },
    },
    "Opera GX": {
        "base": str(Path(os.environ.get("APPDATA", "")) / "Opera Software" / "Opera GX Stable"),
        "profiles": [""],
        "cache_dirs": ["Cache", "Code Cache", "GPUCache"],
        "data_files": {
            "History": "History",
            "Cookies": "Cookies",
        },
    },
}


class BrowserCleaner:
    def __init__(self):
        self.scan_results: Dict = {}
        self.cookie_whitelist: List[str] = self._load_whitelist()

    # ------------------------------------------------------------------ #
    # Scanning
    # ------------------------------------------------------------------ #
    def scan(self) -> Dict:
        self.scan_results = {}
        for browser, cfg in BROWSERS.items():
            base = cfg["base"]
            if not os.path.exists(base):
                continue
            browser_data: Dict = {
                "cache": {"files": [], "size": 0},
                "history": {"files": [], "size": 0},
                "cookies": {"files": [], "size": 0},
                "other": {"files": [], "size": 0},
            }

            profiles = self._get_profiles(browser, cfg)

            for profile in profiles:
                profile_dir = os.path.join(base, profile) if profile else base
                if not os.path.isdir(profile_dir):
                    continue

                # Cache directories
                cache_base = cfg.get("cache_base", base)
                cache_root = os.path.join(cache_base, profile) if profile else cache_base
                for cd in cfg.get("cache_dirs", []):
                    cd_path = os.path.join(cache_root, cd)
                    if os.path.isdir(cd_path):
                        for root, _, files in os.walk(cd_path):
                            for f in files:
                                fp = os.path.join(root, f)
                                sz = self._safe_size(fp)
                                browser_data["cache"]["files"].append((fp, sz))
                                browser_data["cache"]["size"] += sz

                # Data files
                for label, filename in cfg.get("data_files", {}).items():
                    fp = os.path.join(profile_dir, filename)
                    if os.path.isfile(fp):
                        sz = self._safe_size(fp)
                        if "cookie" in label.lower() or "cookie" in filename.lower():
                            browser_data["cookies"]["files"].append((fp, sz))
                            browser_data["cookies"]["size"] += sz
                        elif "history" in label.lower() or "places" in filename.lower():
                            browser_data["history"]["files"].append((fp, sz))
                            browser_data["history"]["size"] += sz
                        else:
                            browser_data["other"]["files"].append((fp, sz))
                            browser_data["other"]["size"] += sz

            self.scan_results[browser] = browser_data
        return self.scan_results

    # ------------------------------------------------------------------ #
    # Cleaning
    # ------------------------------------------------------------------ #
    def clean(self, browser: str, clean_types: List[str]) -> Tuple[int, int]:
        """
        clean_types: list of 'cache', 'history', 'cookies', 'other'
        Returns (files_removed, bytes_freed)
        """
        if browser not in self.scan_results:
            return 0, 0
        count, freed = 0, 0
        for ctype in clean_types:
            for fp, sz in self.scan_results[browser].get(ctype, {}).get("files", []):
                if ctype == "cookies" and self._is_whitelisted_cookie(fp):
                    continue
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                        count += 1
                        freed += sz
                    elif os.path.isdir(fp):
                        shutil.rmtree(fp, ignore_errors=True)
                        count += 1
                        freed += sz
                except (OSError, PermissionError):
                    pass
        return count, freed

    def clean_on_browser_close(self, browser: str, clean_types: List[str]) -> bool:
        """Register auto-clean hook for when browser closes. Uses a scheduler flag file."""
        flag_dir = Path(os.environ.get("APPDATA", "")) / "PCPolish"
        flag_dir.mkdir(parents=True, exist_ok=True)
        flag_file = flag_dir / f"auto_clean_{browser.replace(' ', '_')}.json"
        config = {"browser": browser, "types": clean_types, "enabled": True}
        with open(flag_file, "w") as f:
            json.dump(config, f)
        return True

    # ------------------------------------------------------------------ #
    # Cookie Whitelist
    # ------------------------------------------------------------------ #
    def _load_whitelist(self) -> List[str]:
        wl_path = Path(os.environ.get("APPDATA", "")) / "PCPolish" / "cookie_whitelist.json"
        if wl_path.exists():
            try:
                with open(wl_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_whitelist(self, whitelist: List[str]):
        wl_dir = Path(os.environ.get("APPDATA", "")) / "PCPolish"
        wl_dir.mkdir(parents=True, exist_ok=True)
        with open(wl_dir / "cookie_whitelist.json", "w") as f:
            json.dump(whitelist, f)
        self.cookie_whitelist = whitelist

    def get_browser_cookies(self, browser: str) -> List[Tuple[str, str, str]]:
        """Read cookies from browser (domain, name, expires). Chrome/Edge only."""
        cookies = []
        cfg = BROWSERS.get(browser)
        if not cfg:
            return cookies
        profiles = self._get_profiles(browser, cfg)
        for profile in profiles:
            profile_dir = os.path.join(cfg["base"], profile) if profile else cfg["base"]
            cookie_db = os.path.join(profile_dir, "Cookies")
            if not os.path.isfile(cookie_db):
                continue
            # Copy db to temp to avoid lock issues
            tmp = cookie_db + ".tmp_read"
            try:
                shutil.copy2(cookie_db, tmp)
                conn = sqlite3.connect(tmp)
                cur = conn.cursor()
                cur.execute("SELECT host_key, name, expires_utc FROM cookies LIMIT 500")
                for row in cur.fetchall():
                    cookies.append(row)
                conn.close()
            except Exception:
                pass
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        return cookies

    def _is_whitelisted_cookie(self, filepath: str) -> bool:
        if not self.cookie_whitelist:
            return False
        # Only partial match – for domain-level whitelist we'd need db manipulation
        return any(domain in filepath for domain in self.cookie_whitelist)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_profiles(browser: str, cfg: Dict) -> List[str]:
        if browser == "Mozilla Firefox":
            base = cfg["base"]
            if os.path.isdir(base):
                return [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
            return []
        return cfg.get("profiles", ["Default"])

    @staticmethod
    def _safe_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    @staticmethod
    def get_installed_browsers() -> List[str]:
        return [b for b, cfg in BROWSERS.items() if os.path.exists(cfg["base"])]
