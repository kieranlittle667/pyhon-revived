"""Regression coverage for upstream fixes retained alongside state recovery."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from pyhon.diagnose import anonymize_data, appliance_data
from pyhon.parameter.enum import HonParameterEnum


@pytest.mark.parametrize("value", ["COTTON", "Cotton", "cotton"])
def test_uppercase_enum_values_preserve_wire_value(value):
    parameter = HonParameterEnum("program", {"enumValues": ["COTTON"]}, "settings")
    triggered = Mock()
    parameter.add_trigger("CoTtOn", triggered, "fixture-rule")
    parameter.value = value
    triggered.assert_called_once_with("fixture-rule")
    assert parameter.value == "cotton"
    assert parameter.intern_value == value


def test_anonymized_non_ascii_json_stays_valid_and_masks_account_and_date():
    source = {
        "nickName": "Sèche-linge Łódź",
        "account": "001ABCdef123456XYZ",
        "updated": "2026-11-17 12:34:56",
    }
    result = json.loads(anonymize_data(json.dumps(source, indent=4)))
    assert result["nickName"] != source["nickName"]
    assert result["account"] != source["account"]
    assert result["updated"] == "1970-01-01 00:00:00"


@pytest.mark.asyncio
async def test_archive_exports_appliance_record_in_reimportable_shape(tmp_path):
    topics = "commands attributes command_history statistics maintenance".split()
    api = SimpleNamespace(
        **{f"load_{topic}": AsyncMock(return_value={}) for topic in topics}
    )
    device = SimpleNamespace(
        api=api,
        appliance_type="TD",
        model_id="fixture",
        info={"applianceTypeName": "TD", "attributes": {"model": "fixture"}},
    )
    files = await appliance_data(device, tmp_path)
    record_path = next(path for path in files if path.name == "appliance_data.json")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record == {
        "applianceTypeName": "TD",
        "attributes": [{"parName": "model", "parValue": "fixture"}],
    }
    assert device.info["attributes"] == {"model": "fixture"}
