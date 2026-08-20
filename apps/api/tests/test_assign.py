from types import SimpleNamespace

from app.content.assign import exam_first_ids, pack_kind


def _set(slug: str, n: int, *, kind: str | None = None, time_limit: int = 600):
    return SimpleNamespace(
        id=slug,
        slug=slug,
        meta={"kind": kind} if kind else {},
        time_limit_sec=time_limit,
        questions=[object()] * n,
    )


def test_pack_kind_uses_meta_then_length():
    exam = _set("exam-a", 40, kind="exam", time_limit=3600)
    drill = _set("drill-a", 6, kind="drill", time_limit=600)
    inferred = _set("inferred", 40, time_limit=3600)
    short = _set("short", 4, time_limit=600)
    assert pack_kind(exam, 40) == "exam"
    assert pack_kind(drill, 6) == "drill"
    assert pack_kind(inferred, 40) == "exam"
    assert pack_kind(short, 4) == "drill"


def test_exam_first_ids_orders_papers_ahead_of_drills():
    exam = _set("exam-a", 40, kind="exam", time_limit=3600)
    drill = _set("drill-a", 3, kind="drill")
    ordered = exam_first_ids("user-1", "reading:academic:set", [drill, exam])
    assert ordered[0] == "exam-a"
    assert ordered[-1] == "drill-a"
