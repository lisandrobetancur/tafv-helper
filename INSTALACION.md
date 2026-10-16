# Cómo instalar y usar la Biblioteca de Estudio

Esta guía es para usar la biblioteca **sin conocimientos técnicos**. Se instala **una sola vez en cada computador** y después se abre con **doble clic**.

La biblioteca funciona **sin internet** (solo se necesita internet durante la instalación) y todo se guarda dentro de su propia carpeta.

---

## Índice

1. [Instalar en un Mac](#1-instalar-en-un-mac)
2. [Instalar en Windows](#2-instalar-en-windows)
3. [Usar la biblioteca cada día](#3-usar-la-biblioteca-cada-día)
4. [Compartir la biblioteca con otro computador](#4-compartir-la-biblioteca-con-otro-computador)
5. [Respaldos (copias de seguridad)](#5-respaldos-copias-de-seguridad)
6. [Probar con datos de demostración](#6-probar-con-datos-de-demostración)
7. [Solución de problemas](#7-solución-de-problemas)

---

## 1. Instalar en un Mac

Sirve para Mac con procesador Apple (M1, M2, M3, M4…) y para Mac con procesador Intel.

### Paso 1 · Instalar Python (una sola vez)

1. Entra en **https://www.python.org/downloads/macos/**.
2. Descarga **Python 3.13** («macOS 64-bit universal2 installer»).
   > En un Mac con **Intel** usa la 3.13 (o 3.12). No uses la 3.14 en un Mac Intel.
3. Abre el archivo descargado y sigue los pasos hasta «Instalación completada».

### Paso 2 · Instalar la biblioteca

1. Abre la carpeta de la biblioteca en el Finder.
2. Haz **doble clic en `instalar.command`**.
3. Se abre una ventana negra (Terminal) que instala todo. La primera vez tarda **unos minutos**. Al terminar verás **«¡Listo!»**. Pulsa Enter para cerrarla.

### Si el Mac no te deja abrir el archivo

La primera vez macOS puede decir que **«no se puede abrir porque no se puede verificar el desarrollador»**. Es normal con archivos que no vienen de la App Store:

1. Pulsa **Aceptar** (o **Listo**) en ese aviso.
2. Abre  → **Ajustes del Sistema** → **Privacidad y seguridad**.
3. Baja hasta el final: verás un mensaje sobre `instalar.command` con el botón **«Abrir igualmente»**. Púlsalo y confirma con tu contraseña o Touch ID.
4. Repite lo mismo la primera vez que abras `iniciar.command`.

> En versiones anteriores de macOS también funciona: **clic derecho** sobre el archivo → **Abrir** → **Abrir**.

Si el aviso dice que **«no tienes permiso»** para abrirlo (puede pasar al copiar la carpeta desde un pendrive), haz esto una sola vez:

1. Abre **Terminal** (búscalo con ⌘ + Espacio).
2. Escribe `chmod +x ` (con un espacio al final), **arrastra** el archivo `instalar.command` a la ventana y pulsa Enter.
3. Repite con `iniciar.command`.

---

## 2. Instalar en Windows

### Paso 1 · Instalar Python (una sola vez)

1. Entra en **https://www.python.org/downloads/windows/**.
2. Descarga **Python 3.13** («Windows installer (64-bit)»).
3. Abre el instalador y, **antes de pulsar «Install Now»**, marca abajo la casilla **«Add python.exe to PATH»**.
4. Pulsa **Install Now** y espera a que termine.

### Paso 2 · Instalar la biblioteca

1. Abre la carpeta de la biblioteca.
2. Haz **doble clic en `instalar.bat`**.
3. Se abre una ventana negra que instala todo. La primera vez tarda **unos minutos**. Al terminar verás **«¡Listo!»**. Pulsa una tecla para cerrarla.

### Si aparece «Windows protegió su PC»

Es el filtro SmartScreen y aparece con archivos descargados de internet:

1. Pulsa **«Más información»**.
2. Pulsa **«Ejecutar de todas formas»**.

> Si la carpeta te llegó como **.zip**, antes de descomprimirla haz clic derecho sobre el .zip → **Propiedades** → marca **«Desbloquear»** → **Aceptar**. Así no aparecen estos avisos.

---

## 3. Usar la biblioteca cada día

- **Abrir:** doble clic en **`iniciar.command`** (Mac) o **`iniciar.bat`** (Windows). Se abre una ventana negra y, a los pocos segundos, la biblioteca en tu navegador.
- **Cerrar:** cierra la **ventana negra**. (Cerrar solo la pestaña del navegador no la cierra.)
- **Dirección:** si el navegador no se abre solo, entra en **http://127.0.0.1:8765**.

Consejos rápidos:

- **Buscar en todo:** pulsa **⌘ K** (Mac) o **Ctrl K** (Windows), o haz clic en el buscador de arriba. No importan las tildes ni las mayúsculas.
- **Nombre descriptivo:** al subir un Excel, PDF o imagen, la biblioteca pide un nombre que diga qué es. Ese nombre es el que verás y el que tendrá el archivo en la carpeta.
- **PDF escaneados:** su texto se lee solo, en segundo plano (arriba verás «Leyendo texto con OCR…»). Puedes seguir usando la biblioteca mientras tanto.
- **Lo que elimines** va a la **Papelera** (menú de la izquierda) y se puede restaurar.
- **Acceso rápido:** es un módulo aparte, en el menú de la izquierda, que reúne todas tus materias. Escribe varios síntomas y verás, materia por materia, qué registros (por ejemplo medicamentos o enfermedades) los mencionan, ordenados por cuántos cubren, con la frase exacta y la columna donde aparece cada síntoma. Marca con la estrella los síntomas más importantes (valen el doble). Los casos se guardan en el mismo módulo (Diagnóstico › Casos guardados) con tu conclusión, y al abrirlos se vuelven a analizar con todo lo que hayas agregado. Es una ayuda de estudio: ordena lo que dice tu material, no reemplaza el juicio clínico.

---

## 4. Compartir la biblioteca con otro computador

La información se carga en un computador y luego se **copia la carpeta completa** al otro (con un pendrive, un disco o una carpeta sincronizada como Google Drive, OneDrive o iCloud).

**Qué copiar:** la carpeta completa de la biblioteca. Lo importante está dentro de:

- `data/` → tu información (base de datos y archivos).
- `modelos/` → el lector de texto (OCR).

**Qué no hace falta copiar:** la carpeta `.venv` (es propia de cada computador; si la copias no pasa nada, se rehace sola).

**En el otro computador:** la primera vez haz doble clic en **`instalar`** (instala lo que ese computador necesita). Después, como siempre, **`iniciar`**.

### ⚠️ Usa la biblioteca en un solo computador a la vez

Si se abre en dos computadores a la vez, **los cambios de uno pueden perderse**. Por eso la biblioteca avisa: si al abrirla aparece **«La biblioteca parece abierta en (otro equipo)»**, ciérrala en ese otro computador primero. Si el otro computador se apagó sin cerrarla, puedes pulsar **«Abrir aquí de todos modos»**.

Si usas una carpeta sincronizada (Drive, OneDrive, iCloud):

- **Cierra la biblioteca** y espera a que termine de sincronizar antes de abrirla en el otro computador.
- Marca la carpeta como **«Mantener siempre en este dispositivo»** (o «Disponible sin conexión»), para que todos los archivos estén realmente descargados.

---

## 5. Respaldos (copias de seguridad)

En el menú de la izquierda entra en **Mantenimiento**:

- **Crear respaldo ahora:** guarda toda la biblioteca en un solo archivo `.zip` dentro de `data/respaldos/`. Hazlo de vez en cuando y **siempre antes de copiar la biblioteca a otro computador**.
- **Descargar:** para guardar el respaldo en un pendrive o en la nube.
- **Restaurar:** devuelve la biblioteca al estado de ese respaldo. Antes de restaurar, la biblioteca guarda automáticamente un respaldo del estado actual, por si te arrepientes.
- **Restaurar desde un archivo ZIP de otro lugar:** para usar un respaldo que tengas en otra carpeta o en otro computador.

---

## 6. Probar con datos de demostración

Para ver cómo funciona sin tocar tu información hay una **biblioteca de ejemplo** (anatomía y farmacología) que se guarda aparte, en la carpeta `demo/`.

- **Mac:** abre Terminal en la carpeta de la biblioteca y escribe `.venv/bin/python -m app.demo`
- **Windows:** abre «Símbolo del sistema» en la carpeta y escribe `.venv\Scripts\python -m app.demo`

Se abre en otra dirección (http://127.0.0.1:8766). Tus datos reales no cambian. Para borrar la demostración, borra la carpeta `demo/`.

---

## 7. Solución de problemas

**«No se encontró Python 3.11 o superior»**
Instala Python 3.13 como se explica arriba. En Windows, asegúrate de haber marcado **«Add python.exe to PATH»**; si no lo hiciste, vuelve a abrir el instalador de Python → **Modify** → marca **«Add Python to environment variables»**.

**El navegador no se abre solo**
Abre tu navegador y entra en **http://127.0.0.1:8765**. Mira la ventana negra: ahí aparece la dirección exacta.

**«El puerto 8765 está ocupado»**
No pasa nada: la biblioteca usa otro número automáticamente (por ejemplo 8766) y lo muestra en la ventana negra. Si ya tenías la biblioteca abierta, probablemente sea esa misma: usa esa ventana del navegador.

**El lector de texto (OCR) va lento**
Es normal en computadores antiguos: cada página escaneada puede tardar unos segundos. Se hace en segundo plano y continúa donde iba si cierras y vuelves a abrir la biblioteca.

**«No se pudieron instalar los componentes»**
Comprueba la conexión a internet y vuelve a hacer doble clic en `instalar`. En redes de universidad o empresa, a veces un cortafuegos bloquea la descarga: prueba en otra red.

**La búsqueda no encuentra algo que sí está**
En **Mantenimiento** pulsa **«Reconstruir índice»**.

**Las miniaturas se ven mal**
En **Mantenimiento** pulsa **«Regenerar miniaturas»**.

**Algo no funciona y no sabes por qué**
Cierra la ventana negra y vuelve a abrir con `iniciar`. Si el problema sigue, el archivo `data/logs/app.log` guarda los detalles técnicos: compártelo con quien te ayude.
