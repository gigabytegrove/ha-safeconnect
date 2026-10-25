"""Regression for mandatory DOMAIN attribute in Home Assistant OAuth config flows."""
import ast
from pathlib import Path
from types import SimpleNamespace
import logging

ROOT = Path(__file__).resolve().parents[1]

def test_oauth2_flow_is_instantiable_with_domain():
    path = ROOT / 'custom_components/safeconnect/config_flow.py'
    module = ast.parse(path.read_text(encoding='utf-8'))
    cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'SafeConnectConfigFlow')
    class StubHomeAssistantOauthBase:
        DOMAIN = ''
        def __init_subclass__(cls, **kwargs):
            # A domain registry keyword does not set the class DOMAIN attribute.
            super().__init_subclass__()
        def __init__(self):
            if self.DOMAIN == '':
                raise TypeError("Can't instantiate class without DOMAIN being set")
    ns = {
        'config_entry_oauth2_flow': SimpleNamespace(AbstractOAuth2FlowHandler=StubHomeAssistantOauthBase),
        'DOMAIN': 'safeconnect', 'logging': logging, '_LOGGER': logging.getLogger('safeconnect'),
        'ConfigFlowResult': dict, 'OptionsFlow': object,
        'config_entries': SimpleNamespace(ConfigEntry=object),
        'callback': lambda cb: cb,
    }
    extracted = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), cls], type_ignores=[])
    ast.fix_missing_locations(extracted)
    exec(compile(extracted, str(path), 'exec'), ns)
    assert ns['SafeConnectConfigFlow']().DOMAIN == 'safeconnect'
