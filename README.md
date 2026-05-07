# CaucionBot 🤖🇦🇷

Bot de automatización para cauciones bursátiles en el mercado argentino a través de **Portfolio Personal Inversiones (PPI)**.

## Características
- 💸 **Inversión Automática**: Coloca cauciones diariamente con el saldo disponible.
- 🕒 **Programación**: Ejecución automática en horarios de mercado.
- 📱 **Notificaciones**: Reportes en tiempo real vía Telegram.
- 🛡️ **Modo Seguro**: Incluye un `DRY_RUN` para probar la lógica sin arriesgar capital.

## Configuración

1. **Clonar el repositorio** (o descargar los archivos).
2. **Crear un entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/macOS
   # o
   venv\Scripts\activate     # En Windows
   ```
3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configurar credenciales**:
   - Copia el archivo `.env.example` a `.env`.
   - Completa tus credenciales de API de PPI (Public Key y Private Key) y el token de tu Bot de Telegram.
   - Para obtener tu `TELEGRAM_CHAT_ID`, puedes usar bots como `@userinfobot`.

## Uso

Para iniciar el bot:
```bash
python main.py
```

Por defecto, el bot iniciará en **Modo Prueba** (`DRY_RUN=True`). Una vez que verifiques que todo funciona correctamente, cambia este valor a `False` en tu archivo `.env`.

## Advertencia
Este software es una herramienta de automatización y no constituye asesoramiento financiero. El uso de APIs para operar en el mercado bursátil conlleva riesgos. Asegúrate de entender cómo funcionan las cauciones antes de activar el bot en modo real.
