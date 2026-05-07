import os
import asyncio
import schedule
import time
import argparse
from datetime import datetime
import logging
from src.bot_logic import CaucionBot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def run_bot_task():
    bot = CaucionBot()
    await bot.run_once()

def job():
    # Ejecutamos el bot de forma asincrónica
    asyncio.run(run_bot_task())

def main():
    parser = argparse.ArgumentParser(description="CaucionBot - Automatización de cauciones bursátiles.")
    parser.add_argument("--force-run", action="store_true", help="Ejecutar el bot inmediatamente al iniciar.")
    args = parser.parse_args()

    logger.info("🚀 CaucionBot iniciado y esperando el horario programado...")
    
    # Programar para las 12:00 cada día (horario donde suele haber buena liquidez)
    schedule.every().day.at("12:00", "America/Argentina/Buenos_Aires").do(job)
    
    # Ejecución inmediata si se solicita por argumento o si estamos en DRY_RUN
    if args.force_run:
        logger.info("Ejecución forzada por argumento --force-run...")
        job()
    elif os.getenv("DRY_RUN", "True").lower() == "true":
        logger.info("Ejecutando prueba inicial (DRY_RUN)...")
        job()

    while True:
        schedule.run_pending()
        time.sleep(60) # Chequear cada minuto

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario.")
