from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from er_reviewer._csv_utils import open_dict_row_source, require_columns


@dataclass(frozen=True)
class MembershipDifference:
    id_value: str
    category: str
    old_members: tuple[str, ...]
    new_members: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["old_members"] = "|".join(self.old_members)
        data["new_members"] = "|".join(self.new_members)
        return data


def _membership(
    rows: Iterable[dict[str, str]],
    id_column: str,
    member_column: str,
    *,
    fieldnames: Iterable[str] | None = None,
) -> dict[str, set[str]]:
    if fieldnames is not None:
        require_columns(fieldnames, [id_column, member_column])
    elif isinstance(rows, list):
        require_columns(rows[0].keys() if rows else [], [id_column, member_column])
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        id_value = (row.get(id_column) or "").strip()
        member_value = (row.get(member_column) or "").strip()
        if id_value and member_value:
            grouped[id_value].add(member_value)
    return grouped


def compare_export_membership(
    old_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
    *,
    id_column: str,
    member_column: str,
    include_narratives: bool = False,
) -> list[MembershipDifference]:
    """Compare entity membership grouped by a persistent or cluster identifier."""
    old_membership = _membership(old_rows, id_column, member_column)
    new_membership = _membership(new_rows, id_column, member_column)
    return _compare_membership(
        old_membership=old_membership,
        new_membership=new_membership,
        include_narratives=include_narratives,
    )


def _compare_membership(
    *,
    old_membership: dict[str, set[str]],
    new_membership: dict[str, set[str]],
    include_narratives: bool,
) -> list[MembershipDifference]:
    differences: list[MembershipDifference] = []
    for id_value in sorted(set(old_membership) | set(new_membership)):
        old_members = old_membership.get(id_value, set())
        new_members = new_membership.get(id_value, set())
        if old_members == new_members:
            continue
        if old_members and not new_members:
            category = "removed"
        elif new_members and not old_members:
            category = "added"
        elif len(old_members) != len(new_members):
            category = "member_count_changed"
        else:
            category = "members_changed"
        differences.append(
            MembershipDifference(
                id_value=id_value,
                category=category,
                old_members=tuple(sorted(old_members)),
                new_members=tuple(sorted(new_members)),
            )
        )
    if include_narratives:
        differences.extend(
            _member_reassignment_differences(
                old_membership=old_membership,
                new_membership=new_membership,
            )
        )
        differences.extend(
            _split_merge_differences(
                old_membership=old_membership,
                new_membership=new_membership,
            )
        )
    return differences


def compare_export_membership_csv(
    old_path: str | Path,
    new_path: str | Path,
    *,
    id_column: str,
    member_column: str,
    old_encoding: str = "utf-8",
    new_encoding: str = "utf-8",
    old_delimiter: str = ",",
    new_delimiter: str = ",",
    include_narratives: bool = False,
) -> list[MembershipDifference]:
    with (
        open_dict_row_source(
            old_path,
            encoding=old_encoding,
            delimiter=old_delimiter,
        ) as old_source,
        open_dict_row_source(
            new_path,
            encoding=new_encoding,
            delimiter=new_delimiter,
        ) as new_source,
    ):
        old_membership = _membership(
            old_source.rows,
            id_column,
            member_column,
            fieldnames=old_source.fieldnames,
        )
        new_membership = _membership(
            new_source.rows,
            id_column,
            member_column,
            fieldnames=new_source.fieldnames,
        )
    return _compare_membership(
        old_membership=old_membership,
        new_membership=new_membership,
        include_narratives=include_narratives,
    )


def _member_to_id(membership: dict[str, set[str]]) -> dict[str, str]:
    member_to_id: dict[str, str] = {}
    for id_value, members in membership.items():
        for member in members:
            member_to_id[member] = id_value
    return member_to_id


def _member_reassignment_differences(
    *,
    old_membership: dict[str, set[str]],
    new_membership: dict[str, set[str]],
) -> list[MembershipDifference]:
    old_by_member = _member_to_id(old_membership)
    new_by_member = _member_to_id(new_membership)
    differences: list[MembershipDifference] = []
    for member in sorted(set(old_by_member) & set(new_by_member)):
        old_id = old_by_member[member]
        new_id = new_by_member[member]
        if old_id == new_id:
            continue
        differences.append(
            MembershipDifference(
                id_value=member,
                category="member_reassigned",
                old_members=(old_id,),
                new_members=(new_id,),
            )
        )
    return differences


def _split_merge_differences(
    *,
    old_membership: dict[str, set[str]],
    new_membership: dict[str, set[str]],
) -> list[MembershipDifference]:
    old_by_member = _member_to_id(old_membership)
    new_by_member = _member_to_id(new_membership)
    differences: list[MembershipDifference] = []

    for old_id, old_members in sorted(old_membership.items()):
        new_ids = sorted(
            {new_by_member[member] for member in old_members if member in new_by_member}
        )
        if len(new_ids) > 1:
            differences.append(
                MembershipDifference(
                    id_value=old_id,
                    category="split",
                    old_members=tuple(sorted(old_members)),
                    new_members=tuple(new_ids),
                )
            )

    for new_id, new_members in sorted(new_membership.items()):
        old_ids = sorted(
            {old_by_member[member] for member in new_members if member in old_by_member}
        )
        if len(old_ids) > 1:
            differences.append(
                MembershipDifference(
                    id_value=new_id,
                    category="merged",
                    old_members=tuple(old_ids),
                    new_members=tuple(sorted(new_members)),
                )
            )

    return differences
