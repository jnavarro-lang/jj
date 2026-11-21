# Fuentes – MinTIC (SIGEP 0012)

Consultadas el 21/11/2026. Los PDF están en `insumos/0012/`, que no se sube al repositorio
(`.gitignore`). Se pueden volver a descargar con estas URL.

| Archivo en `insumos/0012/` | Documento | URL de origen |
|---|---|---|
| `manual.pdf` | Anexo Manual Específico de Funciones y de Competencias Laborales, **Resolución 03927 de 2024** (18/10/2024), 1.249 páginas. Modifica el manual de la Res. 1350 de 2020 / 0177 de 2021. Según el Plan Anual de Vacantes 2025 es el manual vigente. | https://www.mintic.gov.co/portal/715/articles-135690_recurso_2.pdf (enlace "Modificación Manual Especifico de Funciones y de Competencias Laborales 2020", página [Manuales y otros lineamientos](https://www.mintic.gov.co/portal/inicio/Atencion-y-Servicio-a-la-Ciudadania/Transparencia/439929:Manuales-y-otros-lineamientos)) |
| `decreto_1065_2020.pdf` | Decreto 1065 de 2020 (23/07/2020), "Por el cual se modifica la planta de personal del MinTIC". Solo suprime y crea empleos: **no** trae la planta completa. | https://www.funcionpublica.gov.co/eva/gestornormativo/norma_pdf.php?i=136671 (la respuesta trae espacios antes de `%PDF`; se quitaron para guardar el PDF) |
| `plan_prevision_rrhh_2026.pdf` | Plan de Previsión de Recursos Humanos 2026: planta con corte al 31/12/2025 (659 empleos por nivel, 497 provistos, 163 vacantes) y relación de vacantes por empleo y dependencia. | https://www.mintic.gov.co/portal/715/articles-135689_v2026_plan_prevision_recursos_humanos.pdf |
| `plan_vacantes_2026.pdf` | Plan Anual de Vacantes 2026 | https://www.mintic.gov.co/portal/715/articles-135689_v2026_plan_vacantes.pdf |

Otras referencias:

* Manual 2021 (Res. 0177 de 2021, reemplazado):
  https://www.mintic.gov.co/portal/715/articles-135690_Manual_Especifico_Funciones__Competencias_Laborales_29_01_2021_V19.pdf
  y la resolución: https://www.mintic.gov.co/portal/715/articles-135690_resolucion_177_2021.pdf
* Plan Anual de Vacantes 2025 (cita la planta: Decreto 2619 de 2012, modificado por los Decretos 1430 de 2017 y 1065 de 2020, con 659 empleos):
  https://www.mintic.gov.co/portal/715/articles-135689_plan_vacantes_2025.pdf

## No se obtuvo `planta.pdf`

La planta completa está en el **Decreto 2619 de 2012**, art. 2, modificado por los Decretos
1430 de 2017 y 1065 de 2020. La distribución por dependencias está en la **Resolución 1351 de
2020**. No se pudo descargar ninguno de los dos:

* `normograma.mintic.gov.co` y `sidn.ramajudicial.gov.co`: el proxy de salida de esta sesión los bloquea (403).
* `www.mintic.gov.co/portal/historico/articles-9305_mintic_decreto_1065_2020.pdf`: redirige a la portada.
* No se encontró el identificador del Decreto 2619 de 2012 en el Gestor Normativo de Función Pública.

El Decreto 1065 de 2020 **no** se guardó como `planta.pdf`. Solo trae los empleos creados y
suprimidos en 2020, y el agente los habría tomado como el total de plazas. El número de cargos
sale del campo "No. de Cargos" de cada ficha del manual.
