"""Explicit, non-overwriting JSON -> PostgreSQL import; no CV files accepted."""
import argparse
from storage import ROOT, ALLOWED, configured_store, local_read, local_write, ConflictError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Create schema and import missing documents only')
    parser.add_argument('--export-dir', help='Export PostgreSQL snapshots to a new directory; never overwrite files')
    args = parser.parse_args()
    store = configured_store()
    if not store:
        raise SystemExit('Set DATABASE_URL in the execution environment; never pass it as a command argument.')
    if args.export_dir:
        from pathlib import Path
        output = Path(args.export_dir)
        if output.exists():
            raise SystemExit('Export destination must be a new directory.')
        records = {key: store.read(key, None) for key in sorted(ALLOWED)}
        for key, value in records.items():
            if value is not None:
                local_write(output / key, value)
        print('Export complete. Existing project files unchanged.')
        return
    documents = {key: local_read(ROOT / key, None) for key in sorted(ALLOWED) if (ROOT / key).exists()}
    print(f'{len(documents)} JSON documents validated. Original files will be retained.')
    if not args.apply:
        print('Preview only. Use --apply to initialize PostgreSQL and import missing keys.')
        return
    store.initialize()
    for key, value in documents.items():
        try:
            store.write(key, value, only_new=True)
            print('IMPORTED', key)
        except ConflictError:
            print('PRESERVED existing database document:', key)


if __name__ == '__main__':
    main()
