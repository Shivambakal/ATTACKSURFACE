from datetime import datetime, timezone
from types import SimpleNamespace
from app.models import utcnow
from app.services.diffing import compare, Diff
from app.services.classification import classify
from app.services.scoring import score

def obs(url, h, tech=None, text=""):
    return SimpleNamespace(url=url, content_hash=h, technologies=tech or [], title="", text_excerpt=text)

def test_diff_added_removed_and_changed():
    result = compare([obs("https://a.test/old", "a"), obs("https://a.test/x", "one")], [obs("https://a.test/new", "b"), obs("https://a.test/x", "two")])
    assert {(x.kind, x.url) for x in result} == {("page_removed", "https://a.test/old"), ("page_added", "https://a.test/new"), ("content_changed", "https://a.test/x")}

def test_classification_and_score_are_deterministic():
    diff = Diff("page_added", "https://a.test/docs/openapi", None, obs("https://a.test/docs/openapi", "x", text="API endpoints"))
    category, confidence, _, note = classify(diff)
    assert category == "new_api_documentation" and confidence == .9 and "not a vulnerability" in note
    assert score(category, diff.url) == 80

def test_score_increases_for_auth_context():
    assert score("public_content_change", "https://a.test/oauth") > score("public_content_change", "https://a.test/news")

def test_utc_timestamp():
    assert utcnow().tzinfo == timezone.utc

def test_deduplication_fingerprint_input_is_stable():
    import hashlib
    payload = "1:2:new_public_page:https://a.test/new:abc"
    assert hashlib.sha256(payload.encode()).hexdigest() == hashlib.sha256(payload.encode()).hexdigest()
