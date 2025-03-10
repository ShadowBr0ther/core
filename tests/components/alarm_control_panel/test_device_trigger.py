"""The tests for Alarm control panel device triggers."""
from datetime import timedelta

import pytest

from homeassistant.components.alarm_control_panel import DOMAIN
import homeassistant.components.automation as automation
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMED_VACATION,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.helpers import device_registry
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util

from tests.common import (
    MockConfigEntry,
    assert_lists_same,
    async_fire_time_changed,
    async_get_device_automation_capabilities,
    async_get_device_automations,
    async_mock_service,
    mock_device_registry,
    mock_registry,
)
from tests.components.blueprint.conftest import stub_blueprint_populate  # noqa: F401


@pytest.fixture
def device_reg(hass):
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


@pytest.fixture
def entity_reg(hass):
    """Return an empty, loaded, registry."""
    return mock_registry(hass)


@pytest.fixture
def calls(hass):
    """Track calls to a mock service."""
    return async_mock_service(hass, "test", "automation")


@pytest.mark.parametrize(
    "set_state,features_reg,features_state,expected_trigger_types",
    [
        (False, 0, 0, ["triggered", "disarmed", "arming"]),
        (
            False,
            47,
            0,
            [
                "triggered",
                "disarmed",
                "arming",
                "armed_home",
                "armed_away",
                "armed_night",
                "armed_vacation",
            ],
        ),
        (True, 0, 0, ["triggered", "disarmed", "arming"]),
        (
            True,
            0,
            47,
            [
                "triggered",
                "disarmed",
                "arming",
                "armed_home",
                "armed_away",
                "armed_night",
                "armed_vacation",
            ],
        ),
    ],
)
async def test_get_triggers(
    hass,
    device_reg,
    entity_reg,
    set_state,
    features_reg,
    features_state,
    expected_trigger_types,
):
    """Test we get the expected triggers from an alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_hass(hass)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_reg.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        supported_features=features_reg,
    )
    if set_state:
        hass.states.async_set(
            "alarm_control_panel.test_5678",
            "attributes",
            {"supported_features": features_state},
        )
    expected_triggers = []

    expected_triggers += [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        }
        for trigger in expected_trigger_types
    ]
    triggers = await async_get_device_automations(
        hass, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert_lists_same(triggers, expected_triggers)


async def test_get_trigger_capabilities(hass, device_reg, entity_reg):
    """Test we get the expected capabilities from an alarm_control_panel."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_hass(hass)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_reg.async_get_or_create(DOMAIN, "test", "5678", device_id=device_entry.id)
    hass.states.async_set(
        "alarm_control_panel.test_5678", "attributes", {"supported_features": 15}
    )

    triggers = await async_get_device_automations(
        hass, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert len(triggers) == 6
    for trigger in triggers:
        capabilities = await async_get_device_automation_capabilities(
            hass, "trigger", trigger
        )
        assert capabilities == {
            "extra_fields": [
                {"name": "for", "optional": True, "type": "positive_time_period_dict"}
            ]
        }


async def test_if_fires_on_state_change(hass, calls):
    """Test for turn_on and turn_off triggers firing."""
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_PENDING)

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "alarm_control_panel.entity",
                        "type": "triggered",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "triggered - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "alarm_control_panel.entity",
                        "type": "disarmed",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "disarmed - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "alarm_control_panel.entity",
                        "type": "armed_home",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_home - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "alarm_control_panel.entity",
                        "type": "armed_away",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_away - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "alarm_control_panel.entity",
                        "type": "armed_night",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_night - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "alarm_control_panel.entity",
                        "type": "armed_vacation",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "armed_vacation - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is triggered.
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_TRIGGERED)
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert (
        calls[0].data["some"]
        == "triggered - device - alarm_control_panel.entity - pending - triggered - None"
    )

    # Fake that the entity is disarmed.
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_DISARMED)
    await hass.async_block_till_done()
    assert len(calls) == 2
    assert (
        calls[1].data["some"]
        == "disarmed - device - alarm_control_panel.entity - triggered - disarmed - None"
    )

    # Fake that the entity is armed home.
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_ARMED_HOME)
    await hass.async_block_till_done()
    assert len(calls) == 3
    assert (
        calls[2].data["some"]
        == "armed_home - device - alarm_control_panel.entity - disarmed - armed_home - None"
    )

    # Fake that the entity is armed away.
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_ARMED_AWAY)
    await hass.async_block_till_done()
    assert len(calls) == 4
    assert (
        calls[3].data["some"]
        == "armed_away - device - alarm_control_panel.entity - armed_home - armed_away - None"
    )

    # Fake that the entity is armed night.
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_ARMED_NIGHT)
    await hass.async_block_till_done()
    assert len(calls) == 5
    assert (
        calls[4].data["some"]
        == "armed_night - device - alarm_control_panel.entity - armed_away - armed_night - None"
    )

    # Fake that the entity is armed vacation.
    hass.states.async_set("alarm_control_panel.entity", STATE_ALARM_ARMED_VACATION)
    await hass.async_block_till_done()
    assert len(calls) == 6
    assert (
        calls[5].data["some"]
        == "armed_vacation - device - alarm_control_panel.entity - armed_night - armed_vacation - None"
    )


async def test_if_fires_on_state_change_with_for(hass, calls):
    """Test for triggers firing with delay."""
    entity_id = f"{DOMAIN}.entity"
    hass.states.async_set(entity_id, STATE_ALARM_DISARMED)

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": entity_id,
                        "type": "triggered",
                        "for": {"seconds": 5},
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "turn_off {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                (
                                    "platform",
                                    "entity_id",
                                    "from_state.state",
                                    "to_state.state",
                                    "for",
                                )
                            )
                        },
                    },
                }
            ]
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ALARM_DISARMED
    assert len(calls) == 0

    hass.states.async_set(entity_id, STATE_ALARM_TRIGGERED)
    await hass.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=10))
    await hass.async_block_till_done()
    assert len(calls) == 1
    await hass.async_block_till_done()
    assert (
        calls[0].data["some"]
        == f"turn_off device - {entity_id} - disarmed - triggered - 0:00:05"
    )
