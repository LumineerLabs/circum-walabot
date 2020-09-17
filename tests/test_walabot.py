from unittest.mock import PropertyMock, call, patch

import circum.endpoint  # noqa: F401

from circum_walabot.walabot import _cli, run_walabot


def _expect_init(path, custom_api_path=None):
    with patch("circum_walabot.walabot._load_api") as loader:
        with patch("circum_walabot.walabot._create_tracker_thread") as thread:
            with patch("circum.endpoint.start_endpoint") as endpoint:

                PROF_TRACKER = 1
                type(loader()).PROF_TRACKER = PropertyMock(return_value=PROF_TRACKER)

                FILTER_TYPE_MTI = 2
                type(loader()).FILTER_TYPE_MTI = PropertyMock(return_value=FILTER_TYPE_MTI)

                expected_calls = [
                    call(path + 'python/WalabotAPI.py'),
                    call().Init(),
                    call().Initialize(),
                    call().ConnectAny(),
                    call().SetProfile(PROF_TRACKER),
                    call().SetThreshold(30),
                    call().SetArenaR(30, 200, 3),
                    call().SetArenaTheta(-15, 15, 5),
                    call().SetArenaPhi(-60, 60, 5),
                    call().SetDynamicImageFilter(FILTER_TYPE_MTI),
                    call().Start(),
                    call.thread(loader()),
                    call.endpoint(None, 'walabot', run_walabot),
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
