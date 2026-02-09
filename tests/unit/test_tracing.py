from core.tracing import get_tracer, JSONLTracer


def test_tracer_noop_when_no_path(tmp_path):
    tracer = get_tracer(None)
    assert tracer.__class__.__name__ == "NoopTracer"
    tracer.emit({"event": "noop"})


def test_tracer_writes_jsonl(tmp_path):
    path = tmp_path / "trace.jsonl"
    tracer = get_tracer(str(path))
    assert isinstance(tracer, JSONLTracer)
    tracer.emit({"event": "test", "value": 123})

    data = path.read_text().strip()
    assert '"event": "test"' in data
    assert '"value": 123' in data
