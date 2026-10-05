"""La cuenta: una sesión compartida por todos los vehículos y su renovación.

Por qué existe esta clase
-------------------------
Una cuenta puede tener varios vehículos, y cada vehículo tiene su propio
coordinador que consulta el servidor por su cuenta. Si el token caduca, todos
lo notarían a la vez y podrían lanzar varias renovaciones simultáneas; el
servidor puede interpretarlo como abuso o invalidar la sesión.

:class:`DeepalAccount` garantiza que:

- **Solo hay una renovación en curso** a la vez. Si llegan varias peticiones
  de renovación mientras una está en marcha, esperan y comparten su resultado.
- **Se respeta la ventana de 30 minutos** de la app oficial entre renovaciones
  "rutinarias" (salvo que el token esté a punto de caducar o se fuerce porque
  el servidor lo rechazó).
- **Cada renovación se guarda** en la entrada de configuración, mediante la
  función ``on_session_changed`` que le pasa Home Assistant.

Lógica tomada de Deepal Alternative (MIT), ver NOTICE.md.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Final, TypeVar

from .auth import DeepalAuth
from .errors import DeepalAuthError, DeepalConnectionError, DeepalError
from .session import DeepalSession
from .transport import DeepalTransport

_LOGGER = logging.getLogger(__name__)

#: Ventana mínima entre renovaciones "rutinarias" (la app usa 30 min).
REFRESH_THROTTLE_SECONDS: Final = 1800.0

#: Espera mínima tras una renovación que NO cambió el token. Cerca de la
#: caducidad el servidor devuelve el mismo token hasta que de verdad lo
#: rota; sin esta espera se pedía una renovación en cada lectura (visto el
#: 05-10-2026: 7 renovaciones en 2 minutos).
UNCHANGED_RETRY_SECONDS: Final = 60.0

T = TypeVar("T")


class DeepalAccount:
    """Sesión de una cuenta, con renovación segura y compartida."""

    def __init__(
        self,
        transport: DeepalTransport,
        *,
        on_session_changed: Callable[[DeepalSession], None] | None = None,
    ) -> None:
        """Crea la cuenta.

        Args:
            transport: transporte HTTP (lleva dentro la sesión).
            on_session_changed: se llama tras cada renovación correcta, para
                guardar los tokens nuevos (en Home Assistant: actualizar
                ``entry.data``).
        """
        self.transport = transport
        self.auth = DeepalAuth(transport)
        self._on_session_changed = on_session_changed
        self._lock = asyncio.Lock()
        self._last_attempt: float | None = None
        # Número de intentos terminados; sirve para saber si otro llamador ya
        # hizo la renovación mientras esperábamos el candado.
        self._attempts = 0
        self._last_error: BaseException | None = None
        # Resultado del último intento real (¿cambió el token?).
        self._last_changed = False

    @property
    def session(self) -> DeepalSession:
        """Sesión actual (la misma instancia que usa el transporte)."""
        return self.transport.session

    # ------------------------------------------------------------------
    # Renovación
    # ------------------------------------------------------------------

    async def refresh(self, *, force: bool = False) -> bool:
        """Renueva el access token si procede.

        Args:
            force: renovar aunque no haya pasado la ventana de 30 min. Se usa
                cuando el servidor acaba de rechazar el token.

        Returns:
            ``True`` si el access token cambió (y por tanto merece la pena
            reintentar lo que falló); ``False`` si se decidió no renovar.

        Raises:
            DeepalAuthError: la renovación falló; hay que volver a iniciar sesión.
            DeepalConnectionError: no hubo red; se puede reintentar más tarde.
        """
        seen = self._attempts
        async with self._lock:
            if self._attempts != seen:
                # Otro llamador renovó mientras esperábamos: compartimos su
                # resultado en vez de lanzar una segunda petición.
                if self._last_error is not None:
                    raise self._last_error
                return self._last_changed
            return await self._refresh_locked(force=force)

    async def _refresh_locked(self, *, force: bool) -> bool:
        """Hace una renovación real. Debe llamarse con el candado cogido."""
        if not force and not self.session.expires_soon() and self._throttled():
            _LOGGER.debug("Renovación omitida: dentro de la ventana de 30 min")
            return False
        if not force and not self._last_changed and self._attempted_within(
            UNCHANGED_RETRY_SECONDS
        ):
            _LOGGER.debug("Renovación omitida: la anterior no cambió el token")
            return False

        previous_token = self.session.access_token
        self._last_attempt = time.monotonic()
        self._last_error = None
        try:
            await self.auth.refresh()
        except DeepalError as err:
            self._attempts += 1
            self._last_changed = False
            _LOGGER.warning("No se pudo renovar la sesión: %s", err)
            if isinstance(err, (DeepalAuthError, DeepalConnectionError)):
                # Sesión rechazada → hay que volver a entrar.
                # Sin red → no es culpa de la sesión; se reintentará más tarde
                # sin pedir al usuario que vuelva a iniciar sesión.
                self._last_error = err
                raise
            self._last_error = DeepalAuthError(f"Renovación fallida: {err}")
            raise self._last_error from err

        self._attempts += 1
        changed = self.session.access_token != previous_token
        self._last_changed = changed
        _LOGGER.debug("Sesión renovada (token cambiado: %s)", changed)
        if changed and self._on_session_changed is not None:
            self._on_session_changed(self.session)
        return changed

    def _throttled(self) -> bool:
        """``True`` si el último intento fue hace menos de 30 min."""
        return self._attempted_within(REFRESH_THROTTLE_SECONDS)

    def _attempted_within(self, seconds: float) -> bool:
        """``True`` si hubo un intento de renovación hace menos de ``seconds``."""
        return (
            self._last_attempt is not None
            and time.monotonic() - self._last_attempt < seconds
        )

    async def ensure_fresh(self) -> None:
        """Renueva de forma preventiva si el token caduca en < 5 min.

        No lanza errores: si falla, la siguiente petición recibirá el rechazo
        del servidor y se gestionará allí.
        """
        if not self.session.refresh_token or not self.session.expires_soon():
            return
        try:
            await self.refresh()
        except DeepalError:
            pass

    # ------------------------------------------------------------------
    # Ejecutar algo con reintento tras renovar
    # ------------------------------------------------------------------

    async def call(self, action: Callable[[], Awaitable[T]]) -> T:
        """Ejecuta ``action``; si falla por sesión, renueva y reintenta una vez.

        ``action`` debe ser una *función* que devuelva una corrutina nueva en
        cada llamada (por ejemplo ``lambda: client.get_vehicles()``), no una
        corrutina ya creada: una corrutina solo se puede esperar una vez.

        Raises:
            DeepalAuthError: si ni tras renovar se acepta la sesión.
        """
        try:
            return await action()
        except DeepalAuthError:
            if not self.session.refresh_token:
                raise
            if not await self.refresh(force=True):
                raise
            return await action()
