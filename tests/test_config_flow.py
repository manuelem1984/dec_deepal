"""Alta de una cuenta: solo con correo electrónico.

Se ejecutan los pasos como lo hace Home Assistant, con un servidor de Deepal
de mentira (``DeepalAuth`` y ``DeepalClient`` sustituidos).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.dec_deepal import config_flow
from custom_components.dec_deepal.api.errors import DeepalConnectionError, DeepalError
from custom_components.dec_deepal.api.models import VehicleInfo

VEHICLES = [
    VehicleInfo(vehicle_id="car1", vin="LS5A3ABE0RA000001", nickname="Changote"),
    VehicleInfo(vehicle_id="car2", vin="LS5A3ABE0RA000002", nickname="Changuito"),
]


async def test_sign_in_with_email_only(hass: HomeAssistant) -> None:
    auth = MagicMock(send_email_code=AsyncMock(), login_email=AsyncMock())
    client = MagicMock(get_vehicles=AsyncMock(return_value=VEHICLES))
    flow = config_flow.DecDeepalConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    # El acceso con teléfono (SMS) ya no existe: ni el paso ni la elección de método.
    assert not hasattr(flow, "async_step_sms") and not hasattr(flow, "async_step_login_method")

    with (
        patch.object(config_flow, "DeepalAuth", return_value=auth),
        patch.object(config_flow, "DeepalClient", return_value=client),
        patch.object(config_flow, "async_get_clientsession", return_value=MagicMock()),
    ):
        # Lo primero, el país: por defecto el de Home Assistant.
        hass.config.country = "PT"
        result = await flow.async_step_user()
        assert result["type"] == "form" and result["step_id"] == "user"
        field = next(iter(result["data_schema"].schema))
        options = result["data_schema"].schema[field].config["options"]
        assert [option["value"] for option in options] == ["de", "es", "fr", "it", "pt"]
        assert field.default() == "pt"
        hass.config.country = "SE"  # sin cuenta posible allí: España
        assert next(iter((await flow.async_step_user())["data_schema"].schema)).default() == "es"
        result = await flow.async_step_user({"country": "pt"})
        assert result["type"] == "form" and result["step_id"] == "email"
        assert flow._country.sales_country == "PT"

        # Sin conexión: se vuelve al formulario con el error.
        auth.send_email_code.side_effect = DeepalConnectionError("sin red")
        result = await flow.async_step_email({"email": " Manuel@Example.com "})
        assert result["step_id"] == "email" and result["errors"] == {"base": "cannot_connect"}
        auth.send_email_code.side_effect = DeepalError("rechazado")
        result = await flow.async_step_email({"email": "manuel@example.com"})
        assert result["errors"] == {"base": "send_code_failed"}

        # Código pedido: introducirlo, reenviarlo o corregir el correo.
        auth.send_email_code.side_effect = None
        result = await flow.async_step_email({"email": " Manuel@Example.com "})
        assert result["type"] == "menu" and result["step_id"] == "code_menu"
        assert result["menu_options"] == ["code", "resend_code", "change_email"]
        assert result["description_placeholders"] == {"destination": "m•••@example.com"}
        auth.send_email_code.assert_awaited_with("manuel@example.com")

        sent = auth.send_email_code.await_count
        assert (await flow.async_step_resend_code())["step_id"] == "code_menu"
        assert auth.send_email_code.await_count == sent + 1
        assert (await flow.async_step_change_email())["step_id"] == "email"

        # Con el código se entra y, al haber dos coches, se pregunta cuáles añadir.
        auth.login_email.side_effect = DeepalError("código malo")
        result = await flow.async_step_code({"auth_code": "000000"})
        assert result["step_id"] == "code" and result["errors"] == {"base": "login_failed"}
        auth.login_email.side_effect = None
        result = await flow.async_step_code({"auth_code": " 123456 "})
        auth.login_email.assert_awaited_with("manuel@example.com", "123456")
        assert result["type"] == "form" and result["step_id"] == "vehicles"
