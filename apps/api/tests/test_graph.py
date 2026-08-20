from app.agents.graph import build_graph


def test_graph_compiles() -> None:
    graph = build_graph()
    assert graph is not None
