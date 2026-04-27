import os
import asyncio
import schedule
import time
from datetime import datetime
from src.bot_logic import CaucionBot
from dotenv import load_dotenv

load_dotenv()

async def run_bot_task():
    bot = CaucionBot()
    await bot.run_once()

def job():
    # Ejecutamos el bot de forma asincrónica
    asyncio.run(run_bot_task())

def main():
    print("🚀 CaucionBot iniciado y esperando el horario programado...")
    
    # Programar para las 12:00 cada día (horario donde suele haber buena liquidez)
    schedule.every().day.at("12:00").do(job)
    
    # También podemos hacer una ejecución de prueba al inicio si estamos en DRY_RUN
    if os.getenv("DRY_RUN", "True").lower() == "true":
        print("Ejecutando prueba inicial (DRY_RUN)...")
        job()

    while True:
        schedule.run_pending()
        time.sleep(60) # Chequear cada minuto

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario.")
