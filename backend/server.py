from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import uuid
from datetime import datetime, date, timezone
from enum import Enum
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    DOCTOR = "doctor"
    FARMACEUTICA = "farmaceutica"

class GravidadDiagnostico(str, Enum):
    LEVE = "leve"
    MODERADA = "moderada"
    GRAVE = "grave"

class EstadoNutricional(str, Enum):
    DESNUTRIDO = "desnutrido"  # IMC < 16
    NORMAL = "normal"  # IMC 16-24.9
    OBESIDAD_LEVE = "obesidad_leve"  # IMC 25-29.9
    OBESIDAD_MODERADA = "obesidad_moderada"  # IMC 30-34.9
    OBESIDAD_MORBIDA = "obesidad_morbida"  # IMC >= 35

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data.get('fecha_nacimiento'), date):
        data['fecha_nacimiento'] = data['fecha_nacimiento'].isoformat()
    if isinstance(data.get('created_at'), datetime):
        data['created_at'] = data['created_at'].isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item.get('fecha_nacimiento'), str):
        item['fecha_nacimiento'] = datetime.fromisoformat(item['fecha_nacimiento']).date()
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    return item

def calcular_edad(fecha_nacimiento: date) -> int:
    today = date.today()
    return today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

def calcular_imc_y_estado_nutricional(peso: float, altura: float) -> tuple[float, EstadoNutricional]:
    imc = peso / (altura ** 2)
    
    if imc < 16:
        estado = EstadoNutricional.DESNUTRIDO
    elif 16 <= imc <= 24.9:
        estado = EstadoNutricional.NORMAL
    elif 25 <= imc <= 29.9:
        estado = EstadoNutricional.OBESIDAD_LEVE
    elif 30 <= imc <= 34.9:
        estado = EstadoNutricional.OBESIDAD_MODERADA
    else:
        estado = EstadoNutricional.OBESIDAD_MORBIDA
    
    return round(imc, 2), estado

# Models
class LoginRequest(BaseModel):
    codigo: str

class LoginResponse(BaseModel):
    success: bool
    token: str
    role: UserRole
    mensaje: str

class CodigoCIE10(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codigo: str
    descripcion: str
    categoria: str

class CodigoCIE10Create(BaseModel):
    codigo: str
    descripcion: str
    categoria: str

class AnalisisLaboratorio(BaseModel):
    nombre_analisis: str
    resultado: str
    fecha_analisis: date
    doctor_solicita: str

class RegistroCita(BaseModel):
    fecha_cita: date
    motivo: str
    tratamiento: str
    cobro: float
    doctor_atencion: str

class Paciente(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre_completo: str
    fecha_nacimiento: date
    edad: int = Field(default=0)
    nombre_padre: str
    nombre_madre: str
    direccion: str
    numero_celular: str
    sintomas_signos: str = ""
    diagnostico_clinico: str = ""
    codigo_cie10: Optional[str] = None
    descripcion_cie10: Optional[str] = None
    gravedad_diagnostico: Optional[GravidadDiagnostico] = None
    peso: Optional[float] = None
    altura: Optional[float] = None
    imc: Optional[float] = None
    estado_nutricional: Optional[EstadoNutricional] = None
    analisis_laboratorio: List[AnalisisLaboratorio] = []
    historial_citas: List[RegistroCita] = []
    contacto_recordatorios: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('edad', always=True)
    def calcular_edad_automatica(cls, v, values):
        if 'fecha_nacimiento' in values:
            return calcular_edad(values['fecha_nacimiento'])
        return v

class PacienteCreate(BaseModel):
    nombre_completo: str
    fecha_nacimiento: date
    nombre_padre: str
    nombre_madre: str
    direccion: str
    numero_celular: str
    sintomas_signos: str = ""
    diagnostico_clinico: str = ""
    codigo_cie10: Optional[str] = None
    gravedad_diagnostico: Optional[GravidadDiagnostico] = None
    peso: Optional[float] = None
    altura: Optional[float] = None
    contacto_recordatorios: str = ""

class PacienteUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    nombre_padre: Optional[str] = None
    nombre_madre: Optional[str] = None
    direccion: Optional[str] = None
    numero_celular: Optional[str] = None
    sintomas_signos: Optional[str] = None
    diagnostico_clinico: Optional[str] = None
    codigo_cie10: Optional[str] = None
    gravedad_diagnostico: Optional[GravidadDiagnostico] = None
    peso: Optional[float] = None
    altura: Optional[float] = None
    contacto_recordatorios: Optional[str] = None

class Medicamento(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    descripcion: str
    stock: int
    precio: float
    categoria: str
    indicaciones: str = ""
    contraindicaciones: str = ""
    dosis_pediatrica: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MedicamentoCreate(BaseModel):
    nombre: str
    descripcion: str
    stock: int
    precio: float
    categoria: str
    indicaciones: str = ""
    contraindicaciones: str = ""
    dosis_pediatrica: str = ""

# Authentication function
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != "valid_token_1970":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Initialize CIE-10 codes
async def initialize_cie10_codes():
    cie10_codes = [
        # Infecciones respiratorias agudas
        {"codigo": "J00", "descripcion": "Rinofaringitis aguda (resfriado común)", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J01", "descripcion": "Sinusitis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J02", "descripcion": "Faringitis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J03", "descripcion": "Amigdalitis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J04", "descripcion": "Laringitis y traqueítis agudas", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J06", "descripcion": "Infecciones agudas de las vías respiratorias superiores", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J12", "descripcion": "Neumonía viral", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J13", "descripcion": "Neumonía por Streptococcus pneumoniae", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J18", "descripcion": "Neumonía, organismo no especificado", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J20", "descripcion": "Bronquitis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J21", "descripcion": "Bronquiolitis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J45", "descripcion": "Asma", "categoria": "Enfermedades respiratorias"},
        
        # Enfermedades del oído
        {"codigo": "H65", "descripcion": "Otitis media no supurativa", "categoria": "Enfermedades del oído"},
        {"codigo": "H66", "descripcion": "Otitis media supurativa y la no especificada", "categoria": "Enfermedades del oído"},
        {"codigo": "H10", "descripcion": "Conjuntivitis", "categoria": "Enfermedades del ojo"},
        
        # Enfermedades gastrointestinales
        {"codigo": "A09", "descripcion": "Diarrea y gastroenteritis de presunto origen infeccioso", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K59", "descripcion": "Otros trastornos funcionales del intestino", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K30", "descripcion": "Dispepsia funcional", "categoria": "Enfermedades gastrointestinales"},
        
        # Enfermedades de la piel
        {"codigo": "L20", "descripcion": "Dermatitis atópica", "categoria": "Enfermedades de la piel"},
        {"codigo": "L21", "descripcion": "Dermatitis seborreica", "categoria": "Enfermedades de la piel"},
        {"codigo": "L22", "descripcion": "Dermatitis del pañal", "categoria": "Enfermedades de la piel"},
        {"codigo": "L30", "descripcion": "Otras dermatitis", "categoria": "Enfermedades de la piel"},
        
        # Síntomas y signos
        {"codigo": "R50", "descripcion": "Fiebre, no especificada", "categoria": "Síntomas y signos"},
        {"codigo": "R05", "descripcion": "Tos", "categoria": "Síntomas y signos"},
        {"codigo": "R06", "descripcion": "Anormalidades de la respiración", "categoria": "Síntomas y signos"},
        {"codigo": "R10", "descripcion": "Dolor abdominal y pélvico", "categoria": "Síntomas y signos"},
        {"codigo": "R11", "descripcion": "Náusea y vómito", "categoria": "Síntomas y signos"},
        
        # Trastornos nutricionales
        {"codigo": "E40", "descripcion": "Kwashiorkor", "categoria": "Trastornos nutricionales"},
        {"codigo": "E41", "descripcion": "Marasmo nutricional", "categoria": "Trastornos nutricionales"},
        {"codigo": "E42", "descripcion": "Marasmo-kwashiorkor", "categoria": "Trastornos nutricionales"},
        {"codigo": "E43", "descripcion": "Desnutrición proteico-calórica severa no especificada", "categoria": "Trastornos nutricionales"},
        {"codigo": "E44", "descripcion": "Desnutrición proteico-calórica de grado moderado y leve", "categoria": "Trastornos nutricionales"},
        {"codigo": "E66", "descripcion": "Obesidad", "categoria": "Trastornos nutricionales"},
        
        # Enfermedades infecciosas
        {"codigo": "A00", "descripcion": "Cólera", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A01", "descripcion": "Fiebres tifoidea y paratifoidea", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A02", "descripcion": "Otras infecciones por Salmonella", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A03", "descripcion": "Shigelosis", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A04", "descripcion": "Otras infecciones intestinales bacterianas", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A08", "descripcion": "Infecciones intestinales debidas a virus y otros organismos especificados", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B00", "descripcion": "Infecciones por virus del herpes simple", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B01", "descripcion": "Varicela", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B02", "descripcion": "Herpes zóster", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B05", "descripcion": "Sarampión", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B06", "descripcion": "Rubéola", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B08", "descripcion": "Otras infecciones virales caracterizadas por lesiones de piel y mucosas", "categoria": "Enfermedades infecciosas"},
    ]
    
    existing_count = await db.cie10_codes.count_documents({})
    if existing_count == 0:
        for code in cie10_codes:
            code_obj = CodigoCIE10(**code)
            await db.cie10_codes.insert_one(code_obj.dict())

# Routes
@api_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    if request.codigo == "1970":
        return LoginResponse(
            success=True,
            token="valid_token_1970",
            role=UserRole.DOCTOR,
            mensaje="Acceso autorizado como Doctor"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código de acceso incorrecto"
        )

@api_router.get("/cie10", response_model=List[CodigoCIE10])
async def get_cie10_codes(token: str = Depends(verify_token)):
    codes = await db.cie10_codes.find().to_list(1000)
    return [CodigoCIE10(**code) for code in codes]

@api_router.get("/cie10/search")
async def search_cie10(query: str, token: str = Depends(verify_token)):
    codes = await db.cie10_codes.find({
        "$or": [
            {"codigo": {"$regex": query, "$options": "i"}},
            {"descripcion": {"$regex": query, "$options": "i"}}
        ]
    }).to_list(50)
    return [CodigoCIE10(**code) for code in codes]

@api_router.post("/pacientes", response_model=Paciente)
async def crear_paciente(paciente_data: PacienteCreate, token: str = Depends(verify_token)):
    paciente_dict = paciente_data.dict()
    
    # Calcular edad automáticamente
    paciente_dict['edad'] = calcular_edad(paciente_data.fecha_nacimiento)
    
    # Obtener descripción del CIE-10 si se proporcionó código
    if paciente_data.codigo_cie10:
        cie10_code = await db.cie10_codes.find_one({"codigo": paciente_data.codigo_cie10})
        if cie10_code:
            paciente_dict['descripcion_cie10'] = cie10_code['descripcion']
    
    # Calcular IMC y estado nutricional si se proporcionó peso y altura
    if paciente_data.peso and paciente_data.altura:
        imc, estado_nutricional = calcular_imc_y_estado_nutricional(
            paciente_data.peso, paciente_data.altura
        )
        paciente_dict['imc'] = imc
        paciente_dict['estado_nutricional'] = estado_nutricional
    
    paciente_obj = Paciente(**paciente_dict)
    paciente_mongo = prepare_for_mongo(paciente_obj.dict())
    await db.pacientes.insert_one(paciente_mongo)
    return paciente_obj

@api_router.get("/pacientes", response_model=List[Paciente])
async def get_pacientes(token: str = Depends(verify_token)):
    pacientes = await db.pacientes.find().to_list(1000)
    return [Paciente(**parse_from_mongo(paciente)) for paciente in pacientes]

@api_router.get("/pacientes/{paciente_id}", response_model=Paciente)
async def get_paciente(paciente_id: str, token: str = Depends(verify_token)):
    paciente = await db.pacientes.find_one({"id": paciente_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return Paciente(**parse_from_mongo(paciente))

@api_router.put("/pacientes/{paciente_id}", response_model=Paciente)
async def actualizar_paciente(paciente_id: str, paciente_update: PacienteUpdate, token: str = Depends(verify_token)):
    paciente_existente = await db.pacientes.find_one({"id": paciente_id})
    if not paciente_existente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    update_data = {k: v for k, v in paciente_update.dict().items() if v is not None}
    
    # Recalcular edad si se actualiza fecha de nacimiento
    if 'fecha_nacimiento' in update_data:
        update_data['edad'] = calcular_edad(update_data['fecha_nacimiento'])
    
    # Obtener descripción del CIE-10 si se actualiza código
    if 'codigo_cie10' in update_data:
        cie10_code = await db.cie10_codes.find_one({"codigo": update_data['codigo_cie10']})
        if cie10_code:
            update_data['descripcion_cie10'] = cie10_code['descripcion']
    
    # Recalcular IMC si se actualiza peso o altura
    paciente_actual = Paciente(**parse_from_mongo(paciente_existente))
    peso = update_data.get('peso', paciente_actual.peso)
    altura = update_data.get('altura', paciente_actual.altura)
    
    if peso and altura:
        imc, estado_nutricional = calcular_imc_y_estado_nutricional(peso, altura)
        update_data['imc'] = imc
        update_data['estado_nutricional'] = estado_nutricional
    
    update_mongo = prepare_for_mongo(update_data)
    await db.pacientes.update_one({"id": paciente_id}, {"$set": update_mongo})
    
    paciente_actualizado = await db.pacientes.find_one({"id": paciente_id})
    return Paciente(**parse_from_mongo(paciente_actualizado))

@api_router.delete("/pacientes/{paciente_id}")
async def eliminar_paciente(paciente_id: str, token: str = Depends(verify_token)):
    result = await db.pacientes.delete_one({"id": paciente_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return {"mensaje": "Paciente eliminado exitosamente"}

@api_router.post("/pacientes/{paciente_id}/citas")
async def agregar_cita(paciente_id: str, cita: RegistroCita, token: str = Depends(verify_token)):
    paciente = await db.pacientes.find_one({"id": paciente_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cita_dict = cita.dict()
    cita_dict['fecha_cita'] = cita_dict['fecha_cita'].isoformat()
    
    await db.pacientes.update_one(
        {"id": paciente_id},
        {"$push": {"historial_citas": cita_dict}}
    )
    return {"mensaje": "Cita agregada exitosamente"}

@api_router.post("/pacientes/{paciente_id}/analisis")
async def agregar_analisis(paciente_id: str, analisis: AnalisisLaboratorio, token: str = Depends(verify_token)):
    paciente = await db.pacientes.find_one({"id": paciente_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    analisis_dict = analisis.dict()
    analisis_dict['fecha_analisis'] = analisis_dict['fecha_analisis'].isoformat()
    
    await db.pacientes.update_one(
        {"id": paciente_id},
        {"$push": {"analisis_laboratorio": analisis_dict}}
    )
    return {"mensaje": "Análisis de laboratorio agregado exitosamente"}

@api_router.post("/medicamentos", response_model=Medicamento)
async def crear_medicamento(medicamento: MedicamentoCreate, token: str = Depends(verify_token)):
    medicamento_obj = Medicamento(**medicamento.dict())
    await db.medicamentos.insert_one(medicamento_obj.dict())
    return medicamento_obj

@api_router.get("/medicamentos", response_model=List[Medicamento])
async def get_medicamentos(token: str = Depends(verify_token)):
    medicamentos = await db.medicamentos.find().to_list(1000)
    return [Medicamento(**medicamento) for medicamento in medicamentos]

@api_router.get("/medicamentos/search")
async def search_medicamentos(query: str, token: str = Depends(verify_token)):
    medicamentos = await db.medicamentos.find({
        "$or": [
            {"nombre": {"$regex": query, "$options": "i"}},
            {"categoria": {"$regex": query, "$options": "i"}}
        ]
    }).to_list(50)
    return [Medicamento(**medicamento) for medicamento in medicamentos]

@api_router.put("/medicamentos/{medicamento_id}/stock")
async def actualizar_stock(medicamento_id: str, nuevo_stock: int, token: str = Depends(verify_token)):
    result = await db.medicamentos.update_one(
        {"id": medicamento_id},
        {"$set": {"stock": nuevo_stock}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    return {"mensaje": "Stock actualizado exitosamente"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await initialize_cie10_codes()
    logger.info("Aplicación iniciada y códigos CIE-10 inicializados")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()