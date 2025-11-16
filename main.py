import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Project as ProjectSchema, Building as BuildingSchema, Element as ElementSchema

app = FastAPI(title="Measurement Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        else:
            out[k] = v
    return out


# Root
@app.get("/")
def read_root():
    return {"message": "Measurement Management API is running"}


# Health and DB test
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Schemas for requests
class ProjectCreate(ProjectSchema):
    pass

class ProjectOut(ProjectSchema):
    id: str = Field(..., description="Document ID")

class BuildingCreate(BuildingSchema):
    pass

class BuildingOut(BuildingSchema):
    id: str

class ElementCreate(ElementSchema):
    pass

class ElementOut(ElementSchema):
    id: str


# Projects endpoints
@app.post("/projects", response_model=dict)
def create_project(payload: ProjectCreate):
    try:
        inserted_id = create_document("project", payload)
        doc = db["project"].find_one({"_id": ObjectId(inserted_id)})
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects", response_model=List[dict])
def list_projects():
    try:
        docs = get_documents("project")
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}", response_model=dict)
def get_project(project_id: str):
    try:
        doc = db["project"].find_one({"_id": PyObjectId.validate(project_id)})
        if not doc:
            raise HTTPException(404, "Project not found")
        return serialize_doc(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Buildings endpoints
@app.post("/buildings", response_model=dict)
def create_building(payload: BuildingCreate):
    # Ensure project exists
    _pid = payload.project_id
    if not ObjectId.is_valid(_pid):
        raise HTTPException(400, "Invalid project_id")
    if not db["project"].find_one({"_id": ObjectId(_pid)}):
        raise HTTPException(404, "Parent project not found")
    try:
        inserted_id = create_document("building", payload)
        doc = db["building"].find_one({"_id": ObjectId(inserted_id)})
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/buildings", response_model=List[dict])
def list_buildings(project_id: str):
    try:
        if not ObjectId.is_valid(project_id):
            raise HTTPException(400, "Invalid project_id")
        docs = get_documents("building", {"project_id": project_id})
        return [serialize_doc(d) for d in docs]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Elements endpoints
@app.post("/elements", response_model=dict)
def create_element(payload: ElementCreate):
    # ensure project exists
    if not ObjectId.is_valid(payload.project_id):
        raise HTTPException(400, "Invalid project_id")
    if not db["project"].find_one({"_id": ObjectId(payload.project_id)}):
        raise HTTPException(404, "Parent project not found")
    # if building_id provided, ensure it exists
    if payload.building_id:
        if not ObjectId.is_valid(payload.building_id):
            raise HTTPException(400, "Invalid building_id")
        if not db["building"].find_one({"_id": ObjectId(payload.building_id)}):
            raise HTTPException(404, "Parent building not found")
    try:
        inserted_id = create_document("element", payload)
        doc = db["element"].find_one({"_id": ObjectId(inserted_id)})
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/elements", response_model=List[dict])
def list_elements(project_id: str, building_id: Optional[str] = None):
    try:
        if not ObjectId.is_valid(project_id):
            raise HTTPException(400, "Invalid project_id")
        query: Dict[str, Any] = {"project_id": project_id}
        if building_id:
            if not ObjectId.is_valid(building_id):
                raise HTTPException(400, "Invalid building_id")
            query["building_id"] = building_id
        docs = get_documents("element", query)
        return [serialize_doc(d) for d in docs]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Summary & Export
@app.get("/projects/{project_id}/summary", response_model=dict)
def project_summary(project_id: str):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project_id")
    pipeline = [
        {"$match": {"project_id": project_id}},
        {"$group": {
            "_id": {"type": "$element_type", "config": "$configuration"},
            "count": {"$sum": "$quantity"}
        }},
    ]
    try:
        agg = list(db["element"].aggregate(pipeline))
        items = [
            {
                "element_type": a["_id"].get("type"),
                "configuration": a["_id"].get("config"),
                "count": a["count"],
            }
            for a in agg
        ]
        total = sum(i["count"] for i in items)
        return {"total": total, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/export/csv")
def export_csv(project_id: str):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(400, "Invalid project_id")
    # Build a CSV for elements
    import csv
    import io
    try:
        elems = get_documents("element", {"project_id": project_id})
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Type", "Configuration", "Ouverture", "Hauteur(mm)", "Largeur(mm)",
            "Profondeur(mm)", "Épaisseur(mm)", "Quantité", "Notes"
        ])
        for e in elems:
            writer.writerow([
                str(e.get("_id")),
                e.get("element_type", ""),
                e.get("configuration", ""),
                e.get("opening", ""),
                e.get("height_mm", ""),
                e.get("width_mm", ""),
                e.get("depth_mm", ""),
                e.get("thickness_mm", ""),
                e.get("quantity", 1),
                (e.get("notes_text") or "").replace("\n", " ")
            ])
        csv_content = output.getvalue()
        return app.response_class(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=project_{project_id}_elements.csv"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
