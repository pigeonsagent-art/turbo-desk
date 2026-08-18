"""
Cookie Manager - Read, display, and selectively delete browser cookies.
Supports a domain whitelist so important cookies survive cleaning.
"""
import os
import sys
import shutil
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone


WHITELIST_FILE = Path(os.environ.get("APPDATA", "")) / "PCPolish" / "cookie_whitelist.json"


class Cookie:
    def __init__(self, host: str, name: str, path: str, expires: int,
                 secure: bool, http_only: bool, browser: str, profile: str):
        self.host = host
        self.name = name
        self.path = path
        self.expires_raw = expires
        self.secure = secure
        self.http_only = http_only
        self.browser = browser
        self.profile = profile

    @property
    def domain(self) -> str:
        return self.host.lstrip(".")

    @property
    def expires_str(self) -> str:
        if not self.expires_raw:
            return "Session"
        try:
            # Chrome stores as microseconds since 1601-01-01
            if self.expires_raw > 11644473600000000:
                ts = (self.expires_raw - 11644473600000000) / 1_000_000
            else:
                ts = self.expires_raw
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return str(self.expires_raw)

    def __repr__(self):
        return f"Cookie({self.host}, {self.name})"


class CookieManager:
    BROWSER_COOKIE_PATHS = {
        "Google Chrome": {
            "base": str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"),
            "profiles": ["Default", "Profile 1", "Profile 2"],
            "db_name": "Cookies",
        },
        "Microsoft Edge": {
            "base": str(Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"),
            "profiles": ["Default", "Profile 1"],
            "db_name": "Cookies",
        },
    }

    def __init__(self):
        self.cookies: List[Cookie] = []
        self.whitelist: List[str] = self._load_whitelist()

    # ------------------------------------------------------------------ #
    # Load cookies from disk
    # ------------------------------------------------------------------ #
    def load_cookies(self, browser: str = "Google Chrome") -> List[Cookie]:
        self.cookies = []
        cfg = self.BROWSER_COOKIE_PATHS.get(browser)
        if not cfg:
            return []
        base = cfg["base"]
        if not os.path.exists(base):
            return []
        for profile in cfg["profiles"]:
            db_path = os.path.join(base, profile, cfg["db_name"])
            if not os.path.isfile(db_path):
                continue
            tmp = db_path + ".PCPolish_tmp"
            try:
                shutil.copy2(db_path, tmp)
                conn = sqlite3.connect(tmp)
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT host_key, name, path, expires_utc, is_secure, is_httponly "
                        "FROM cookies ORDER BY host_key"
                    )
                    for row in cur.fetchall():
                        host, name, path, expires, secure, http_only = row
                        self.cookies.append(Cookie(
                            host=host or "",
                            name=name or "",
                            path=path or "/",
                            expires=expires or 0,
                            secure=bool(secure),
                            http_only=bool(http_only),
                            browser=browser,
                            profile=profile,
                        ))
                except sqlite3.OperationalError:
                    # Different schema
                    try:
                        cur.execute("SELECT host_key, name, path, expires_utc, is_secure, httponly FROM cookies")
                        for row in cur.fetchall():
                            host, name, path, expires, secure, http_only = row
                            self.cookies.append(Cookie(
                                host=host or "", name=name or "", path=path or "/",
                                expires=expires or 0, secure=bool(secure), http_only=bool(http_only),
                                browser=browser, profile=profile,
                            ))
                    except Exception:
                        pass
                conn.close()
            except Exception:
                pass
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        return self.cookies

    # ------------------------------------------------------------------ #
    # Delete cookies
    # ------------------------------------------------------------------ #
    def delete_cookies(
        self,
        browser: str,
        domains_to_delete: Optional[List[str]] = None,
        preserve_whitelist: bool = True,
    ) -> Tuple[int, int]:
        """
        Delete cookies from browser databases.
        If domains_to_delete is None, deletes all except whitelisted.
        Returns (deleted_count, failed_count).
        """
        cfg = self.BROWSER_COOKIE_PATHS.get(browser)
        if not cfg:
            return 0, 0
        deleted = 0
        failed = 0
        for profile in cfg["profiles"]:
            db_path = os.path.join(cfg["base"], profile, cfg["db_name"])
            if not os.path.isfile(db_path):
                continue
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                if domains_to_delete:
                    for domain in domains_to_delete:
                        if preserve_whitelist and self._is_whitelisted(domain):
                            continue
                        try:
                            cur.execute("DELETE FROM cookies WHERE host_key LIKE ?", (f"%{domain}%",))
                            deleted += cur.rowcount
                        except Exception:
                            failed += 1
                else:
                    # Delete all non-whitelisted
                    if preserve_whitelist and self.whitelist:
                        placeholders = ",".join(["?" for _ in self.whitelist])
                        conditions = " AND ".join([f"host_key NOT LIKE ?" for _ in self.whitelist])
                        params = [f"%{d}%" for d in self.whitelist]
                        try:
                            cur.execute(f"DELETE FROM cookies WHERE {conditions}", params)
                            deleted += cur.rowcount
                        except Exception:
                            failed += 1
                    else:
                        try:
                            cur.execute("DELETE FROM cookies")
                            deleted += cur.rowcount
                        except Exception:
                            failed += 1
                conn.commit()
                conn.close()
            except Exception:
                failed += 1
        return deleted, failed

    # ------------------------------------------------------------------ #
    # Whitelist management
    # ------------------------------------------------------------------ #
    def get_whitelist(self) -> List[str]:
        return self.whitelist.copy()

    def add_to_whitelist(self, domain: str) -> bool:
        domain = domain.strip().lstrip(".")
        if domain and domain not in self.whitelist:
            self.whitelist.append(domain)
            self._save_whitelist()
            return True
        return False

    def remove_from_whitelist(self, domain: str) -> bool:
        if domain in self.whitelist:
            self.whitelist.remove(domain)
            self._save_whitelist()
            return True
        return False

    def _is_whitelisted(self, domain: str) -> bool:
        domain = domain.lstrip(".")
        return any(w.lstrip(".") in domain or domain in w for w in self.whitelist)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def get_unique_domains(self) -> List[str]:
        return sorted(set(c.domain for c in self.cookies))

    def filter_by_domain(self, domain: str) -> List[Cookie]:
        return [c for c in self.cookies if domain in c.host]

    def _load_whitelist(self) -> List[str]:
        if WHITELIST_FILE.exists():
            try:
                with open(WHITELIST_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return ["google.com", "github.com", "microsoft.com"]  # sensible defaults

    def _save_whitelist(self):
        WHITELIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WHITELIST_FILE, "w") as f:
            json.dump(self.whitelist, f, indent=2)
