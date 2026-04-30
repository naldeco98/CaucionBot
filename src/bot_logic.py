import os
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from src.iol_client import IOLClient
from src.telegram_bot import TelegramNotifier

class CaucionBot:
    def __init__(self):
        self.iol = IOLClient()
        self.notifier = TelegramNotifier()
        self.tz = ZoneInfo("America/Argentina/Buenos_Aires")

        # Data Input Variables from Environment
        self.min_balance = float(os.getenv("MIN_BALANCE_ARS", 1000))
        self.reserve_cash = float(os.getenv("RESERVE_CASH_ARS", 0)) # Cash to keep liquid
        self.dry_run = os.getenv("DRY_RUN", "True").lower() == "true"

    async def run_once(self):
        # Ejecuta una iteración de la lógica del bot.
        try:
            now = datetime.now(self.tz)
            print(f"[{now}] Iniciando chequeo de cauciones (Hora ART)...")
            
            # Cut-off Time check (16:00)
            if now.hour >= 16:
                msg = "⏳ Horario límite alcanzado (16:00). Abortando para evitar fondos ociosos sin colocar."
                print(msg)
                return

            # 1. Obtener saldo (C)
            total_balance = await self.iol.get_available_balance()
            # Check Liquidity Needs (Reserve cash if required)
            balance = total_balance - self.reserve_cash            
            
            print(f"Saldo total: ${total_balance:,.2f} ARS | Reservado: ${self.reserve_cash:,.2f} ARS")
            print(f"Saldo a invertir: ${balance:,.2f} ARS")
            
            if balance < self.min_balance:
                print(f"⚠️ Saldo a invertir insuficiente (${balance:,.2f} ARS). Mínimo: ${self.min_balance}")
                return

            # 2. Obtener mejores tasas (TNA_m)
            rates = await self.iol.get_caucion_rates()

            if not rates or not rates.get("titulos"):
                await self.notifier.send_message("❌ No se pudieron obtener las tasas de cauciones.")
                return

            best_option = None
            for r in rates.get("titulos", []):
                symbol = r.get('simbolo', '')
                try:
                    days = int(''.join(filter(str.isdigit, symbol))) if any(c.isdigit() for c in symbol) else 1
                except:
                    days = 1
                
                market_tna = r.get('ultimoPrecio', 0)
                if market_tna == 0: continue

                if not best_option or market_tna > best_option['market_tna']:
                    best_option = {
                        'symbol': symbol,
                        'term_days': days,
                        'market_tna': market_tna,
                        'raw_data': r
                    }

            if not best_option:
                msg = "ℹ️ No hay opciones viables para operar."
                print(msg)
                await self.notifier.send_message(msg)
                return

            # 3. Execution Strategy (Limit Order + Laddering)
            target_rate = best_option['market_tna']
            
            # Intentamos buscar el Ask en las puntas si están disponibles
            puntas = best_option['raw_data'].get('puntas', [])
            if puntas:
                # En cauciones, queremos la punta de venta (quien coloca)
                # Si queremos ser competitivos, nos ponemos un escalón debajo del mejor Ask actual.
                asks = [p.get('precioVenta') for p in puntas if p.get('precioVenta')]
                if asks:
                    target_rate = min(asks) - 0.1
            
            print(f"Ejecutando: {best_option['symbol']} | TNA Objetivo: {target_rate}%")
            
            result = await self.iol.place_caucion_order(
                amount=balance, 
                rate=target_rate, 
                term_days=best_option['term_days'], 
                dry_run=self.dry_run
            )
            
            # 4. Notificar
            if result.get("status") == "success":
                mode = "[MODO PRUEBA]" if self.dry_run else "[REAL]"
                msg = (f"✅ {mode} Caución colocada.\n"
                       f"💰 Invertido: ${balance:,.2f} ARS\n"
                       f"📈 Tasa: {target_rate}%\n"
                       f"🗓️ Plazo: {best_option['term_days']} día(s)")
                await self.notifier.send_message(msg)
                print(f"Log: TNA {target_rate}% colocada con éxito.")
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
