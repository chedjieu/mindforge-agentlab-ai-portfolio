from app.api.schemas import ChatRequest, FinalAnswer, ResearchNotes, StudyNote


def test_chat_request_defaults():
    req = ChatRequest(message="hello")
    assert req.thread_id == "default"
    assert req.stream is True


def test_structured_outputs():
    notes = ResearchNotes(facts=["a"], citations=["doc#page=1"])
    study = StudyNote(title="Guide", markdown="# Guide\n- a", sections=["Guide"])
    final = FinalAnswer(answer="ok", citations=notes.citations)
    assert study.title == "Guide"
    assert final.citations == ["doc#page=1"]
