from pdftomd.converter.marker_process import MarkerProcessClient


class FakeProcess:
    def __init__(self, *args, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False

    def is_alive(self) -> bool:
        return self.started

    def start(self) -> None:
        self.started = True


class FakeContext:
    created_process: FakeProcess | None = None

    def Queue(self):  # noqa: N802
        return object()

    def Process(self, *args, **kwargs):  # noqa: N802
        process = FakeProcess(*args, **kwargs)
        type(self).created_process = process
        return process


def test_marker_process_is_not_daemonic(monkeypatch) -> None:
    monkeypatch.setattr(
        "pdftomd.converter.marker_process.multiprocessing.get_context",
        lambda method: FakeContext(),
    )

    client = MarkerProcessClient(device="cpu")
    client._start()

    assert FakeContext.created_process is not None
    assert "daemon" not in FakeContext.created_process.kwargs
