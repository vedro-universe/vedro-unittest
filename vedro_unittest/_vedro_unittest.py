from vedro.core import Dispatcher, Plugin, PluginConfig
from vedro.events import ConfigLoadedEvent

from ._test_case_loader import TestCaseLoader

__all__ = ("VedroUnitTest", "VedroUnitTestPlugin",)


class VedroUnitTestPlugin(Plugin):
    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        event.config.Registry.ScenarioLoader.register(TestCaseLoader, self)


class VedroUnitTest(PluginConfig):
    plugin = VedroUnitTestPlugin
