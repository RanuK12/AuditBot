# Auditbot: Auditoría de Accesibilidad Web
=============================================

## Descripción del Proyecto
---------------------------

Auditbot es una herramienta de auditoría de accesibilidad web diseñada para ayudar a los desarrolladores y propietarios de sitios web a identificar y corregir problemas de accesibilidad en sus sitios web. Nuestro objetivo es proporcionar una herramienta fácil de usar y personalizable que permita a los usuarios evaluar la accesibilidad de sus sitios web de acuerdo con las pautas de accesibilidad web más recientes.

## Características
-------------------

*   Evaluación automática de la accesibilidad web según las pautas WCAG 2.1
*   Informes detallados sobre problemas de accesibilidad y recomendaciones para su corrección
*   Personalización de la auditoría para adaptarse a las necesidades específicas de cada sitio web
*   Integración con herramientas de desarrollo y sistemas de gestión de contenido

## Instalación
--------------

Para instalar Auditbot, sigue estos pasos:

1.  Clona el repositorio de Auditbot utilizando Git: `git clone https://github.com/auditbot/auditbot.git`
2.  Cambia al directorio del proyecto: `cd auditbot`
3.  Instala las dependencias requeridas: `npm install`
4.  Ejecuta la herramienta de auditoría: `npm run audit`

## Uso Básico
--------------

Para realizar una auditoría básica de accesibilidad con Auditbot, sigue estos pasos:

1.  Abre la terminal y navega al directorio del proyecto
2.  Ejecuta el comando de auditoría:
    - Con npm: `npm run audit https://example.com`
    - Con CLI directo: `python app.py https://example.com`
3.  La herramienta generará un informe detallado sobre los problemas de accesibilidad encontrados en el sitio web

## Uso de la Interfaz de Línea de Comandos (CLI)

Auditbot también incluye una interfaz de línea de comandos para ejecutar auditorías directamente desde la terminal:

```bash
# Auditoría básica en formato JSON
python app.py https://example.com

# Auditoría con formato PDF
python app.py https://example.com --format pdf

# Especificar puerto y host para el servidor API
python app.py https://example.com --host 127.0.0.1 --port 8000

# Guardar resultado en archivo específico
python app.py https://example.com --output report.json --format json
```

Parámetros disponibles:
- `url`: URL del sitio web a auditar (obligatorio)
- `--format`: Formato de salida (json o pdf, default: json)
- `--output`: Ruta del archivo de salida (opcional)
- `--host`: Host para el servidor API (default: 127.0.0.1)
- `--port`: Puerto para el servidor API (default: 8000)

## Contribución
--------------

Queremos que contribuyas a mejorar Auditbot. Si encuentras un error o tienes una idea para una nueva característica, por favor:

1.  Abre un issue en el repositorio de GitHub para describir el problema o la característica que deseas agregar
2.  Crea un fork del repositorio y realiza los cambios necesarios
3.  Envía un pull request con tus cambios para que podamos revisarlos y fusionarlos en el proyecto principal

## Licencia
------------

Auditbot está licenciado bajo la licencia MIT. Esto significa que eres libre de utilizar, modificar y distribuir el software sin restricciones, siempre y cuando incluyas el aviso de copyright y la licencia en tus distribuciones.

## Agradecimientos
------------------

Queremos agradecer a todos los contribuyentes y colaboradores que han ayudado a hacer de Auditbot una herramienta útil y efectiva para la auditoría de accesibilidad web. ¡Gracias por tu apoyo!