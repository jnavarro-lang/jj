# Agente ITECO Drive

Agente que aprende la experiencia, el RUP, el equipo y los documentos de ITECO CONSULTORES S.A.S. BIC
(desde Google Drive o desde una carpeta del PC) y valida procesos del SECOP II: experiencia habilitante y
puntuable, equipo de trabajo, capacidad financiera, documentos habilitantes y simulación de consorcios.

## Dónde funciona

El agente está publicado como artifact de Claude:
https://claude.ai/artifact/6MueRwrY4aj3eW8DKuNZn2

Este repositorio guarda **solo el código** (copia y control de versiones). **No contiene datos**: lo aprendido
(fichas de archivos, contratos, RUP, análisis) vive en la base de datos del artifact en claude.ai.
Para tener una copia de los datos, usa el botón «Descargar respaldo completo» en la pestaña «Conocimiento ITECO».

El archivo `Agente ITECO Drive.html` abierto directamente en el navegador **no funciona solo**: necesita las
capacidades de claude.ai (base de datos, conexión con Google Drive y Claude). Ábrelo siempre desde el enlace de arriba.

## Archivos

| Archivo | Qué es |
|---|---|
| `Agente ITECO Drive.html` | El programa completo del agente (una sola página). |
| `codigo/lector_rup.js` | Lector del certificado RUP de la Cámara de Comercio (extraído del programa, para pruebas). |

## Carpetas que lee

- **Google Drive**: pega el enlace de la carpeta en «Conocimiento ITECO» → «Conectar y aprender».
- **Carpeta del PC** (p. ej. `F:\secop\ITECO - PROCESOS\EXPERIENCIA RUP ITECO CONSULTORES S.A.S BIC`):
  «💻 Conectar carpeta de mi PC» y selecciona la carpeta. Instalado como app de escritorio de Claude
  (cuando la app lo ofrece) lee la ruta directamente.

## Versión

Última publicación: 2026-11-24 · versión del artifact `1795567279-1c11` (carpetas del PC + app de escritorio).
