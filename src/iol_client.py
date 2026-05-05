import os
import asyncio
import aiohttp
import datetime
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

class IOLClient:
    BASE_URL = "https://api.invertironline.com"

    def __init__(self, username=None, password=None):
        self.username = username or os.getenv("IOL_USERNAME")
        self.password = password or os.getenv("IOL_PASSWORD")
        self.access_token = None
        self.token_expiry = None
        self._session = None

    async def _get_session(self):
        """Devuelve la sesión actual o crea una nueva si no existe."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Cierra la sesión de aiohttp."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _ensure_auth(self):
        """Asegura que tengamos un token válido."""
        now = datetime.datetime.now()
        if self.access_token is None or (self.token_expiry and now >= self.token_expiry):
            await self._login()

    async def _login(self):
        """Realiza el login para obtener el access_token."""
        session = await self._get_session()
        url = f"{self.BASE_URL}/token"
        data = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password"
        }
        try:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    res_json = await response.json()
                    self.access_token = res_json.get("access_token")
                    expires_in = res_json.get("expires_in", 3600)
                    # Restamos 60 segundos de margen
                    self.token_expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 60)
                else:
                    error_text = await response.text()
                    raise Exception(f"Error de autenticación: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Excepción durante el login: {e}")
            raise

    async def get_available_balance(self):
        """Obtiene el saldo disponible en pesos para operar."""
        try:
            await self._ensure_auth()
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v2/estadocuenta"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    estado = await response.json()
                    for cuenta in estado.get('cuentas', []):
                        if cuenta.get('moneda') == 'peso_Argentino':
                            return cuenta.get('disponible', 0.0)
                    return 0.0
                else:
                    logger.error(f"Error al obtener saldo: {response.status}")
                    return 0.0
        except Exception as e:
            logger.error(f"Error al obtener saldo: {e}")
            return 0.0

    async def get_caucion_rates(self):
        """Obtiene las tasas de cauciones actuales para pesos."""
        try:
            await self._ensure_auth()
            session = await self._get_session()
            # En la API v2, se usa 'bcba' como mercado para Argentina
            url = f"{self.BASE_URL}/api/v2/Cotizaciones/Cauciones/argentina/Todos"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error al obtener tasas de cauciones: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error al obtener tasas de cauciones: {e}")
            return []

    async def place_caucion_order(self, amount, rate, term_days=1, dry_run=True):
        """
        Coloca una orden de caución (Venta en el contexto de IOL para colocar capital).
        """
        if dry_run:
            logger.info(f"[DRY RUN] Colocando caución: {amount} ARS a {rate}% TNA por {term_days} días.")
            return {"status": "success", "order_id": "DRY_RUN_ID", "dry_run": True}

        try:
            await self._ensure_auth()
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v2/Operar/Vender"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Símbolo: CA + días + D (ej: CA1D)
            symbol = f"CA{term_days}D"
            
            # Validez hasta el cierre de hoy (16:30 ART)
            validez = datetime.datetime.now().replace(hour=16, minute=30, second=0, microsecond=0).isoformat()

            payload = {
                "simbolo": symbol,
                "cantidad": int(amount),
                "precio": float(rate),
                "plazo": "t0",
                "validez": validez,
                "mercado": "bCBA"
            }

            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"status": "success", "data": data}
                else:
                    error_text = await response.text()
                    return {"status": "error", "message": f"{response.status} - {error_text}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
