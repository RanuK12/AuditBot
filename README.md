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

### CLI
Para realizar una auditoría básica de accesibilidad con Auditbot, sigue estos pasos:

1. Abre la terminal y navega al directorio del proyecto
2. Ejecuta el comando `npm run audit` seguido de la URL del sitio web que deseas auditar: `npm run audit https://example.com`
3. La herramienta generará un informe detallado sobre los problemas de accesibilidad encontrados en el sitio web


### API REST
Auditbot expone una API REST para integrar la auditoría en tus flujos de trabajo:

#### Endpoints disponibles:
- **POST `/trigger`**: Inicia una auditoría de accesibilidad a partir de una URL y devuelve el reporte en formato compatible con `generate_report.py`.
  **Request body**:
  ```json
  {
    "url": "https://example.com"
  }
  ```
  **Response**: Reporte en formato JSON compatible con `generate_report.py`.

- **GET `/audit?url=<url>`**: Ejecuta una auditoría y devuelve los resultados en formato JSON.
- **POST `/audit`**: Igual que GET `/audit`, pero con el cuerpo JSON.
- **GET `/audit/report?url=<url>`**: Genera y devuelve un informe PDF de la auditoría.
- **GET/POST `/audit/report/json`**: Devuelve el reporte en formato JSON compatible con `generate_report.py`.

Ejemplo de uso con `curl`:
```bash
curl -X POST http://localhost:8000/trigger -H "Content-Type: application/json" -d '{"url": "https://example.com"}'
```

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