# Contexto del Proyecto: CaucionBot

Este archivo proporciona instrucciones críticas y contexto técnico para agentes de IA que trabajen en este repositorio.

## Propósito del Proyecto
Automatizar la colocación de "cauciones bursátiles" (préstamos con garantía de títulos) en el mercado financiero argentino utilizando la API de **Portfolio Personal Inversiones (PPI)**. El objetivo es reinvertir el saldo líquido diariamente para aprovechar el interés compuesto.

## Arquitectura y Estructura
El proyecto sigue una estructura modular para facilitar el mantenimiento y las pruebas:
- `main.py`: Punto de entrada, maneja la programación (scheduling) y el bucle principal.
- `src/ppi_client.py`: Wrapper sobre la API de PPI. Maneja autenticación y operaciones bursátiles.
- `src/telegram_bot.py`: Módulo de comunicación para enviar alertas y estados a través de un bot de Telegram.
- `src/bot_logic.py`: Orquestador que decide cuánto y a qué tasa invertir basándose en el saldo y datos de mercado.

## Mandatos de Desarrollo (Reglas de Oro)
1. **Seguridad de Credenciales**: NUNCA hardcodear usuarios, contraseñas o tokens. Utilizar siempre `load_dotenv()` y acceder vía `os.getenv()`. El archivo `.env` debe estar en `.gitignore`.
2. **Modo Dry Run**: Cualquier lógica que implique una operación financiera DEBE respetar la variable `DRY_RUN`. Si es `True`, la operación se loguea pero NO se envía a la API real.
3. **Asincronía**: La API de PPI y Telegram se manejan de forma asincrónica (`asyncio`). Mantener este patrón en todas las extensiones.
4. **Horarios de Mercado**: Las cauciones solo tienen liquidez real entre las 11:00 y las 16:30 ART. Evitar ejecuciones fuera de este rango para no obtener tasas nulas.
5. **Tipos de Cambio**: El bot opera principalmente en pesos (ARS), pero la arquitectura debe prever una futura expansión a dólares (USD).

## Flujo de Trabajo del Bot
1. Autenticación en PPI.
2. Consulta de saldo líquido disponible en la cuenta (Inmediato).
3. Consulta de cotizaciones de cauciones (TNA).
4. Si el saldo > `MIN_BALANCE_ARS`:
    - Ejecutar orden de "Venta" (colocación) a la mejor tasa.
    - Notificar resultado por Telegram.

## Guía de Estilo
- Seguir PEP 8 para Python.
- Comentarios en español (preferido por el usuario) o inglés técnico claro.
- Documentar métodos con Docstrings explicando parámetros y retornos.

## Dependencias Clave
- `aiohttp`: Interacción con la API REST de PPI.
- `python-telegram-bot`: Notificaciones.
- `schedule`: Planificación de tareas.
- `python-dotenv`: Gestión de configuración.
