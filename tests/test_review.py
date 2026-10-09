import json
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer
import pytest
from ledger_htr.data import write_jsonl, read_jsonl
from ledger_htr.review import make_handler


@pytest.fixture
def server(tmp_path):
    write_jsonl(tmp_path / "data/references.jsonl", [{"id": "one", "page_id": "page", "split": "pilot",
                "kind": "text", "text": "Cash", "reviewed": False, "reviewer": None}])
    (tmp_path / "data/source-manifest.json").write_text('{"pages": []}')
    http = HTTPServer(("127.0.0.1", 0), make_handler(tmp_path))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{http.server_port}", tmp_path
    http.shutdown(); http.server_close(); thread.join()


def get(url):
    return json.load(urllib.request.urlopen(url))


def update(url, revision, **kwargs):
    body = {"id": "one", "revision": revision, "text": "Cash", "reviewer": "fixture reviewer",
            "reviewed": True, "uncertain": False, **kwargs}
    request = urllib.request.Request(url + "/api/reference", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(request))


def test_review_persists_and_stale_write_is_rejected(server):
    url, root = server
    revision = get(url + "/api/state")["revision"]
    saved = update(url, revision, text="Cash 20")
    assert saved["revision"] != revision
    assert read_jsonl(root / "data/references.local.jsonl")[0]["text"] == "Cash 20"
    assert read_jsonl(root / "data/references.jsonl")[0]["reviewed"] is False
    # A fresh handler reads persisted state, rather than keeping it only in memory.
    fresh = HTTPServer(("127.0.0.1", 0), make_handler(root))
    thread = threading.Thread(target=fresh.serve_forever, daemon=True); thread.start()
    try:
        assert get(f"http://127.0.0.1:{fresh.server_port}/api/state")["references"][0]["text"] == "Cash 20"
    finally:
        fresh.shutdown(); fresh.server_close(); thread.join()
    with pytest.raises(urllib.error.HTTPError) as error:
        update(url, revision, text="overwrite")
    assert error.value.code == 409


def test_empty_reviewer_is_rejected(server):
    url, _ = server
    with pytest.raises(urllib.error.HTTPError) as error:
        update(url, get(url + "/api/state")["revision"], reviewer="")
    assert error.value.code == 400


def test_cross_origin_write_is_rejected(server):
    url, _ = server
    request = urllib.request.Request(url + "/api/reference", data=b"{}",
        headers={"Content-Type": "application/json", "Origin": "https://unrelated.example"})
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request)
    assert error.value.code == 403


def test_server_does_not_expose_arbitrary_project_files(server):
    url, root = server
    (root / "private.txt").write_text("fixture content")
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(url + "/private.txt")
    assert error.value.code == 404
