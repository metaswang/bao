import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import List, Iterable

logger = logging.getLogger(__name__)


class InjestEventSync:
    def __init__(self, db_root: str, sqllite_local: str = ".sqllite.injest") -> None:
        self.db_root = db_root
        self.sqllite_local = sqllite_local
        with closing(sqlite3.connect(Path(db_root) / sqllite_local)) as conn:
            cursor = conn.cursor()
            # Create a table (if it doesn't exist)
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS injest_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT,
                entry_name TEXT UNIQUE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
            )

    def batch_insert_event(self, app_name: str, entry_names: List[str]) -> None:
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            cursor = conn.cursor()
            query = f"SELECT entry_name FROM injest_events WHERE app_name = ? and entry_name in ({','.join(['?']*len(entry_names))})"
            cursor.execute(query, (app_name, *entry_names))
            filtered_res = cursor.fetchall()
            cursor.close()
            existing_entries = [_[0] for _ in filtered_res]
            if filtered_res:
                logger.warning(f"({app_name}, {existing_entries}) alreay exists!")
            new_entries = set(entry_names) - set(existing_entries)
            new_recs = [(app_name, _) for _ in new_entries]
            cursor = conn.cursor()
            cursor.executemany(
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
            cursor = conn.cursor()
            query = f"SELECT entry_name FROM injest_events WHERE app_name = ? and entry_name in ({','.join(['?']*len(entry_name_list))})"
            cursor.execute(query, (app_name, *entry_name_list))
            res = cursor.fetchall()
            existed = set([_[0] for _ in res])
            return list(set(entry_name_list) - existed)

    def is_exist_entry(self, app_name: str, entry_name: str) -> bool:
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            cursor = conn.cursor()
            query = f"SELECT count(entry_name) as cnt FROM injest_events WHERE app_name = ? and entry_name = ?"
            cursor.execute(query, (app_name, entry_name))
            res = cursor.fetchall()
            return res and res[0][0] > 0  # type: ignore

    def remove(self, app_name: str, entries: Iterable[str]) -> None:
        with closing(sqlite3.connect(Path(self.db_root) / self.sqllite_local)) as conn:
            entries = list(set(entries))
            cursor = conn.cursor()
            query = f"DELETE FROM injest_events WHERE app_name = ? and entry_name in ({','.join(['?'] * len(entries))})"
            cursor.execute(query, (app_name, *entries))
            conn.commit()
