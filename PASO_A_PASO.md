# CryptoLove · Loving Crypto

Entrega del 10/10/2026. Web blanca, corazón rojo animado, texto azul, idiomas EN/ES/FR/DE. Nombre del proyecto: **CryptoLove**; marca de portada: **Loving Crypto**.

## 1. Qué subir y dónde

| Carpeta | Destino | Visibilidad |
|---|---|---|
| `cryptolove-web` | Repositorio GitHub `cryptolove-web` → Render Static Site | Privado por defecto; puedes hacerlo público para el concurso. |
| `cryptolove-server` | Repositorio privado `cryptolove-server` → `/opt/cryptolove` en Hetzner | Privado. |
| Tu carpeta actual `agente_hma_real` | Sigue en Hetzner | Privada; no se sube al repositorio de la web. |

Sube **el contenido** de cada carpeta a la raíz de su repositorio. Activa la visualización de archivos ocultos para incluir `.gitignore` y `.env.example`. Nunca subas `.env`, `data/`, claves, bases de datos, logs o el `config.txt` real. Este paquete no contiene tus credenciales ni tu estrategia privada.

No se han creado repositorios ni desplegado servicios. Tú los subes y los despliegas.

## 2. Decisiones importantes ya implementadas

- **Capital mínimo: 100 USDC.** Se ve en grande. El backend impide nuevas entradas por debajo de ese patrimonio; no suspende cierres y protecciones de posiciones existentes.
- **Comisión predeterminada: 1% del beneficio neto**, solo cuando el rendimiento neto de la operación cerrada es **estrictamente superior al 1% sobre el margen inicial**. Beneficio neto = PnL de fills de cierre − comisiones de entrada/salida + funding atribuido. Un resultado exacto del 1% no paga. Ejemplo: margen 1.000, beneficio neto 50 → comisión 0,50 USDC. El cálculo usa decimales y redondea hacia abajo a 6 decimales.
- Si querías **1% del capital/margen invertido**, configura `FEE_BASIS=margin` **antes de registrar usuarios**. El mismo ejemplo cobraría 10 USDC. La base aceptada queda asociada a cada perfil; cambiar el entorno no cambia retroactivamente contratos existentes. No es 1% del nominal apalancado.
- **Limitación de cobro:** el agente API de Hyperliquid no tiene permiso para transferir comisiones a otra wallet. La comisión builder depende del nominal y no cumple esta regla. Este paquete calcula la comisión automáticamente, muestra el estado **pendiente**, y el usuario pulsa **Pagar comisiones pendientes** y firma un `usdSend` en MetaMask. Solo una respuesta aceptada de Hyperliquid la marca pagada. **No incluye cobro automático sin firma.** No se piden claves principales para sortear esta limitación.
- **Impago: plazo de 48 horas y recordatorios cada 8 horas.** El área privada muestra importe pendiente, fecha límite UTC y cuenta atrás. Se envía un correo inicial y recordatorios a las 8, 16, 24, 32 y 40 horas. A las 48 horas, si queda una comisión vencida sin pagar, se desactiva y borra el perfil automáticamente. Véase el apartado 10.1 para actualización, alcance del borrado y posiciones abiertas.
- El botón de área privada solo aparece tras autenticar una cuenta confirmada. El servidor también exige sesión y separa los datos de cada usuario.
- Todos los correos llevan una baja completa. Abrir el enlace muestra una confirmación: los escáneres de enlaces de los proveedores de correo no borran cuentas al visitar una URL.

## 3. Dominios y DNS

Usa un dominio tuyo, por ejemplo `tudominio.com` (ejemplo, no un dominio comprado):

- `https://tudominio.com`: web estática de Render.
- `https://api.tudominio.com`: API en Hetzner, con un registro **A** hacia la IP de tu servidor.

El dominio de la web y el subdominio de la API deben pertenecer al mismo dominio principal para evitar el bloqueo de cookies de terceros. Usar `algo.onrender.com` y una API de otro dominio puede impedir el inicio de sesión en navegadores que bloqueen esas cookies. Todos los enlaces y cookies requieren HTTPS.

En Render añade tu dominio en **Settings → Custom Domains** y crea los registros DNS que te indique Render. Para `api.tudominio.com`, abre los puertos 80/443 en el firewall de Hetzner. No expongas el puerto interno de Uvicorn.

## 4. Instalar el servidor en Hetzner

Necesitas Ubuntu/Debian con Python **3.10 o superior** y acceso sudo. Conserva tu agente actual y su `estado_real`: no los sustituyas ni los borres.

Copia los archivos de `cryptolove-server` a `/opt/cryptolove`. Por ejemplo, desde tu ordenador, después de descomprimir:

```bash
scp -r cryptolove-server usuario@IP_DE_HETZNER:~/
```

En Hetzner:

```bash
sudo mkdir -p /opt/cryptolove
sudo cp -a ~/cryptolove-server/. /opt/cryptolove/
cd /opt/cryptolove
sudo bash install.sh
sudo nano /opt/cryptolove/.env
```

El instalador crea usuario de servicio, entorno Python, claves de cifrado locales y dos unidades systemd. **No arranca los servicios.** No imprime las claves generadas. Repetirlo conserva `.env`; no lo borres ni regeneres `ENCRYPTION_KEY`, porque dejarías de poder descifrar los agentes ya autorizados.

Rellena `.env`:

```dotenv
FRONTEND_URL=https://tudominio.com
API_PUBLIC_URL=https://api.tudominio.com
DATA_DIR=/opt/cryptolove/data
HL_NETWORK=testnet
TRADING_ENABLED=false
MAX_SUBSCRIBERS=10
STRATEGY_DIR=/opt/agente_hma_real
STRATEGY_CONFIG=/opt/agente_hma_real/config_cryptolove_testnet.txt
FEE_BASIS=profit
TREASURY_ADDRESS=TU_WALLET_RECEPTORA_DE_COMISIONES
PUBLIC_MASTER_WALLET=TU_DIRECCION_PUBLICA_REAL_A_VERIFICAR
GOOGLE_CLIENT_ID=TU_CLIENT_ID.apps.googleusercontent.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=tu_correo@gmail.com
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD="CONTRASEÑA_DE_APLICACION"
```

`APP_SECRET` y `ENCRYPTION_KEY` ya los rellena el instalador; consérvalos. No uses la dirección del agente API como `PUBLIC_MASTER_WALLET`: debe ser la cuenta/subcuenta que realmente opera. No he asumido que tu wallet de comisiones o la que usaste en otros proyectos sea tu cuenta actual.

`TREASURY_ADDRESS` recibe USDC **dentro de Hyperliquid**, no en Ethereum/Arbitrum mediante una transferencia ERC-20. Configura una dirección válida de recepción. Los usuarios necesitan saldo transferible suficiente para pagar; las posiciones que ocupan margen pueden impedir un pago temporalmente.

Con SMTP de Gmail utiliza una contraseña de aplicación. También puedes usar otro proveedor SMTP con TLS. El puerto 587 usa STARTTLS y el 465 SSL. Credenciales con espacios o `#` deben ir entre comillas en `.env`; no uses variables `export` ni comandos shell en ese archivo. Configura SPF/DKIM/DMARC de tu proveedor para que lleguen los mensajes.

### Dar acceso de lectura al motor existente

`STRATEGY_DIR` debe contener los archivos de tu agente actual: `agente_real.py`, `cuenta.py`, `motor.py`, `infraestructura.py`, `estrategia_original.py`. **No se reemplazan.** La integración ha sido comprobada contra el paquete Linux de `agente_hma_real` de la conversación anterior; una versión distinta requiere comprobar compatibilidad.

Si está en `/home/toni/agente_hma_real`, cambia ambas rutas del `.env`. El usuario `cryptolove` necesita atravesar las carpetas padre y leer los cinco módulos y el config; no necesita escribir en la carpeta del agente principal. Puedes dar ACL solo de lectura:

```bash
sudo apt-get install -y acl
sudo setfacl -m u:cryptolove:x /home/toni
sudo setfacl -m u:cryptolove:rx /home/toni/agente_hma_real
sudo setfacl -m u:cryptolove:r /home/toni/agente_hma_real/agente_real.py
sudo setfacl -m u:cryptolove:r /home/toni/agente_hma_real/cuenta.py
sudo setfacl -m u:cryptolove:r /home/toni/agente_hma_real/motor.py
sudo setfacl -m u:cryptolove:r /home/toni/agente_hma_real/infraestructura.py
sudo setfacl -m u:cryptolove:r /home/toni/agente_hma_real/estrategia_original.py
sudo setfacl -m u:cryptolove:r /home/toni/agente_hma_real/config_cryptolove_testnet.txt
```

Sustituye `toni` y las rutas por las reales. Si hay más directorios padre, necesitan permiso de paso. Si usas `/opt/agente_hma_real`, aplica los permisos a esa ruta.

Haz una copia del config para testnet. En ella cambia únicamente `API` a `https://api.hyperliquid-testnet.xyz/info` y deja vacíos los campos de wallet API y correo. `HL_NETWORK` y `API` deben coincidir. Las reglas de la estrategia permanecen iguales. Cada suscriptor tiene su propia clave cifrada, estado, fills y caché dentro de `data/subscribers/`; no comparte el estado de tu cuenta principal.

### HTTPS con Caddy

Edita `/etc/caddy/Caddyfile` y **añade** este bloque con tu dominio real. Conserva los bloques de otros proyectos:

```caddy
api.tudominio.com {
    request_body {
        max_size 20KB
    }
    reverse_proxy 127.0.0.1:8091
    header {
        X-Content-Type-Options nosniff
        Referrer-Policy no-referrer
    }
}
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl enable --now cryptolove-api cryptolove-worker
curl https://api.tudominio.com/health
```

Debe responder `{"ok":true}`. Si el puerto 8091 está ocupado, cambia el puerto tanto en la unidad `cryptolove-api.service` como en Caddy y ejecuta `sudo systemctl daemon-reload`.

## 5. Google Sign-In

En [Google Cloud Console](https://console.cloud.google.com/): crea un proyecto o utiliza el tuyo; configura la pantalla de consentimiento de Google Auth Platform y crea un **OAuth Client ID de aplicación web**.

- En **Authorized JavaScript origins**, añade exactamente `https://tudominio.com`. Si mantienes otro dominio de acceso, su origen también necesita configuración coherente.
- Copia el Client ID a `GOOGLE_CLIENT_ID` de `.env`.
- Este flujo usa Google Identity Services con popup y credencial; no necesita un Client Secret en la web ni una redirección OAuth de servidor.
- Si el proyecto de Google está en pruebas, añade los correos de prueba o publícalo para permitir a otros usuarios entrar.

También se envía confirmación de correo a los registros con Google. Después de confirmar, se vuelve a entrar con Google. Una cuenta creada con contraseña no se fusiona automáticamente con una identidad Google del mismo email: se entra con su contraseña. Nunca se pide al usuario su contraseña de Google.

Reinicia tras cambiar `.env`:

```bash
sudo systemctl restart cryptolove-api cryptolove-worker
```

## 6. Publicar la web en Render

1. Edita `cryptolove-web/config.js`: cambia la URL por `https://api.tudominio.com`.
2. Crea el repositorio GitHub y sube el contenido de `cryptolove-web` a su raíz. Puede ser privado. El código servido al navegador siempre será visible para sus visitantes.
3. En Render: **New → Blueprint**, conecta el repositorio y utiliza su `render.yaml`. Alternativamente, **New → Static Site** con los ajustes de abajo.
4. Conecta tu dominio según el paso 3. Usa ese mismo origen exacto en `.env` y en Google.

| Ajuste | Valor |
|---|---|
| Build Command | `mkdir -p dist && cp index.html style.css app.js config.js logo.svg history.json dist/` |
| Publish Directory | `dist` |
| Root Directory | Vacío si subes el contenido a la raíz. |

Los encabezados de `render.yaml` protegen el sitio y permiten el popup de Google. En el modo manual cópialos a Settings → Headers. La web es estática: no lleva contraseñas SMTP, claves de wallet, usuarios ni datos privados. Los datos de `history.json` sí son públicos al visitar la web.

## 7. Comprobar el flujo antes de activar dinero real

Con `TRADING_ENABLED=false`, las nuevas entradas permanecen bloqueadas. El correo, registro, datos públicos, vinculación y firmas funcionan con la configuración real del servidor.

1. Regístrate con usuario, correo y contraseña de 12 caracteres. Confirma el correo y entra.
2. Repite el registro con una cuenta Google de prueba y confirma su correo.
3. Conecta MetaMask y firma la prueba de propiedad de la wallet. Esta firma no autoriza trading todavía.
4. Autoriza la estrategia: MetaMask muestra `HyperliquidTransaction:ApproveAgent`, el agente CryptoLove y la red. **No solicita tu seed ni la clave privada principal.**
5. Para probar operaciones en testnet, usa una cuenta de testnet con al menos 100 USDC de prueba. No mezcles operaciones manuales ni de otros bots en esa cuenta.
6. Establece `TRADING_ENABLED=true` manteniendo `HL_NETWORK=testnet` y config de testnet, y reinicia. Se esperan nuevas señales del motor; no se inventan señales ni se ejecutan señales antiguas. El mercado y las monedas de testnet pueden diferir de mainnet.
7. Comprueba apertura, stops, cierre, correo y tabla privada. La contabilidad espera fills completos y al menos 60 segundos tras el último cierre antes de calcular comisión/funding.
8. Comprueba que pausar bloquea entradas y conserva la gestión de posiciones; bajar de 100 USDC también bloquea entradas.
9. Prueba la baja con el perfil de prueba: los correos y escrituras de cuenta se detienen; el supervisor elimina el estado privado tras parar su proceso. Revoca después el agente en Hyperliquid.

**Pasar a mainnet:** termina/gestiona todas las posiciones de prueba; elimina los perfiles de testnet y revoca sus agentes antes de cambiar red. No migres autorizaciones de testnet a mainnet. Configura `HL_NETWORK=mainnet`, usa una copia de tu config con `API=https://api.hyperliquid.xyz/info`, reinicia y registra/autoriza de nuevo las wallets reales. Mantén la clave de cifrado. Nunca cambies de red conservando posiciones o perfiles activos. Tu agente principal sigue funcionando donde ya estaba.

La integración ejecuta **instancias del mismo motor** por suscriptor; no copia a ciegas el tamaño de tu cuenta principal. Las reglas y parámetros son los mismos, pero saldo, latencia, entrada en el servicio y ejecuciones pueden producir operaciones distintas. La instancia empieza desde su arranque y no abre retrospectivamente una posición que tu cuenta principal ya tenía.

## 8. Rendimiento real desde el 10/10/2026 y verificación independiente

Rellena `PUBLIC_MASTER_WALLET` con la dirección pública de **tu cuenta real operativa**. La consulta es pública y de solo lectura. El indicador siempre utiliza mainnet, aunque estés probando suscriptores en testnet.

- Inicio solicitado: **10/10/2026 00:00 Europe/Madrid**, equivalente a **09/10/2026 22:00 UTC**.
- Se consultan datos públicos `portfolio` de Hyperliquid cada 5 minutos y se conservan muestras en Hetzner.
- La cifra grande muestra el **rendimiento estimado de la cuenta de perpetuos**, incluyendo beneficio/pérdida flotante, comisiones y funding reflejados en su patrimonio. **No es exclusivamente la rentabilidad de operaciones cerradas.**
- Se usa Modified Dietz: `(patrimonio_final − patrimonio_inicial − aportaciones_netas) / (patrimonio_inicial + aportaciones_ponderadas) × 100`. Los flujos se infieren de cambios de patrimonio y PnL del exchange entre muestras. Su momento se aproxima al final del intervalo. Esto evita contar un depósito como beneficio, pero no equivale a una TWR exacta.
- Se conserva el primer punto disponible dentro de los 15 minutos siguientes al inicio y se muestra su hora efectiva. Si no existe, se muestra **pendiente de datos verificables**, no 0% inventado. Los valores PnL de distintas ventanas se alinean únicamente con muestras solapadas compatibles.
- Los datos antiguos se indican como tales. Datos originales disponibles en `https://api.tudominio.com/public/audit`; indicador calculado en `/public/performance`.
- El botón abre **`https://hypurrscan.io/address/TU_WALLET`**. Cualquier visitante puede consultar el explorador sin iniciar sesión en CryptoLove. No hay que darle claves ni conectar la wallet allí para consultar la dirección.

Hypurrscan aporta verificación independiente de la cuenta y su actividad; **no es una auditoría certificada de CryptoLove ni una certificación de rentabilidad**. Puede utilizar otra ventana o metodología de rendimiento. Para que el indicador represente solo la estrategia, usa una cuenta dedicada; actividad manual en la cuenta maestra también afecta al resultado.

## 9. Simulación interactiva del Excel

Se incluyen **242 operaciones ejecutadas y cerradas**, con cierres en 2025 y 2026: 122 en 2025 y 120 en 2026. Último cierre: **07/10/2026 15:00 UTC**. Se excluyen 170 filas «No ejecutada» de todo el archivo y 103 operaciones fuera del periodo. No se fabrican meses que el Excel no contiene. «Dos últimos años» se ha interpretado como los años naturales **2025 y 2026 hasta el último dato**, no 24 meses móviles.

Reproductor con play/pausa, reinicio, velocidad, selección del año, escala lineal/logarítmica y desplazamiento por operación. Muestra moneda, apertura UTC, cierre UTC y beneficio/pérdida del precio de esa operación.

El índice parte de 100 y aplica `índice = índice_anterior × (1 + columna_H / 100)` en cada cierre. Incluye ganancias y pérdidas. **No equivale al saldo de la columna P**, ni reproduce asignación simultánea de capital, apalancamiento, fees o deslizamiento. El efecto compuesto del Excel es extraordinariamente alto; se mantiene identificado como simulación ilustrativa y separado del resultado real. No se ha validado ni corregido la estrategia que produjo el Excel.

Las aperturas usan la fecha UTC explícita de la columna Q. Las fechas locales F/G se han contrastado con Europe/Madrid; los cierres G se convierten a UTC con precisión de minutos. Se verificó la correspondencia de las 515 aperturas del archivo.

Para actualizar los datos con otro Excel de las mismas columnas, en tu ordenador:

```bash
cd cryptolove-web
python3 import_history.py /ruta/al/nuevo.xlsx --start-year 2025 --end-year 2026
```

Sube el `history.json` actualizado. No necesitas subir el Excel ni instalar librerías para importarlo.

## 10. Baja, pausa, privacidad y operación diaria

**Pausa:** `active=0` impide nuevas entradas. El proceso sigue gestionando salidas/stops existentes.

**Baja:** el perfil se desactiva bajo el mismo bloqueo que protege envíos de órdenes y correos. Se borran email, contraseña, claves API cifradas, sesiones, tokens, historial privado y cola de correo. No se puede dar por revocada una autorización on-chain sin firma de la wallet principal: el usuario debe revocar **CryptoLove** en la página API de Hyperliquid. La baja no ejecuta un cierre forzoso. Las órdenes nativas permanecen, pero los stops lógicos/HMA requieren un agente activo y dejan de gestionarse al darse de baja.

El supervisor termina el proceso y elimina su carpeta de datos; si el supervisor está detenido, esa limpieza de archivos se completa cuando vuelva a arrancar. No se envía un correo después de la baja. Ningún sistema puede retirar un correo ya entregado, borrar la blockchain ni eliminar instantáneamente copias externas del disco: si activas backups/snapshots, su retención y eliminación también deben contemplar las bajas. No se configuran backups de datos personales en este paquete.

Comandos habituales:

```bash
sudo systemctl status cryptolove-api cryptolove-worker
sudo journalctl -u cryptolove-worker -n 80 --no-pager
sudo journalctl -u cryptolove-api -n 80 --no-pager
sudo systemctl restart cryptolove-api cryptolove-worker
```

`MAX_SUBSCRIBERS=10` es un límite inicial conservador de procesos, no una garantía de capacidad. Cada suscriptor usa el feed y consultas del motor original: aumenta el límite únicamente tras medir recursos y límites de API. Una desconexión/revocación deja de permitir trading; se avisa y se reintenta, sin reenviar órdenes cuyo resultado sea incierto.

Si un pago de comisión devuelve timeout, se queda **incierto** y bloquea un segundo pago. Comprueba el movimiento concreto en Hyperliquid antes de reconciliar manualmente el registro. No borres una factura incierta para forzar otro cobro. No hay cobro periódico, comisión por pérdidas ni comisión solo por registrarse.

## 10.1. Avisos y baja automática por comisiones pendientes (versión 1.1)

**No hay cobro automático:** el cliente sigue firmando el pago en MetaMask. Este cambio añade el plazo, los correos y la baja solicitados; no impide técnicamente que alguien vuelva a registrarse.

### Plazo y recordatorios

- Cada comisión obtiene su fecha de inicio cuando el servidor registra el cierre reconciliado y la comisión positiva. El plazo es de **48 horas exactas**, no dos cambios de fecha del calendario.
- El vencimiento visible es el de la **comisión pendiente más antigua**. Las comisiones nuevas conservan su propio plazo; no aplazan la deuda anterior. Pausar la estrategia, reiniciar, cerrar sesión o volver a entrar no reinicia los plazos.
- Se envía un **correo inicial**, seguido de recordatorios a las **8, 16, 24, 32 y 40 horas**. A las 48 horas se aplica la baja; no se envía un correo posterior con el perfil eliminado.
- Los mensajes incluyen importe exacto en USDC, vencimiento UTC, tiempo restante, enlace al área privada, instrucciones de MetaMask y consecuencias de la baja. Se envían en español e inglés. El aviso web, FAQ y autorización están en inglés, español, francés y alemán.
- El pago confirmado cancela los recordatorios de la deuda pagada. Si durante la firma surgió otra comisión no incluida en el importe autorizado, esa comisión conserva su propio vencimiento.
- La planificación queda en SQLite y sobrevive a reinicios. Si el servicio estuvo detenido, al volver se envía solo el recordatorio vigente; no se acumula una ráfaga de avisos atrasados. Si ya venció, se aplica la baja al reanudarse.
- SMTP debe estar bien configurado. Los fallos de envío se reintentan con espera progresiva; no cambian el vencimiento. La entrega efectiva depende del proveedor de correo y no se puede garantizar a una hora exacta.
- Un pago `submitting` o `uncertain` suspende **recordatorios y baja automática**, evitando borrar una cuenta que puede haber pagado. Se debe reconciliar el movimiento en Hyperliquid. No se libera un pago incierto por tiempo ni se solicita pagarlo otra vez. Si se confirma, se marcan pagadas sus operaciones; si se demuestra rechazado, se conserva el plazo original.

### Baja y alcance del borrado

El supervisor procesa los vencimientos en cada ciclo (espera habitual de 2 segundos, más el tiempo de las tareas). No necesita que el cliente mantenga la web abierta. **El servicio debe estar ejecutándose** para enviar correos y aplicar la baja.

Al vencer, el mismo bloqueo que protege los pagos y las escrituras de cuenta desactiva el perfil. Se eliminan correo, contraseña, identidad Google, wallet vinculada, clave API cifrada, sesiones, tokens, desafíos de firma, operaciones privadas, facturas y correos en cola. El supervisor detiene el proceso del cliente antes de eliminar su carpeta local de estado, caché y logs. Si falla la limpieza de archivos, conserva una marca anónima de baja y reintenta; el bot permanece detenido. No mantiene una lista negra de correos o wallets.

**No se cierran posiciones automáticamente ni se liquidan fondos por impago.** Las posiciones abiertas y las órdenes nativas siguen en Hyperliquid; los stops lógicos/HMA dejan de gestionarse. El cliente debe gestionar las posiciones restantes y revocar el agente en Hyperliquid. El aviso está visible antes de autorizar la estrategia y en cada recordatorio.

No pueden borrarse transacciones públicas de blockchain, correos ya recibidos, registros externos del proveedor o copias de seguridad guardadas fuera del servicio. Los archivos vacíos de coordinación del servidor no contienen las credenciales ni el perfil. Un registro nuevo empieza como una cuenta nueva y requiere repetir confirmación y autorización; esto no garantiza que todos paguen.

### Actualizar una instalación existente

1. Sube los archivos de `cryptolove-web` a tu repositorio de la web y publica la actualización en Render manteniendo tu `config.js` real.
2. Sustituye los archivos de código de `cryptolove-server` en `/opt/cryptolove`, **incluyendo el nuevo `billing.py`**. Mantén tu `.env` y tu carpeta `data/`. No reemplaces los archivos del motor `agente_hma_real`.
3. Reinicia los dos servicios para que no queden procesos antiguos:

```bash
sudo systemctl restart cryptolove-api cryptolove-worker
sudo systemctl status cryptolove-api cryptolove-worker
```

La migración es automática y aditiva. Las comisiones pendientes de una instalación anterior reciben **48 horas desde la primera ejecución de la nueva versión**. Los siguientes reinicios conservan esa fecha. No hay que crear tareas de cron ni recordatorios externos; lo gestiona `cryptolove-worker`.

### Pruebas de esta actualización

Han pasado **17 pruebas offline** de esta actualización, incluidas en `cryptolove-server/tests/test_fee_deadlines.py`. Usan cuentas efímeras, una base temporal, reloj simulado, Hyperliquid simulado y SMTP simulado; no envían pagos ni correos reales. Para ejecutarlas en un entorno de pruebas con las dependencias del servidor:

```bash
python -m pip install pytest httpx
python -m pytest tests/test_fee_deadlines.py -q
```

También se ha verificado funcionalmente el DOM en los cuatro idiomas: aviso, cuenta atrás, pago firmado simulado, suspensión por pago incierto y retirada de datos privados al terminar la sesión. Se ha comprobado la sintaxis Python, JavaScript y shell. No se ha podido hacer una comprobación visual con navegador en esta actualización; no se han usado SMTP, credenciales de clientes ni pagos reales.

Se comprueban: aviso inicial y cadencia, borde exacto de 48 horas, conservación del plazo tras reinicios y nuevas deudas, migración, pagos confirmados/rechazados/inciertos, concurrencia entre pago y baja, cancelación de correos antiguos, aislamiento de usuarios, eliminación del estado local y reintento si falla el borrado.

## 11. Concurso y alcance de la comprobación

Las reglas vigentes de **Crypto World’s Fair de Colosseum** contemplan proyectos multichain y una categoría Hyperliquid. Un repositorio público de la web puede servir para mostrar esta parte; **no sustituye** facilitar el código que exijan los jueces para revisar la funcionalidad. Las reglas permiten repositorios privados con acceso para revisión. Declara qué motor existía previamente y qué has construido durante el concurso.

Fuentes técnicas:

- [Hyperliquid: agentes y nonces](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets)
- [Hyperliquid: Exchange endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint)
- [Hyperliquid: builder codes](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/builder-codes)
- [Hyperliquid: Info endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint)
- [Hyperliquid: gráficos de portfolio](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/portfolio-graphs)
- [Google: verificar credenciales](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
- [Render: static sites](https://render.com/docs/static-sites)
- [Colosseum: reglas del concurso](https://colosseum.com/legal/Crypto%20World%27s%20Fair%20Hackathon%20Rules.pdf)

En la entrega anterior se registraron **19 pruebas offline** de autenticación/confirmación, aislamiento de usuarios, firma y antirrepetición, cifrado de claves, umbral de comisión, cobro confirmado/incierto, baja, fills parciales y funding, ajuste de depósitos y bloqueo de entradas por debajo de 100 USDC con el motor existente. También se han comprobado mediante DOM los cuatro idiomas, reproductor, filtros por año, indicador público, visibilidad privada, login/logout y confirmación de Google; y se ha verificado la sintaxis Python/JavaScript/shell. En esa entrega no había navegador de pruebas disponible para una comprobación visual de escritorio/móvil. No se ha operado con dinero real, enviado correos a usuarios, probado credenciales Google/SMTP reales ni desplegado. Esas comprobaciones necesitan tu configuración y una prueba completa en testnet. No se ha realizado una auditoría de seguridad externa.
