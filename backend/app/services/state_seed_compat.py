"""Reuse legacy state-directory rows without deleting or merging their IDs."""
from __future__ import annotations

from datetime import datetime, timezone


def _key(value):
    return ' '.join(str(value or '').split()).casefold()


def _build_plan(rows, catalog, normalized_names):
    """Resolve every catalog entry before mutating any ORM row."""
    by_code, by_name = {}, {}
    for row in rows:
        code = _key(row.code)
        if code:
            by_code.setdefault(code, {})[row.id] = row
        names = {_key(row.name), _key(normalized_names.get(row.id))} - {''}
        for name in names:
            by_name.setdefault(name, {})[row.id] = row
    plan, used_ids, seen_codes, seen_names = [], set(), set(), set()
    for item in catalog:
        code, name = _key(item.get('code')), _key(item.get('name'))
        if not code or not name or not item.get('type'):
            raise ValueError('State catalog entry requires nonempty code, name and type.')
        if code in seen_codes or name in seen_names:
            raise ValueError('Duplicate entry in the state catalog: ' + item['name'])
        seen_codes.add(code)
        seen_names.add(name)
        matches = {**by_code.get(code, {}), **by_name.get(name, {})}
        if len(matches) > 1:
            raise ValueError(
                'State directory has conflicting rows for ' + item['name']
                + '; IDs: ' + ', '.join(str(value) for value in matches)
                + '. Resolve the conflicting code/name assignments; no rows were merged or deleted.'
            )
        row = next(iter(matches.values()), None)
        if row is not None:
            if row.id in used_ids:
                raise ValueError('A legacy row matches multiple catalog states; ID: ' + str(row.id))
            used_ids.add(row.id)
        plan.append((row, item))
    return plan


def seed_state_directory(db, model, catalog):
    # Imports stay local: the resolver can be verified without a database driver.
    from sqlalchemy import MetaData, Table, insert, select, text

    connection = db.connection()
    table = Table(model.__tablename__, MetaData(), autoload_with=connection)
    dialect = connection.dialect.name
    if dialect == 'postgresql':
        # Serialize concurrent seeders in this transaction, including legacy writers.
        quoted = connection.dialect.identifier_preparer.format_table(table)
        db.execute(text('LOCK TABLE ' + quoted + ' IN SHARE ROW EXCLUSIVE MODE'))
    rows = list(db.scalars(select(model)))
    has_normalized_name = 'normalized_name' in table.c
    normalized_names = {}
    if has_normalized_name:
        normalized_names = dict(db.execute(select(table.c.id, table.c.normalized_name)).all())
    plan = _build_plan(rows, list(catalog), normalized_names)
    for row, item in plan:
        if row is None:
            continue
        row.code = item['code']
        row.name = item['name']
        row.state_type = item['type']
        row.active = True
        if not row.source:
            row.source = 'Government of India state directory'
    db.flush()
    inserted = 0
    for row, item in plan:
        if row is not None:
            continue
        now = datetime.now(timezone.utc)
        values = dict(
            code=item['code'], name=item['name'], state_type=item['type'], active=True,
            source='Government of India state directory', created_at=now, updated_at=now,
        )
        if has_normalized_name and table.c.normalized_name.computed is None:
            values['normalized_name'] = _key(item['name'])
        db.execute(insert(table).values(**values))
        inserted += 1
    # The caller owns commit/rollback; do not commit part of application startup.
    return inserted
