"""Modelos de datos (también sirven de esquema para la extracción con Claude)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Empleo(BaseModel):
    denominacion: str = Field(description="Denominación del empleo, p. ej. 'Profesional Especializado'")
    codigo: str | None = Field(None, description="Código del empleo, p. ej. '2028'")
    grado: str | None = Field(None, description="Grado salarial, p. ej. '13'")
    nivel: str | None = Field(None, description="Directivo, Asesor, Profesional, Técnico o Asistencial")
    numero_cargos: int | None = Field(None, description="Número de cargos/plazas de este empleo, si el documento lo indica")
    dependencia: str | None = Field(None, description="Dependencia donde se ubica el empleo")
    proposito: str | None = None
    funciones: str | None = Field(None, description="Funciones esenciales, resumidas")
    requisitos_estudio: str | None = Field(None, description="Formación académica / núcleos básicos del conocimiento")
    requisitos_experiencia: str | None = None
    alternativas: str | None = Field(None, description="Equivalencias o alternativas de requisitos")


class ListaEmpleos(BaseModel):
    empleos: list[Empleo]


class ListaDependencias(BaseModel):
    dependencias: list[str] = Field(description="Nombre de cada dependencia del organigrama, sin repetir")
