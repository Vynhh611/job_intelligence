"""Backward-compatible JSON store with opt-in PostgreSQL shared snapshots.

PostgreSQL uses revision checks to prevent lost updates and an append-only audit.
No CV or applicant data belongs in this store. Migration is explicit, never startup.
"""
import json
import os
import tempfile
from pathlib import Path
from settings import setting

ROOT = Path(__file__).resolve().parent
ALLOWED = {'sources.json', 'data/jobs.json', 'data/history.json', 'data/run_status.json',
           'data/discovered_jobs.json', 'data/discovery_history.json', 'data/discovery_status.json',
           'data/company_profiles.json', 'data/company_watchlist.json', 'data/source_probe.json',
           'data/source_candidates.json', 'data/job_explanations.json'}


class StorageError(RuntimeError):
    pass


class ConflictError(StorageError):
    pass


def document_key(path):
    try:
        key = Path(path).resolve().relative_to(ROOT).as_posix()
        return key if key in ALLOWED else None
    except ValueError:
        return None


def local_read(path, default):
    return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default


def local_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique temporary file avoids colliding writers' temporary paths.
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as file:
            name = file.name
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write('\n')
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()


class PostgresStore:
    def __init__(self, url):
        self.url = url
        self.revisions = {}

    def connect(self):
        try:
            import psycopg
            return psycopg.connect(self.url, connect_timeout=10)
        except Exception:
            raise StorageError('Không kết nối được PostgreSQL. Kiểm tra cấu hình máy chủ; không chuyển âm thầm sang dữ liệu cục bộ.') from None

    def initialize(self):
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS ji_documents (key TEXT PRIMARY KEY, value JSONB NOT NULL, revision BIGINT NOT NULL DEFAULT 1, updated_at TIMESTAMPTZ NOT NULL DEFAULT now())')
            connection.execute('CREATE TABLE IF NOT EXISTS ji_document_history (id BIGSERIAL PRIMARY KEY, key TEXT NOT NULL, value JSONB NOT NULL, revision BIGINT NOT NULL, recorded_at TIMESTAMPTZ NOT NULL DEFAULT now())')

    def read(self, key, default):
        try:
            with self.connect() as connection:
                row = connection.execute('SELECT value, revision FROM ji_documents WHERE key = %s', (key,)).fetchone()
            self.revisions[key] = row[1] if row else 0
            return row[0] if row else default
        except StorageError:
            raise
        except Exception:
            raise StorageError('Không đọc được PostgreSQL. Chạy bước khởi tạo/di trú trước khi bật lưu trữ dùng chung.') from None

    def write(self, key, value, only_new=False):
        from psycopg.types.json import Jsonb
        expected = 0 if only_new else self.revisions.get(key)
        if expected is None:
            raise ConflictError('Đọc bản hiện tại trước khi lưu để kiểm tra xung đột.')
        try:
            with self.connect() as connection:
                # Serializes insert as well as update, independent of row existence.
                connection.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (key,))
                row = connection.execute('SELECT revision, value FROM ji_documents WHERE key = %s FOR UPDATE', (key,)).fetchone()
                actual = row[0] if row else 0
                if actual != expected:
                    raise ConflictError('Dữ liệu đã được cập nhật bởi phiên khác. Tải lại trước khi lưu.')
                if row:
                    connection.execute('INSERT INTO ji_document_history(key, value, revision) VALUES (%s, %s, %s)', (key, Jsonb(row[1]), actual))
                    connection.execute('UPDATE ji_documents SET value = %s, revision = revision + 1, updated_at = now() WHERE key = %s', (Jsonb(value), key))
                else:
                    connection.execute('INSERT INTO ji_documents(key, value) VALUES (%s, %s)', (key, Jsonb(value)))
            self.revisions[key] = actual + 1
        except StorageError:
            raise
        except Exception:
            raise StorageError('Không lưu được PostgreSQL. Dữ liệu của lần ghi này đã được hoàn tác.') from None


def load(path, default, store=None):
    key = document_key(path)
    return store.read(key, default) if store and key else local_read(path, default)


def save(path, value, store=None):
    key = document_key(path)
    if store and key:
        store.write(key, value)
    else:
        local_write(path, value)


def configured_store():
    url = setting('DATABASE_URL')
    return PostgresStore(url) if url else None
