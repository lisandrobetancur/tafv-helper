# Versión de escritorio

La misma Biblioteca de Estudio, como programa que se instala con doble clic: no necesita Python, se abre en su propia
ventana y funciona **sin internet**. Cada equipo se activa con una **licencia propia**, que no vence; no hay límite de
equipos. Todo es gratis: no hace falta comprar certificados ni licencias de software.

La versión web (carpeta + `iniciar`) sigue en la rama `main`; esta versión vive en la rama `escritorio`.

---

## 1. Crear las claves de licencia (una sola vez)

En tu computador, dentro de la carpeta del proyecto (rama `escritorio`) y con las dependencias instaladas:

```
python tools/licencias/crear_claves.py
```

- Guarda la **clave privada** en `~/LicenciasBiblioteca/clave_privada.pem` (fuera del proyecto).
  **Haz una copia de seguridad** (USB, nube personal) y no la compartas. Si se pierde, no podrás emitir licencias
  que valgan para los programas ya repartidos.
- Escribe la **clave pública** en `app/licencia_publica.py`. Haz **commit y push** de ese archivo: los instaladores
  la necesitan. (La clave pública no es secreta: solo sirve para comprobar licencias, no para crearlas.)

Sin la clave pública, el programa no se puede activar y la construcción se detiene con un aviso.

## 2. Construir los instaladores

### Opción A · En GitHub (recomendada: arma Windows y Mac sin tener los dos equipos)

1. En GitHub, pestaña **Actions** › **Escritorio** › **Run workflow** › rama `escritorio` › **Run workflow**.
2. Al terminar (unos 15 minutos), abre la ejecución y descarga en **Artifacts**:
   - `Instalador-Windows` → `Instalador-Biblioteca-de-Estudio.exe`
   - `Instalador-Mac-Apple` → `Biblioteca-de-Estudio.dmg` (Mac M1, M2, M3…)
   - `Instalador-Mac-Intel` → `Biblioteca-de-Estudio.dmg` (Mac con Intel)

### Opción B · En tu equipo

- **Windows:** instala [Inno Setup 6](https://jrsoftware.org/isdl.php) (gratis) y haz doble clic en
  `construir_escritorio.bat`. El instalador queda en `dist\Instalador-Biblioteca-de-Estudio.exe`.
- **Mac:** doble clic en `construir_escritorio.command`. Queda `dist/Biblioteca-de-Estudio.dmg`.

El instalador incluye la biblioteca tal como está en `data/` en ese momento (base de datos y archivos) y los modelos
de lectura de texto (OCR).

## 3. Instalar en el equipo de una persona

**Windows:** abrir `Instalador-Biblioteca-de-Estudio.exe`. Como el programa no tiene firma comprada, Windows muestra
«Windows protegió su PC»: clic en **Más información** › **Ejecutar de todas formas**. Se instala solo para ese usuario
(no pide contraseña de administrador) y crea el acceso en el menú Inicio y, si se elige, en el escritorio.

**Mac:** abrir el `.dmg` y arrastrar **Biblioteca de Estudio** a **Aplicaciones**. La primera vez, el Mac dice que no
puede verificar al desarrollador: cerrar el aviso, ir a **Ajustes del Sistema › Privacidad y seguridad** y, abajo,
pulsar **Abrir de todas formas**. Solo pasa la primera vez.

## 4. Activar (licencia por equipo)

1. Al abrir el programa por primera vez aparece **Activar el programa**, con un **código de equipo**
   (por ejemplo `7K3M-QWXD-2RPA-F4TB`) y un botón **Copiar**. La persona te lo envía.
2. Tú emites la licencia:
   ```
   python tools/licencias/emitir.py 7K3M-QWXD-2RPA-F4TB --nombre "Nombre de la persona"
   ```
   Imprime una licencia que empieza por `TAFV1.` y la anota en `~/LicenciasBiblioteca/registro.csv`.
3. Se la envías; la persona la pega en **Licencia** y pulsa **Activar**. Listo: no vence y no se vuelve a pedir.

Cada equipo necesita su propia licencia: si se copia la carpeta de datos a otro computador, allí se pide activar de
nuevo. Si alguien formatea o cambia de computador, el código cambia y se le emite una licencia nueva.

## 5. Datos, actualizaciones y desinstalación

- La biblioteca de cada persona se guarda en su usuario:
  - Windows: `%APPDATA%\Biblioteca de Estudio`
  - Mac: `~/Library/Application Support/Biblioteca de Estudio`
- **Actualizar:** se instala la versión nueva encima. La biblioteca de la persona **se conserva**: la incluida en el
  instalador solo se usa la primera vez. (Para entregar material nuevo a quien ya tiene el programa, usa los
  respaldos de Mantenimiento.)
- **Desinstalar** (Windows: Configuración › Aplicaciones; Mac: borrar la app) no borra la biblioteca.

## 6. Qué protege la licencia y qué no

Evita que el programa se use en un equipo sin activar y que una copia pase de un computador a otro. No es
inviolable: alguien con conocimientos de programación podría modificar el programa para saltarse la comprobación.
Para quien usa el programa normalmente, es una protección suficiente y sin costo.

## Para desarrollo

- `python escritorio.py` abre la versión de escritorio sin empaquetar (con `--navegador`, en el navegador).
- Piezas: `app/services/licencia.py` (código de equipo y verificación), `app/templates/paginas/licencia.html`,
  `escritorio.py` (carpeta del usuario, servidor y ventana), `escritorio/` (PyInstaller, Inno Setup y
  `construir.py`), `tools/licencias/` (crear claves y emitir licencias), `.github/workflows/escritorio.yml`.
- Las pruebas no exigen licencia (`crear_app(exigir_licencia=False)`); `tests/test_fase14_licencia.py` y
  `tests/test_fase15_escritorio.py` cubren la licencia y la carpeta de datos.
