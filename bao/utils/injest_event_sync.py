import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


class InjestEventSync:
    def __init__(self, db_root: str, sqllite_local: str = ".sqllite.injest") -> None:
        self.db_root = db_root
        self.sqllite_local = sqllite_local
        with closing(sqlite3.connect(Path(db_root) / sqllite_local)) as conn:
            # Create a table (if it doesn't exist)
            conn.execute(
                """CREATE TABLE IF NOT EXISTS injest_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT,
                entry_name TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
            )
            conn.commit()

    def batch_insert_event(self, app_name: str, entry_names: List[str]) -> None:
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            query = f"SELECT entry_name FROM injest_events WHERE app_name = ? and entry_name in ({','.join(['?']*len(entry_names))})"
            cursor = conn.execute(query, (app_name, *entry_names))
            filtered_res = cursor.fetchall()
            cursor.close()
            existing_entries = [_[0] for _ in filtered_res]
            if filtered_res:
                logger.warning(f"({app_name}, {existing_entries}) alreay exists!")
            new_entries = set(entry_names) - set(existing_entries)
            if new_entries:
                new_recs = [(app_name, _) for _ in new_entries]
                conn.executemany(
                    "INSERT INTO injest_events (app_name, entry_name) VALUES (?, ?)",
                    new_recs,
                )
                conn.commit()

    def find_new_entries(self, app_name, entry_name_list: Iterable[str]) -> List[str]:
        """
        Find the existing entries according to the app_and and entry_names.
        And return the matched entry name list.
        """
        if not entry_name_list:
            return None  # type: ignore
        entry_name_list = list(set(entry_name_list))
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            query = f"SELECT entry_name FROM injest_events WHERE app_name = ? and entry_name in ({','.join(['?']*len(entry_name_list))})"
            cursor = conn.execute(query, (app_name, *entry_name_list))
            res = cursor.fetchall()
            cursor.close()
            existed = set([_[0] for _ in res])
            return list(set(entry_name_list) - existed)

    def is_exist_entry(self, app_name: str, entry_name: str) -> bool:
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            query = f"SELECT count(entry_name) as cnt FROM injest_events WHERE app_name = ? and entry_name = ?"
            cursor = conn.execute(query, (app_name, entry_name))
            res = cursor.fetchall()
            cursor.close()
            return res and res[0][0] > 0  # type: ignore

    def remove(self, app_name: str, entries: Iterable[str]) -> None:
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            entries = list(set(entries))
            query = f"DELETE FROM injest_events WHERE app_name = ? and entry_name in ({','.join(['?'] * len(entries))})"
            conn.execute(query, (app_name, *entries))
            conn.commit()

    def list_events(
        self, app_name, entry_name_like: Optional[str] = None
    ) -> List[List[str]]:
        """
        Find records by app_name and entry_name like entry_name_like.
        """
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            has_filter = entry_name_like is not None and entry_name_like.strip()
            if has_filter:
                filter = f"%{entry_name_like}%"
                query = f"SELECT entry_name FROM injest_events WHERE app_name = ? and entry_name like ? order by timestamp desc"
                cursor = conn.execute(query, (app_name, filter))
            else:
                query = f"SELECT entry_name FROM injest_events WHERE app_name = ?  order by timestamp desc"
                cursor = conn.execute(query, (app_name,))
            res = cursor.fetchall()
            cursor.close()
            return res
