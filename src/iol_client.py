import os
import asyncio
from iol_api import IOLAPI
from dotenv import load_dotenv

load_dotenv()

class IOLClient:
    def __init__(self, username=None, password=None):
        self.username = username or os.getenv("IOL_USERNAME")
        self.password = password or os.getenv("IOL_PASSWORD")
        self.api = None

    async def _ensure_auth(self):
        if self.api is None:
            self.api = IOLAPI(username=self.username, password=self.password)
            # La librería iol-api suele manejar el login automáticamente en el primer llamado,
            # pero algunas versiones requieren un llamado explícito o se inicializan con credenciales.

    async def get_available_balance(self):
        """Obtiene el saldo disponible en pesos para operar."""
        await self._ensure_auth()
        try:
            estado = await self.api.get_estado_cuenta()
            # El formato suele ser una lista de cuentas o un objeto con saldos
            # Necesitamos extraer el saldo disponible en pesos (ARS)
            for cuenta in estado.get('cuentas', []):
                if cuenta.get('moneda') == 'Peso Argentino':
                    return cuenta.get('disponible', 0.0)
            return 0.0
        except Exception as e:
            print(f"Error al obtener saldo: {e}")
            return 0.0

    async def get_caucion_rates(self):
        """Obtiene las tasas de cauciones actuales para pesos."""
        await self._ensure_auth()
        try:
            # Según la documentación de IOL API v2
            cauciones = await self.api.get_cauciones(mercado="bcba", simbolo="PESOS")
            return cauciones
        except Exception as e:
            print(f"Error al obtener tasas de cauciones: {e}")
            return []

    async def place_caucion_order(self, amount, rate, term_days=1, dry_run=True):
        """
        Coloca una orden de caución (Venta en el contexto de IOL para colocar capital).
        amount: monto en pesos
        rate: TNA (Tasa Nominal Anual)
        term_days: días de plazo (ej. 1 para caución a 1 día)
        dry_run: si es True, no ejecuta la orden real.
        """
        await self._ensure_auth()
        
        symbol = f"CA{term_days}D" # Ejemplo: CA1D para 1 día. Esto puede variar según el broker.
        # En IOL, para colocar dinero se suele usar Venta.
        
        if dry_run:
            print(f"[DRY RUN] Colocando caución: {amount} ARS a {rate}% TNA por {term_days} días.")
            return {"status": "success", "order_id": "DRY_RUN_ID", "dry_run": True}

        try:
            # Este endpoint puede variar o requerir parámetros específicos como cantidad, precio (tasa), etc.
            # Según el Help de IOL: POST /api/v2/Operar/Vender
            # Sin embargo, cauciones a veces tiene su propio endpoint.
            # Verificamos si iol-api tiene un método específico. 
            # Si no, usamos el genérico de vender si es compatible.
            
            # Nota: Colocar caución en IOL a veces se hace vía /api/v2/Operar/Caucion
            # Si iol-api no lo soporta directamente, habría que extenderlo.
            
            # Asumimos por ahora que existe un método o usamos el genérico.
            # result = await self.api.vender(simbolo=symbol, cantidad=amount, precio=rate, plazo="t0")
            
            # ATENCIÓN: Operar cauciones es crítico. En IOL se usa el endpoint de cauciones.
            # Por seguridad, implementaremos una advertencia si el método no está claro.
            print(f"EJECUTANDO ORDEN REAL: {amount} ARS a {rate}% TNA")
            
            # TODO: Validar el método exacto en la librería iol-api para cauciones.
            # result = await self.api.operar_caucion(monto=amount, tasa=rate, dias=term_days)
            
            return {"status": "error", "message": "Método de operación no confirmado plenamente en iol-api. Revisar implementación."}
        except Exception as e:
            print(f"Error al colocar orden: {e}")
            return {"status": "error", "message": str(e)}
