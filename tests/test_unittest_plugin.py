from pathlib import Path
from unittest.mock import Mock

from baby_steps import given, then, when
from vedro.core import Config, Dispatcher
from vedro.events import ConfigLoadedEvent

from vedro_unittest import VedroUnitTestPlugin

from ._utils import dispatcher, vedro_unittest

__all__ = ("dispatcher", "vedro_unittest",)  # fixtures


async def test_unittest_plugin(*, vedro_unittest: VedroUnitTestPlugin, dispatcher: Dispatcher):
    with given:
        config_ = Mock(Config)
        event = ConfigLoadedEvent(Path("."), config_)

    with when:
        await dispatcher.fire(event)

    with then:
        assert config_.Registry.ModuleLoader.assert_called_once() is None
        assert config_.Registry.ScenarioLoader.register.assert_called_once() is None

        assert len(config_.mock_calls) == 2
