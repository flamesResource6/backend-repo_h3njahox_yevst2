"""
Database Schemas for Measurement Management App

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

class Project(BaseModel):
    name: str = Field(..., description="Project name")
    project_type: Literal[
        "Immeuble", "Résidence", "Villa", "École", "Hôtel", "Autre"
    ] = Field("Autre", description="Type de projet")
    location: Optional[str] = Field(None, description="Localisation du chantier")
    contact_name: Optional[str] = Field(None, description="Nom du contact")
    contact_phone: Optional[str] = Field(None, description="Téléphone du contact")
    photo_url: Optional[str] = Field(None, description="Photo du projet (URL)")

class Building(BaseModel):
    project_id: str = Field(..., description="ID du projet parent")
    name: str = Field(..., description="Nom du bâtiment / bloc")
    description: Optional[str] = Field(None, description="Description facultative")

class Element(BaseModel):
    project_id: str = Field(..., description="ID du projet")
    building_id: Optional[str] = Field(None, description="ID du bâtiment")
    element_type: Literal["porte", "placard", "dressing"] = Field(..., description="Type d\'élément")
    configuration: Optional[str] = Field(None, description="Configuration (simple/double, L, U, etc.)")
    opening: Optional[Literal["poussant", "tirant"]] = Field(None, description="Sens d\'ouverture (portes)")
    height_mm: Optional[float] = Field(None, ge=0, description="Hauteur en mm")
    width_mm: Optional[float] = Field(None, ge=0, description="Largeur en mm")
    depth_mm: Optional[float] = Field(None, ge=0, description="Profondeur en mm (placards/dressings)")
    thickness_mm: Optional[float] = Field(None, ge=0, description="Épaisseur en mm")
    quantity: int = Field(1, ge=1, description="Quantité")
    notes_text: Optional[str] = Field(None, description="Notes écrites")
    notes_audio_url: Optional[str] = Field(None, description="Note vocale (URL)")
    photo_url: Optional[str] = Field(None, description="Photo (URL)")
