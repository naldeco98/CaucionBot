import os
import asyncio
import aiohttp
import datetime
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

class PPIClient:
    # Base URL for Production. For Sandbox use: https://sandbox.api.portfoliopersonal.com
    DRY_RUN = os.getenv("DRY_RUN", "true")
    if DRY_RUN == "true":
        BASE_URL = os.getenv("PPI_BASE_URL", "https://sandbox.api.portfoliopersonal.com")
    else:
        BASE_URL = os.getenv("PPI_BASE_URL", "https://api.portfoliopersonal.com")

    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.getenv("PPI_API_KEY")
        self.api_secret = api_secret or os.getenv("PPI_API_SECRET")
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
        url = f"{self.BASE_URL}/api/v1/Account/Login"
        headers = {
            "ApiKey": self.api_key,
            "ApiSecret": self.api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            async with session.post(url, headers=headers, json={}) as response:
                if response.status == 200:
                    res_json = await response.json()
                    self.access_token = res_json.get("accessToken")
                    # El token de PPI suele durar 30-60 min. 
                    # Si no viene expiry, asumimos 30 min por seguridad.
                    expires_in = 1800 
                    self.token_expiry = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 60)
                    logger.info("Login en PPI exitoso.")
                else:
                    error_text = await response.text()
                    raise Exception(f"Error de autenticación en PPI: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Excepción durante el login en PPI: {e}")
            raise

    async def get_available_balance(self):
        """Obtiene el saldo disponible en pesos para operar."""
        try:
            await self._ensure_auth()
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v1/Account/Balance"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    balances = await response.json()
                    # PPI devuelve una lista de balances por moneda y liquidación
                    for balance in balances:
                        # Buscamos pesos en liquidación inmediata (Inmediato)
                        if balance.get('currency') == 'ARS' and balance.get('settlement') == 'Inmediato':
                            return balance.get('available', 0.0)
                    # Si no encontramos Inmediato, buscamos cualquier ARS disponible
                    for balance in balances:
                        if balance.get('currency') == 'ARS':
                            return balance.get('available', 0.0)
                    return 0.0
                else:
                    logger.error(f"Error al obtener saldo PPI: {response.status}")
                    return 0.0
        except Exception as e:
            logger.error(f"Error al obtener saldo PPI: {e}")
            return 0.0

    async def get_caucion_rates(self):
        """
        Obtiene las tasas de cauciones actuales para pesos.
        PPI requiere consultar por ticker específico o buscar.
        """
        try:
            await self._ensure_auth()
            session = await self._get_session()
            
            # En PPI las cauciones suelen tener el formato "PESOS - X DIAS" o tickers tipo "CA1", "CA7"
            # Vamos a intentar buscar todas las cauciones disponibles en pesos.
            url = f"{self.BASE_URL}/api/v1/MarketData/Search?ticker=PESOS&type=Caucion"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    cauciones = await response.json()
                    # Para cada caución encontrada, obtenemos su cotización actual
                    results = {"titulos": []}
                    for c in cauciones:
                        ticker = c.get('ticker')
                        # Solo nos interesan cauciones en BYMA
                        if c.get('market') != 'BYMA': continue
                        
                        quote_url = f"{self.BASE_URL}/api/v1/MarketData/Current?ticker={ticker}&type=Caucion&settlement=Inmediato"
                        async with session.get(quote_url, headers=headers) as q_resp:
                            if q_resp.status == 200:
                                q_data = await q_resp.json()
                                # Adaptamos al formato que espera bot_logic.py
                                results["titulos"].append({
                                    "simbolo": ticker,
                                    "ultimoPrecio": q_data.get('last'),
                                    "puntas": [
                                        {
                                            "precioCompra": q_data.get('bid'),
                                            "precioVenta": q_data.get('ask')
                                        }
                                    ]
                                })
                    return results
                else:
                    logger.error(f"Error al buscar cauciones PPI: {response.status}")
                    return {"titulos": []}
        except Exception as e:
            logger.error(f"Error al obtener tasas de cauciones PPI: {e}")
            return {"titulos": []}

    async def place_caucion_order(self, amount, rate, term_days=1, ticker=None, dry_run=True):
        """
        Coloca una orden de caución (SELL para colocadora).
        """
        # PPI usa tickers descriptivos. Si no se pasa uno, intentamos deducirlo.
        if not ticker:
            ticker = f"PESOS - {term_days} DIA{'S' if term_days > 1 else ''}"

        if dry_run:
            logger.info(f"[DRY RUN PPI] Colocando caución: {amount} ARS a {rate}% TNA ({ticker})")
            return {"status": "success", "order_id": "DRY_RUN_ID", "dry_run": True}

        try:
            await self._ensure_auth()
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v1/Order/Add"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            payload = {
                "ticker": ticker,
                "quantity": int(amount),
                "price": float(rate),
                "side": "SELL",
                "type": "Limit",
                "validity": "Day",
                "settlement": "Inmediato",
                "assetType": "Caucion"
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
