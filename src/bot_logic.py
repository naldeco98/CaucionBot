import os
import asyncio
from datetime import datetime
from src.iol_client import IOLClient
from src.telegram_bot import TelegramNotifier

class CaucionBot:
    def __init__(self):
        self.iol = IOLClient()
        self.notifier = TelegramNotifier()
        self.min_balance = float(os.getenv("MIN_BALANCE_ARS", 1000))
        self.dry_run = os.getenv("DRY_RUN", "True").lower() == "true"

    async def run_once(self):
        """Ejecuta una iteración de la lógica del bot."""
        try:
            print(f"[{datetime.now()}] Iniciando chequeo de cauciones...")
            
            # 1. Obtener saldo
            balance = await self.iol.get_available_balance()
            print(f"Saldo disponible: ${balance} ARS")
            
            if balance < self.min_balance:
                msg = f"⚠️ Saldo insuficiente para caucionar (${balance} ARS). Mínimo requerido: ${self.min_balance} ARS."
                print(msg)
                # Podríamos no notificar esto todos los días para no spamear si la cuenta está vacía
                return

            # 2. Obtener mejores tasas
            rates = await self.iol.get_caucion_rates()
            if not rates:
                await self.notifier.send_message("❌ No se pudieron obtener las tasas de cauciones.")
                return

            # Buscamos la mejor tasa para 1 día (o el plazo más corto disponible)
            # El formato de 'rates' de IOL suele ser una lista de cotizaciones.
            # Necesitamos filtrar por plazo y buscar la mejor punta compradora/vendedora.
            
            best_rate = 0
            best_term = 1
            
            # Lógica simplificada: buscamos el primer elemento que sea caución en pesos a 1 día
            # Nota: Esto debe ajustarse según la respuesta real de la API de IOL
            for r in rates:
                # Ejemplo de filtrado (ajustar según realidad de la API)
                if r.get('plazo') == 't0' or '1D' in r.get('simbolo', ''):
                    best_rate = r.get('ultimoPrecio', 0)
                    break
            
            if best_rate == 0:
                # Si no encontramos tasa específica, tomamos la primera disponible como fallback
                # (En un bot real esto sería más robusto)
                best_rate = rates[0].get('ultimoPrecio', 0)
                best_term = rates[0].get('plazo', 1)

            # 3. Colocar orden
            print(f"Mejor tasa encontrada: {best_rate}% TNA para {best_term} día(s)")
            
            result = await self.iol.place_caucion_order(
                amount=balance, 
                rate=best_rate, 
                term_days=best_term, 
                dry_run=self.dry_run
            )
            
            # 4. Notificar
            if result.get("status") == "success":
                mode = "[MODO PRUEBA]" if self.dry_run else "[REAL]"
                msg = (f"✅ {mode} Caución colocada exitosamente.\n"
                       f"💰 Monto: ${balance} ARS\n"
                       f"📈 Tasa: {best_rate}% TNA\n"
                       f"🗓️ Plazo: {best_term} día(s)")
                await self.notifier.send_message(msg)
            else:
                msg = f"❌ Error al colocar caución: {result.get('message')}"
                await self.notifier.send_message(msg)
        finally:
            await self.iol.close()

async def main():
    bot = CaucionBot()
    await bot.run_once()

if __name__ == "__main__":
    asyncio.run(main())
