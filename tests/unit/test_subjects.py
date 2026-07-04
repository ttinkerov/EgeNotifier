from egebot.content.federal_subjects import SUBJECTS, subject_exists


def test_subject_codes_are_unique() -> None:
    assert len(SUBJECTS) == len(set(SUBJECTS.keys()))


def test_subject_lookup() -> None:
    assert subject_exists(77)
    assert subject_exists(78)
    assert not subject_exists(99)
