import json
from pathlib import Path

import pytest

from egebot.content.university_catalog import (
    load_programs,
    parse_programs,
    reload_programs,
    update_catalog_from_file,
)
from egebot.services.universities import UniversitiesService


def test_parse_programs_rejects_empty() -> None:
    with pytest.raises(ValueError, match="пуст"):
        parse_programs([])


def test_parse_programs_rejects_duplicate_ids() -> None:
    sample = load_programs()[0].model_dump(mode="json")
    with pytest.raises(ValueError, match="дублир"):
        parse_programs([sample, sample])


def test_update_catalog_and_reload(tmp_path: Path) -> None:
    source = tmp_path / "new.json"
    programs = list(load_programs()[:3])
    source.write_text(
        json.dumps([p.model_dump(mode="json") for p in programs], ensure_ascii=False),
        encoding="utf-8",
    )
    dest = tmp_path / "universities.json"
    count = update_catalog_from_file(source, dest=dest)
    assert count == 3
    assert dest.exists()

    service = UniversitiesService()
    # dest is not CATALOG_PATH, so reload still loads packaged file
    assert service.catalog_size() >= 3
    assert service.reload_catalog() == service.catalog_size()
