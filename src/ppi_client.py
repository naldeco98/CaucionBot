import os
import asyncio
import logging
import decimal
from datetime import datetime
from dotenv import load_dotenv
from ppi_client.ppi import PPI
from ppi_client.models.order_confirm import OrderConfirm

logger = logging.getLogger(__name__)

load_dotenv()

class PPIClient:
    """
    Wrapper sobre la librería oficial ppi-client para Portfolio Personal Inversiones.
    Mantiene la interfaz asincrónica para compatibilidad con el resto del bot.
    """
    
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.getenv("PPI_API_KEY")
        self.api_secret = api_secret or os.getenv("PPI_API_SECRET")
        self.account_number = os.getenv("PPI_ACCOUNT_NUMBER")
        
        # Determinamos si usar sandbox basado en DRY_RUN o PPI_BASE_URL
        # El cliente oficial usa un booleano para sandbox.
        dry_run_env = os.getenv("DRY_RUN", "true").lower() == "true"
        base_url = os.getenv("PPI_BASE_URL", "")
        is_sandbox = dry_run_env or "sandbox" in base_url.lower()
        
        self.ppi = PPI(sandbox=is_sandbox)
        self._is_logged_in = False

    async def _ensure_auth(self):
        """Asegura que la sesión esté autenticada."""
        if not self._is_logged_in:
            try:
                # Login es una operación bloqueante en la librería oficial
                await asyncio.to_thread(self.ppi.account.login_api, self.api_key, self.api_secret)
                self._is_logged_in = True
                logger.info("Autenticación exitosa con el cliente oficial de PPI.")
                
                # Si no hay número de cuenta configurado, intentamos detectar el primero disponible
                if not self.account_number:
                    accounts = await asyncio.to_thread(self.ppi.account.get_accounts)
                    if accounts and len(accounts) > 0:
                        self.account_number = accounts[0].get('accountNumber')
                        logger.info(f"Cuenta detectada automáticamente: {self.account_number}")
                    else:
                        logger.error("No se encontraron cuentas comitentes disponibles.")
            except Exception as e:
                logger.error(f"Error al autenticar en PPI: {e}")
                raise

    async def close(self):
        """
        No se requiere cierre explícito de sesión en la librería oficial (usa requests),
        pero se mantiene el método para compatibilidad de interfaz.
        """
        pass

    async def get_available_balance(self):
        """Obtiene el saldo disponible en pesos (ARS) con liquidación inmediata."""
        try:
            await self._ensure_auth()
            balances = await asyncio.to_thread(self.ppi.account.get_available_balance, self.account_number)
            
            # Buscamos ARS en Inmediato
            for balance in balances:
                if balance.get('symbol') == 'ARS' and balance.get('settlement') == 'Inmediato':
                    return float(balance.get('amount', 0.0))
            
            # Fallback a cualquier ARS si no hay 'Inmediato'
            for balance in balances:
                if balance.get('symbol') == 'ARS':
                    return float(balance.get('amount', 0.0))
            
            return 0.0
        except Exception as e:
            logger.error(f"Error al obtener saldo PPI: {e}")
            return 0.0

    async def get_caucion_rates(self):
        """
        Obtiene las tasas de cauciones actuales.
        Simula la estructura esperada por la lógica del bot.
        """
        try:
            await self._ensure_auth()
            results = {"titulos": []}
            
            # Consultamos los plazos más operados
            for plazo in ["1", "7"]:
                try:
                    # En el cliente oficial, el ticker es "PESOS" y el plazo es el settlement
                    data = await asyncio.to_thread(
                        self.ppi.marketdata.current, 
                        "PESOS", "CAUCIONES", plazo
                    )
                    
                    if data and data.get('lastPrice'):
                        titulo = {
                            "simbolo": f"PESOS - {plazo} DIA{'S' if int(plazo) > 1 else ''}",
                            "ultimoPrecio": float(data.get('lastPrice')),
                            "puntas": []
                        }
                        
                        # Mapeamos la mejor punta de compra y venta
                        bids = data.get('bids', [])
                        offers = data.get('offers', [])
                        if bids or offers:
                            punta = {}
                            if bids: punta["precioCompra"] = float(bids[0].get('price'))
                            if offers: punta["precioVenta"] = float(offers[0].get('price'))
                            titulo["puntas"].append(punta)
                        
                        results["titulos"].append(titulo)
                except Exception:
                    # Es normal que algunos plazos no tengan mercado en ese momento
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Error al obtener tasas de cauciones: {e}")
            return {"titulos": []}

    async def place_caucion_order(self, amount, rate, term_days=1, ticker=None, dry_run=True):
        """
        Coloca una orden de caución (Venta para colocadora).
        """
        if dry_run:
            logger.info(f"[DRY RUN] Colocando caución: {amount} ARS a {rate}% TNA (Plazo: {term_days} días)")
            return {"status": "success", "order_id": "DRY_RUN_ID", "dry_run": True}

        try:
            await self._ensure_auth()
            
            # Construimos el modelo de confirmación de orden
            order_confirm = OrderConfirm(
                accountNumber=self.account_number,
                ticker="PESOS",
                quantity=int(amount),
                price=decimal.Decimal(str(rate)),
                instrumentType="CAUCIONES",
                quantityType="MONTO",
                operationType="LIMIT",
                operationTerm="DAY",
                operationMaxDate=datetime.now(),
                operation="SELL", # SELL para colocar (prestar dinero)
                settlement=str(term_days),
                disclaimers=[],
                externalId=None
            )
            
            # Ejecutamos la orden
            response = await asyncio.to_thread(self.ppi.orders.confirm, order_confirm)
            return {"status": "success", "data": response}
            
        except Exception as e:
            logger.error(f"Error al colocar orden de caución: {e}")
            return {"status": "error", "message": str(e)}
