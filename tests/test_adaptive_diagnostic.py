from types import SimpleNamespace

import app.main as m


class _ScalarResult:
    def __init__(self, profiles):
        self._profiles = profiles

    def scalars(self):
        return self

    def all(self):
        return list(self._profiles)


class _FakeDB:
    def __init__(self, profiles):
        self._profiles = profiles

    def execute(self, _statement):
        return _ScalarResult(self._profiles)


def _lesson_pool():
    return m.bank.pool("Chương I", "lesson", "Bài 1", diagnostic_only=True)


def test_repaired_profile_always_gets_two_mapped_recheck_probes():
    pool = _lesson_pool()
    generic = m.bank.select_practice(pool, "lesson", "standard")
    assert len(generic) >= 2
    profile = SimpleNamespace(
        error_id="VLN-01",
        repair_state="Đã sửa tốt",
        confidence=35.0,
    )
    selected, targets, strategy = m._diagnostic_select(
        _FakeDB([profile]),
        SimpleNamespace(id="student-test"),
        pool,
        generic,
        "Chương I",
        "Bài 1",
    )
    mapped = [q for q in selected if "VLN-01" in str(q)]
    assert strategy == "profile_targeted"
    assert "VLN-01" in targets
    assert len(mapped) >= 2
    assert len(selected) == min(len(generic), int(m.settings.max_session_questions))
    assert len({q["id"] for q in selected}) == len(selected)


def test_new_student_diagnostic_is_coverage_first_not_pure_random():
    pool = _lesson_pool()
    generic = m.bank.select_practice(pool, "lesson", "standard")
    selected, targets, strategy = m._diagnostic_select(
        _FakeDB([]),
        SimpleNamespace(id="new-student"),
        pool,
        generic,
        "Chương I",
        "Bài 1",
    )
    available = set()
    for q in pool:
        available.update(
            code for code in m._question_error_codes(q)
            if m._error_matches_scope(m.bank.error_by_id.get(code) or {}, "Chương I", "Bài 1")
        )
    covered = set()
    for q in selected:
        covered.update(m._question_error_codes(q))

    assert strategy == "coverage_first"
    assert targets == []
    assert len(selected) == min(len(generic), int(m.settings.max_session_questions))
    assert len({q["id"] for q in selected}) == len(selected)
    # Standard mode should cover every available misconception when the
    # session has enough capacity, otherwise it should use all available slots
    # for distinct coverage as far as mappings allow.
    assert len(covered & available) >= min(len(available), len(selected))


def test_practice_mode_selector_remains_unchanged():
    pool = m.bank.pool("Chương I", "lesson", "Bài 1", diagnostic_only=False)
    selected = m.bank.select_practice(pool, "lesson", "standard")
    assert selected
