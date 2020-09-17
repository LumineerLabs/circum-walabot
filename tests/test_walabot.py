from unittest.mock import DEFAULT, MagicMock, PropertyMock, call, patch

import circum.endpoint  # noqa: F401

import circum_walabot.walabot
from circum_walabot.walabot import _cli, _update_thread, run_walabot

import pytest


def _expect_init(path, custom_api_path=None):
    with patch("circum_walabot.walabot._load_api") as loader:
        with patch("circum_walabot.walabot._create_tracker_thread") as thread:
            with patch("circum.endpoint.start_endpoint") as endpoint:

                PROF_TRACKER = 1
                type(loader()).PROF_TRACKER = PropertyMock(return_value=PROF_TRACKER)

                FILTER_TYPE_MTI = 2
                type(loader()).FILTER_TYPE_MTI = PropertyMock(return_value=FILTER_TYPE_MTI)

                expected_calls = [
                    # _init_api
                    call(path + 'python/WalabotAPI.py'),
                    call().Init(),
                    call().Initialize(),
                    # _connect_to_and_initialize_device
                    call().ConnectAny(),
                    call().SetProfile(PROF_TRACKER),
                    call().SetThreshold(30),
                    call().SetArenaR(30, 200, 3),
                    call().SetArenaTheta(-15, 15, 5),
                    call().SetArenaPhi(-60, 60, 5),
                    call().SetDynamicImageFilter(FILTER_TYPE_MTI),
                    call().Start(),
                    # _create_tracker_thread
                    call.thread(loader()),
                    # start endpoint
                    call.endpoint(None, 'walabot', run_walabot),
                    # clean up and exit
                    call().Stop(),
                    call().Disconnect(),
                    call().Clean(),
                ]

                loader.attach_mock(thread, 'thread')
                loader.attach_mock(endpoint, 'endpoint')

                _cli(None, custom_api_path)

                loader.assert_has_calls(expected_calls)


def test_walabot_nt():
    with patch("os.name", "nt"):
        _expect_init('C:/Program Files/Walabot/WalabotSDK/')


def test_walabot_else():
    with patch("os.name", "not_nt"):
        _expect_init('/usr/share/walabot/')


def test_walabot_specify_api():
    _expect_init('/foo/', '/foo/')


class EndLoopException(Exception):
    pass


class FakeTarget():
    def __init__(self, x, y, z, a):
        self.xPosCm = x
        self.yPosCm = y
        self.zPosCm = z
        self.amplitude = a


def test__update_thread_gettargets_returns_none():
    wlbt = MagicMock()

    with patch("circum_walabot.walabot.tracking_semaphore") as tracking_semaphore:
        wlbt.attach_mock(tracking_semaphore, 'tracking_semaphore')

        # run the loop twice, then except out
        wlbt.GetStatus = MagicMock()
        wlbt.GetStatus.return_value = (1, 1)
        wlbt.GetStatus.side_effect = [DEFAULT, EndLoopException]

        wlbt.GetTrackerTargets = MagicMock()
        wlbt.GetTrackerTargets.return_value = None

        wlbt.GetRawImageSlice = MagicMock()
        wlbt.GetRawImageSlice.return_value = (0, 0, 0, 0, 0)

        expected_calls = [
            # _get_targets
            call.GetStatus(),
            call.Trigger(),
            call.GetTrackerTargets(),
            call.GetRawImageSlice(),
            # _update_thread
            call.tracking_semaphore.acquire(),
            call.tracking_semaphore.release(),
            # _get_targets
            call.GetStatus(),
        ]

        assert not circum_walabot.walabot.updated

        with pytest.raises(EndLoopException):
            _update_thread(wlbt)

        assert circum_walabot.walabot.updated

        circum_walabot.walabot.updated = False

        wlbt.assert_has_calls(expected_calls)

        circum_walabot.walabot.tracking_info["objects"] == []


def test__update_thread_gettargets_returns_targets_once():
    wlbt = MagicMock()

    with patch("circum_walabot.walabot.tracking_semaphore") as tracking_semaphore:
        wlbt.attach_mock(tracking_semaphore, 'tracking_semaphore')

        # run the loop twice, then except out
        wlbt.GetStatus = MagicMock()
        wlbt.GetStatus.return_value = (1, 1)
        wlbt.GetStatus.side_effect = [DEFAULT, EndLoopException]

        wlbt.GetTrackerTargets = MagicMock()
        wlbt.GetTrackerTargets.return_value = [FakeTarget(0, 1, 2, 3)]

        wlbt.GetRawImageSlice = MagicMock()
        wlbt.GetRawImageSlice.return_value = (0, 0, 0, 0, 0)

        expected_targets = [
            {
                "x": -1 * target.xPosCm / 100,
                "y": target.yPosCm / 100,
                "z": target.zPosCm / 100
            } for target in wlbt.GetTrackerTargets.return_value
        ]

        expected_calls = [
            # _get_targets
            call.GetStatus(),
            call.Trigger(),
            call.GetTrackerTargets(),
            call.GetRawImageSlice(),
            # _update_thread
            call.tracking_semaphore.acquire(),
            call.tracking_semaphore.release(),
            # _get_targets
            call.GetStatus(),
        ]

        assert not circum_walabot.walabot.updated

        with pytest.raises(EndLoopException):
            _update_thread(wlbt)

        assert circum_walabot.walabot.updated

        circum_walabot.walabot.updated = False

        wlbt.assert_has_calls(expected_calls)

        circum_walabot.walabot.tracking_info["objects"] == expected_targets


def test__update_thread_gettargets_returns_targets_multiple():
    wlbt = MagicMock()

    with patch("circum_walabot.walabot.tracking_semaphore") as tracking_semaphore:
        wlbt.attach_mock(tracking_semaphore, 'tracking_semaphore')

        # run the loop twice, then except out
        wlbt.GetStatus = MagicMock()
        wlbt.GetStatus.return_value = (1, 1)
        wlbt.GetStatus.side_effect = [DEFAULT, DEFAULT, EndLoopException]

        wlbt.GetTrackerTargets = MagicMock()
        wlbt.GetTrackerTargets.side_effect = [
            [FakeTarget(0, 1, 2, 3)],
            [
                FakeTarget(4, 5, 6, 7),
                FakeTarget(8, 9, 10, 11)
            ]
        ]

        wlbt.GetRawImageSlice = MagicMock()
        wlbt.GetRawImageSlice.return_value = (0, 0, 0, 0, 0)

        expected_targets = [
            {
                "x": -1 * target.xPosCm / 100,
                "y": target.yPosCm / 100,
                "z": target.zPosCm / 100
            } for target in wlbt.GetTrackerTargets.return_value[1]
        ]

        expected_calls = [
            # _get_targets
            call.GetStatus(),
            call.Trigger(),
            call.GetTrackerTargets(),
            call.GetRawImageSlice(),
            # _update_thread
            call.tracking_semaphore.acquire(),
            call.tracking_semaphore.release(),
            # _get_targets
            call.GetStatus(),
            call.Trigger(),
            call.GetTrackerTargets(),
            call.GetRawImageSlice(),
            # _update_thread
            call.tracking_semaphore.acquire(),
            call.tracking_semaphore.release(),
            # _get_targets
            call.GetStatus(),
        ]

        assert not circum_walabot.walabot.updated

        with pytest.raises(EndLoopException):
            _update_thread(wlbt)

        assert circum_walabot.walabot.updated

        circum_walabot.walabot.updated = False

        wlbt.assert_has_calls(expected_calls)

        assert len(circum_walabot.walabot.tracking_info["objects"]) == 2
        circum_walabot.walabot.tracking_info["objects"] == expected_targets


def test_run_walabot_updated_false():
    with patch("circum_walabot.walabot.tracking_semaphore") as tracking_semaphore:
        expected_calls = [
            call.acquire(),
            call.release(),
        ]

        assert not circum_walabot.walabot.updated
        assert run_walabot(None) is None

        tracking_semaphore.assert_has_calls(expected_calls)


def test_run_walabot_updated_true():
    with patch("circum_walabot.walabot.tracking_semaphore") as tracking_semaphore:
        expected_calls = [
            call.acquire(),
            call.release(),
        ]

        circum_walabot.walabot.updated = True
        circum_walabot.walabot.tracking_info = [0, 1, 2]
        ret = run_walabot(None)
        assert ret is not None
        assert ret == circum_walabot.walabot.tracking_info
        assert ret is not circum_walabot.walabot.tracking_info

        tracking_semaphore.assert_has_calls(expected_calls)

        circum_walabot.walabot.update = False
