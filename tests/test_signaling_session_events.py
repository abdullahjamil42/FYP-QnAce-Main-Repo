from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from server.app.intelligence.session_stages import SessionStage, SessionTimer
from server.app.webrtc import signaling


def _set_elapsed(timer: SessionTimer, elapsed_seconds: float) -> None:
    timer.start()
    timer._start_time = time.time() - elapsed_seconds  # type: ignore[attr-defined]


def test_process_timer_events_emits_time_warning_once():
    timer = SessionTimer(duration_minutes=20)
    _set_elapsed(timer, elapsed_seconds=(20 * 60) - (4 * 60))
    session = {
        "timer": timer,
        "stage": SessionStage.TECHNICAL,
    }

    events: list[tuple[str, object]] = []

    ended = signaling._process_timer_events(
        session,
        object(),
        send_time_warning_fn=lambda _channel, remaining_minutes: events.append(("time_warning", remaining_minutes)),
        send_session_ended_fn=lambda _channel, reason: events.append(("session_ended", reason)),
        send_stage_change_fn=lambda *_args, **_kwargs: None,
        send_status_fn=lambda *_args, **_kwargs: None,
    )
    assert ended is False
    assert session.get("time_warning_sent") is True
    assert events == [("time_warning", 4)]

    # Second tick should not re-emit the same warning.
    ended_second = signaling._process_timer_events(
        session,
        object(),
        send_time_warning_fn=lambda _channel, remaining_minutes: events.append(("time_warning", remaining_minutes)),
        send_session_ended_fn=lambda _channel, reason: events.append(("session_ended", reason)),
        send_stage_change_fn=lambda *_args, **_kwargs: None,
        send_status_fn=lambda *_args, **_kwargs: None,
    )
    assert ended_second is False
    assert events == [("time_warning", 4)]


def test_process_timer_events_emits_session_end_once():
    timer = SessionTimer(duration_minutes=20)
    _set_elapsed(timer, elapsed_seconds=(20 * 60) + 5)
    session = {
        "timer": timer,
        "stage": SessionStage.WRAP_UP,
    }

    events: list[tuple[str, object]] = []

    ended = signaling._process_timer_events(
        session,
        object(),
        send_time_warning_fn=lambda _channel, remaining_minutes: events.append(("time_warning", remaining_minutes)),
        send_session_ended_fn=lambda _channel, reason: events.append(("session_ended", reason)),
        send_stage_change_fn=lambda _channel, stage, metadata=None: events.append(("stage_change", stage)),
        send_status_fn=lambda *_args, **_kwargs: None,
    )
    assert ended is True
    assert session.get("session_end_notified") is True
    assert session["stage"] == SessionStage.ENDED
    assert ("session_ended", "time_limit_reached") in events
    assert ("stage_change", SessionStage.ENDED.name) in events

    ended_second = signaling._process_timer_events(
        session,
        object(),
        send_time_warning_fn=lambda _channel, remaining_minutes: events.append(("time_warning", remaining_minutes)),
        send_session_ended_fn=lambda _channel, reason: events.append(("session_ended", reason)),
        send_stage_change_fn=lambda _channel, stage, metadata=None: events.append(("stage_change", stage)),
        send_status_fn=lambda *_args, **_kwargs: None,
    )
    assert ended_second is True
    assert events.count(("session_ended", "time_limit_reached")) == 1


def test_ensure_timer_started_is_idempotent():
    timer = SessionTimer(duration_minutes=1)
    session = {"timer": timer}

    started_first = signaling._ensure_timer_started(session)
    assert started_first is True
    assert timer._start_time is not None  # type: ignore[attr-defined]

    started_second = signaling._ensure_timer_started(session)
    assert started_second is False


@pytest.mark.asyncio
async def test_run_session_timer_loop_processes_open_channel_and_stops_on_end():
    session_id = "session-1"
    session = {
        "data_channel": SimpleNamespace(readyState="open"),
    }
    sessions = {session_id: session}
    calls: list[str] = []

    async def no_wait(_seconds: float) -> None:
        return None

    def process_timer_events_fn(_session, _channel) -> bool:
        calls.append("tick")
        return True

    ended = await signaling._run_session_timer_loop(
        session_id,
        session,
        sessions,
        process_timer_events_fn=process_timer_events_fn,
        sleep_fn=no_wait,
        interval_s=0.0,
    )

    assert ended is True
    assert calls == ["tick"]


@pytest.mark.asyncio
async def test_run_session_timer_loop_skips_closed_channel_until_tick_limit():
    session_id = "session-2"
    session = {
        "data_channel": SimpleNamespace(readyState="closed"),
    }
    sessions = {session_id: session}
    calls: list[str] = []

    async def no_wait(_seconds: float) -> None:
        return None

    def process_timer_events_fn(_session, _channel) -> bool:
        calls.append("tick")
        return False

    ended = await signaling._run_session_timer_loop(
        session_id,
        session,
        sessions,
        process_timer_events_fn=process_timer_events_fn,
        sleep_fn=no_wait,
        interval_s=0.0,
        max_ticks=3,
    )

    assert ended is False
    assert calls == []
