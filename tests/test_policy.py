from short_video_agent.runtime import can_finish, run
from test_graph_mock import request


def test_old_report_rejected():
    state = run(request("normal"))
    assert can_finish(state)
    state["draft"]["title"] = "改变标题"
    assert not can_finish(state)
