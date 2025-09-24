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
import re

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

class EstadoCita(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"

class AlertaTipo(str, Enum):
    STOCK_BAJO = "stock_bajo"
    VENCIMIENTO_CERCANO = "vencimiento_cercano"
    ALTA_ROTACION = "alta_rotacion"
    BAJA_ROTACION = "baja_rotacion"

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data.get('fecha_nacimiento'), date):
        data['fecha_nacimiento'] = data['fecha_nacimiento'].isoformat()
    if isinstance(data.get('created_at'), datetime):
        data['created_at'] = data['created_at'].isoformat()
    if isinstance(data.get('fecha_vencimiento'), date):
        data['fecha_vencimiento'] = data['fecha_vencimiento'].isoformat()
    if isinstance(data.get('fecha_cita'), date):
        data['fecha_cita'] = data['fecha_cita'].isoformat()
    if isinstance(data.get('fecha_hora'), datetime):
        data['fecha_hora'] = data['fecha_hora'].isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item.get('fecha_nacimiento'), str):
        item['fecha_nacimiento'] = datetime.fromisoformat(item['fecha_nacimiento']).date()
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    if isinstance(item.get('fecha_vencimiento'), str):
        item['fecha_vencimiento'] = datetime.fromisoformat(item['fecha_vencimiento']).date()
    if isinstance(item.get('fecha_cita'), str):
        item['fecha_cita'] = datetime.fromisoformat(item['fecha_cita']).date()
    if isinstance(item.get('fecha_hora'), str):
        item['fecha_hora'] = datetime.fromisoformat(item['fecha_hora'])
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

def clasificar_cie10_inteligente(diagnostico: str) -> Optional[str]:
    """Clasificación inteligente y ampliada de diagnósticos según CIE-10"""
    if not diagnostico:
        return None
    
    diagnostico_lower = diagnostico.lower()
    
    # Mapeo expandido y más inteligente de diagnósticos a códigos CIE-10
    clasificaciones = {
        # Enfermedades neurológicas (G00-G99)
        'hidrocefalia': 'G91.9',
        'hidrocefalias': 'G91.9',
        'hidrocéfalo': 'G91.9',
        'meningitis': 'G03.9',
        'encefalitis': 'G04.9',
        'epilepsia': 'G40.9',
        'convulsiones': 'R56.8',
        'parálisis cerebral': 'G80.9',
        'paralisis cerebral': 'G80.9',
        'microcefalia': 'Q02',
        'macrocefalia': 'Q75.3',
        'espina bífida': 'Q05.9',
        'espina bifida': 'Q05.9',
        
        # Enfermedades infecciosas y parasitarias (A00-B99)
        'diarrea': 'A09.9',
        'gastroenteritis': 'A09.0',
        'rotavirus': 'A08.0',
        'salmonela': 'A02.9',
        'salmonella': 'A02.9',
        'shigella': 'A03.9',
        'shigelosis': 'A03.9',
        'cólera': 'A00.9',
        'fiebre tifoidea': 'A01.0',
        'hepatitis a': 'B15.9',
        'hepatitis b': 'B16.9',
        'varicela': 'B01.9',
        'sarampión': 'B05.9',
        'rubeola': 'B06.9',
        'rubéola': 'B06.9',
        'parotiditis': 'B26.9',
        'paperas': 'B26.9',
        'mononucleosis': 'B27.9',
        'citomegalovirus': 'B25.9',
        'herpes simple': 'B00.9',
        'herpes zoster': 'B02.9',
        'candidiasis': 'B37.9',
        'candida': 'B37.9',
        
        # Enfermedades respiratorias (J00-J99)
        'resfriado': 'J00',
        'resfrio': 'J00',
        'gripe': 'J11.1',
        'influenza': 'J11.1',
        'rinitis': 'J00',
        'rinofaringitis': 'J00',
        'sinusitis': 'J01.9',
        'faringitis': 'J02.9',
        'dolor de garganta': 'J02.9',
        'amigdalitis': 'J03.9',
        'anginas': 'J03.9',
        'laringitis': 'J04.0',
        'traqueitis': 'J04.1',
        'crup': 'J05.0',
        'epiglotitis': 'J05.1',
        'bronquitis': 'J20.9',
        'bronquiolitis': 'J21.9',
        'neumonía': 'J18.9',
        'neumonia': 'J18.9',
        'pulmonía': 'J18.9',
        'pulmonia': 'J18.9',
        'asma': 'J45.9',
        'broncoespasmo': 'J45.9',
        'tos': 'R05',
        'tos ferina': 'A37.9',
        
        # Enfermedades del oído (H60-H95)
        'otitis': 'H66.9',
        'otitis media': 'H66.9',
        'otitis externa': 'H60.9',
        'dolor de oído': 'H92.0',
        'otalgia': 'H92.0',
        
        # Enfermedades del ojo (H00-H59)
        'conjuntivitis': 'H10.9',
        'blefaritis': 'H01.9',
        'orzuelo': 'H00.0',
        'chalazión': 'H00.1',
        
        # Enfermedades gastrointestinales (K00-K93)
        'dolor abdominal': 'R10.4',
        'dolor estómago': 'K30',
        'dolor de estomago': 'K30',
        'gastritis': 'K29.7',
        'úlcera gástrica': 'K25.9',
        'ulcera gastrica': 'K25.9',
        'reflujo': 'K21.9',
        'estreñimiento': 'K59.0',
        'constipación': 'K59.0',
        'apendicitis': 'K37',
        'intususcepción': 'K56.1',
        'intususcepcio': 'K56.1',
        'invaginación': 'K56.1',
        'cólico intestinal': 'K59.1',
        'colico intestinal': 'K59.1',
        
        # Enfermedades de la piel (L00-L99)
        'dermatitis': 'L30.9',
        'eccema': 'L20.9',
        'dermatitis atópica': 'L20.9',
        'dermatitis atopica': 'L20.9',
        'dermatitis del pañal': 'L22',
        'dermatitis del panal': 'L22',
        'impétigo': 'L01.0',
        'impetigo': 'L01.0',
        'celulitis': 'L03.9',
        'urticaria': 'L50.9',
        'sarpullido': 'L30.9',
        'erupción': 'R21',
        'erupcion': 'R21',
        'acné': 'L70.9',
        'acne': 'L70.9',
        'psoriasis': 'L40.9',
        'vitíligo': 'L80',
        'vitiligo': 'L80',
        
        # Síntomas y signos generales (R00-R99)
        'fiebre': 'R50.9',
        'hipertermia': 'R50.9',
        'hipotermia': 'R68.0',
        'vómito': 'R11',
        'vomito': 'R11',
        'náusea': 'R11',
        'nausea': 'R11',
        'mareo': 'R42',
        'cefalea': 'R51',
        'dolor de cabeza': 'R51',
        'fatiga': 'R53',
        'cansancio': 'R53',
        'debilidad': 'R53',
        'pérdida de peso': 'R63.4',
        'perdida de peso': 'R63.4',
        'ganancia de peso': 'R63.5',
        'sudoración': 'R61',
        'sudoracion': 'R61',
        'palidez': 'R23.1',
        'cianosis': 'R23.0',
        'ictericia': 'R17',
        'convulsión': 'R56.9',
        'convulsion': 'R56.9',
        
        # Trastornos nutricionales y metabólicos (E00-E89)
        'desnutrición': 'E44.1',
        'desnutricion': 'E44.1',
        'marasmo': 'E41',
        'kwashiorkor': 'E40',
        'obesidad': 'E66.9',
        'diabetes': 'E14.9',
        'hipoglucemia': 'E16.2',
        'hiperglucemia': 'R73.9',
        'raquitismo': 'E55.0',
        'escorbuto': 'E54',
        'anemia': 'D64.9',
        'anemia ferropénica': 'D50.9',
        'anemia ferropenica': 'D50.9',
        
        # Trastornos mentales y del comportamiento (F00-F99)
        'autismo': 'F84.0',
        'tdah': 'F90.9',
        'hiperactividad': 'F90.9',
        'ansiedad': 'F41.9',
        'depresión': 'F32.9',
        'depresion': 'F32.9',
        'trastorno del sueño': 'G47.9',
        'trastorno del sueno': 'G47.9',
        'insomnio': 'G47.0',
        
        # Malformaciones congénitas (Q00-Q99)
        'cardiopatía congénita': 'Q24.9',
        'cardiopatia congenita': 'Q24.9',
        'labio leporino': 'Q36.9',
        'paladar hendido': 'Q35.9',
        'pie zambo': 'Q66.8',
        'luxación congénita cadera': 'Q65.9',
        'luxacion congenita cadera': 'Q65.9',
        
        # Traumatismos (S00-T98)
        'fractura': 'S72.9',
        'luxación': 'S73.0',
        'luxacion': 'S73.0',
        'esguince': 'S83.5',
        'contusión': 'S30.1',
        'contusion': 'S30.1',
        'herida': 'T14.1',
        'quemadura': 'T30.0',
        'intoxicación': 'T65.9',
        'intoxicacion': 'T65.9',
        'envenenamiento': 'T65.9'
    }
    
    # Búsqueda exacta primero
    for palabra, codigo in clasificaciones.items():
        if palabra in diagnostico_lower:
            return codigo
    
    # Búsqueda por palabras clave si no hay coincidencia exacta
    palabras = diagnostico_lower.split()
    for palabra in palabras:
        if len(palabra) > 3:  # Solo considerar palabras de más de 3 caracteres
            for clave, codigo in clasificaciones.items():
                if palabra in clave or clave in palabra:
                    return codigo
    
    return None

def obtener_capitulo_cie10(codigo: str) -> str:
    """Obtiene el capítulo CIE-10 según el código"""
    if not codigo:
        return "No clasificado"
    
    primera_letra = codigo[0].upper()
    
    capitulos = {
        'A': "Capítulo I – Ciertas enfermedades infecciosas y parasitarias (A00-B99)",
        'B': "Capítulo I – Ciertas enfermedades infecciosas y parasitarias (A00-B99)",
        'C': "Capítulo II – Neoplasias (C00-D48)",
        'D': "Capítulo III – Enfermedades de la sangre y órganos hematopoyéticos (D50-D89)",
        'E': "Capítulo IV – Enfermedades endocrinas, nutricionales y metabólicas (E00-E90)",
        'F': "Capítulo V – Trastornos mentales y del comportamiento (F00-F99)",
        'G': "Capítulo VI – Enfermedades del sistema nervioso (G00-G99)",
        'H': "Capítulo VII – Enfermedades del ojo y del oído (H00-H95)",
        'I': "Capítulo IX – Enfermedades del sistema circulatorio (I00-I99)",
        'J': "Capítulo X – Enfermedades del sistema respiratorio (J00-J99)",
        'K': "Capítulo XI – Enfermedades del sistema digestivo (K00-K93)",
        'L': "Capítulo XII – Enfermedades de la piel y tejido subcutáneo (L00-L99)",
        'M': "Capítulo XIII – Enfermedades del sistema osteomuscular (M00-M99)",
        'N': "Capítulo XIV – Enfermedades del sistema genitourinario (N00-N99)",
        'O': "Capítulo XV – Embarazo, parto y puerperio (O00-O99)",
        'P': "Capítulo XVI – Ciertas afecciones originadas en el período perinatal (P00-P96)",
        'Q': "Capítulo XVII – Malformaciones congénitas (Q00-Q99)",
        'R': "Capítulo XVIII – Síntomas, signos y hallazgos anormales (R00-R99)",
        'S': "Capítulo XIX – Traumatismos, envenenamientos (S00-T98)",
        'T': "Capítulo XIX – Traumatismos, envenenamientos (S00-T98)",
        'V': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
        'W': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
        'X': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
        'Y': "Capítulo XX – Causas externas de morbilidad y mortalidad (V01-Y98)",
        'Z': "Capítulo XXI – Factores que influyen en el estado de salud (Z00-Z99)"
    }
    
    return capitulos.get(primera_letra, "No clasificado")

def calcular_precios_farmacia_detallado(costo_unitario: float, impuesto: float = 0, 
                                      escala_compra: str = "sin_escala", 
                                      descuento: float = 0) -> Dict:
    """Sistema completo de cálculo de precios con margen garantizado del 25%"""
    
    # 1. Calcular costo real considerando impuesto
    costo_con_impuesto = costo_unitario * (1 + impuesto / 100)
    
    # 2. Calcular costo real considerando escala de compra
    costo_real = costo_con_impuesto
    unidades_recibidas = 1
    
    if escala_compra and escala_compra != "sin_escala":
        try:
            # Ejemplo: "10+3" significa comprar 10 y recibir 13
            if '+' in escala_compra:
                partes = escala_compra.split('+')
                if len(partes) == 2:
                    compra = float(partes[0])
                    bonus = float(partes[1])
                    recibe = compra + bonus
                    # Costo real = (total pagado) / (total recibido)
                    costo_real = (costo_con_impuesto * compra) / recibe
                    unidades_recibidas = recibe
        except Exception:
            costo_real = costo_con_impuesto
    
    # 3. Calcular precio base (sin descuento) con margen del 25%
    # Fórmula: Precio Base = Costo Real / (1 - 0.25)
    precio_base = costo_real / (1 - 0.25)
    
    # 4. Calcular precio público (con descuento) manteniendo margen del 25%
    # Fórmula: Precio Público = Costo Real / ((1 - 0.25) * (1 - Descuento))
    if descuento > 0:
        precio_publico = costo_real / ((1 - 0.25) * (1 - descuento / 100))
    else:
        precio_publico = precio_base
    
    # 5. Verificar margen final después del descuento
    precio_final_cliente = precio_publico * (1 - descuento / 100)
    margen_final = ((precio_final_cliente - costo_real) / precio_final_cliente) * 100
    
    return {
        'costo_unitario_original': round(costo_unitario, 2),
        'costo_con_impuesto': round(costo_con_impuesto, 2),
        'costo_real': round(costo_real, 2),
        'escala_aplicada': escala_compra,
        'unidades_recibidas': unidades_recibidas,
        'precio_base': round(precio_base, 2),
        'precio_publico': round(precio_publico, 2),
        'precio_final_cliente': round(precio_final_cliente, 2),
        'margen_utilidad_final': round(margen_final, 2),
        'descuento_aplicado': descuento,
        'impuesto_aplicado': impuesto,
        'margen_garantizado': margen_final >= 24.5  # Tolerancia del 0.5%
    }

def generar_alertas_farmacia(medicamentos: List[Dict]) -> List[Dict]:
    """Genera alertas inteligentes de farmacia"""
    alertas = []
    
    for med in medicamentos:
        # Alerta de stock bajo
        if med.get('stock', 0) <= med.get('stock_minimo', 5):
            alertas.append({
                'tipo': AlertaTipo.STOCK_BAJO,
                'medicamento_id': med.get('id'),
                'medicamento_nombre': med.get('nombre'),
                'mensaje': f"Stock crítico: {med.get('stock', 0)} unidades (mínimo: {med.get('stock_minimo', 5)})",
                'prioridad': 'alta' if med.get('stock', 0) == 0 else 'media',
                'fecha_alerta': datetime.now(timezone.utc)
            })
        
        # Alerta de vencimiento cercano (30 días)
        if med.get('fecha_vencimiento'):
            try:
                if isinstance(med['fecha_vencimiento'], str):
                    fecha_venc = datetime.fromisoformat(med['fecha_vencimiento']).date()
                else:
                    fecha_venc = med['fecha_vencimiento']
                
                dias_hasta_vencimiento = (fecha_venc - date.today()).days
                
                if 0 <= dias_hasta_vencimiento <= 30:
                    prioridad = 'alta' if dias_hasta_vencimiento <= 7 else 'media'
                    alertas.append({
                        'tipo': AlertaTipo.VENCIMIENTO_CERCANO,
                        'medicamento_id': med.get('id'),
                        'medicamento_nombre': med.get('nombre'),
                        'mensaje': f"Vence en {dias_hasta_vencimiento} días ({fecha_venc.strftime('%d/%m/%Y')})",
                        'prioridad': prioridad,
                        'fecha_alerta': datetime.now(timezone.utc)
                    })
            except Exception:
                pass
    
    return alertas

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
    capitulo: str = ""

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
    tratamiento_medico: str = ""
    medicamentos_recetados: List[str] = []  # IDs de medicamentos
    codigo_cie10: Optional[str] = None
    descripcion_cie10: Optional[str] = None
    capitulo_cie10: Optional[str] = None
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
    tratamiento_medico: str = ""
    medicamentos_recetados: List[str] = []
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
    tratamiento_medico: Optional[str] = None
    medicamentos_recetados: Optional[List[str]] = None
    codigo_cie10: Optional[str] = None
    gravedad_diagnostico: Optional[GravidadDiagnostico] = None
    peso: Optional[float] = None
    altura: Optional[float] = None
    contacto_recordatorios: Optional[str] = None

class Medicamento(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    descripcion: str
    codigo_barras: str = ""
    stock: int
    stock_minimo: int = 5
    costo_unitario: float  # Costo base sin impuestos
    impuesto: float = 15  # Porcentaje de impuesto
    escala_compra: str = "sin_escala"  # Ej: "10+3", "1+1"
    descuento_aplicable: float = 0  # Porcentaje de descuento
    costo_real: float = 0  # Calculado automáticamente
    precio_base: float = 0  # Calculado automáticamente
    precio_publico: float = 0  # Calculado automáticamente
    margen_utilidad: float = 0  # Calculado automáticamente
    categoria: str
    lote: str = ""
    fecha_vencimiento: Optional[date] = None
    proveedor: str = ""
    indicaciones: str = ""
    contraindicaciones: str = ""
    dosis_pediatrica: str = ""
    ventas_mes: int = 0  # Para alertas de rotación
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MedicamentoCreate(BaseModel):
    nombre: str
    descripcion: str
    codigo_barras: str = ""
    stock: int
    stock_minimo: int = 5
    costo_unitario: float
    impuesto: float = 15
    escala_compra: str = "sin_escala"
    descuento_aplicable: float = 0
    categoria: str
    lote: str = ""
    fecha_vencimiento: Optional[date] = None
    proveedor: str = ""
    indicaciones: str = ""
    contraindicaciones: str = ""
    dosis_pediatrica: str = ""

class CitaMedica(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    paciente_id: str
    paciente_nombre: str
    fecha_hora: datetime
    motivo: str
    estado: EstadoCita = EstadoCita.PENDIENTE
    doctor: str
    notas: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CitaMedicaCreate(BaseModel):
    paciente_id: str
    fecha_hora: datetime
    motivo: str
    doctor: str
    notas: str = ""

class CitaRapida(BaseModel):
    paciente_id: str
    motivo: str = "Seguimiento"
    doctor: str = "Dr. Usuario"
    dias_adelante: int = 7  # Programar para dentro de X días

class AlertaFarmacia(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: AlertaTipo
    medicamento_id: str
    medicamento_nombre: str
    mensaje: str
    prioridad: str  # alta, media, baja
    fecha_alerta: datetime
    leida: bool = False

# Authentication function
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != "valid_token_1970":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Initialize expanded CIE-10 codes
async def initialize_cie10_codes_expandido():
    cie10_codes = [
        # Enfermedades neurológicas
        {"codigo": "G91.9", "descripcion": "Hidrocefalia, no especificada", "categoria": "Enfermedades neurológicas"},
        {"codigo": "G03.9", "descripcion": "Meningitis, no especificada", "categoria": "Enfermedades neurológicas"},
        {"codigo": "G04.9", "descripcion": "Encefalitis, no especificada", "categoria": "Enfermedades neurológicas"},
        {"codigo": "G40.9", "descripcion": "Epilepsia, no especificada", "categoria": "Enfermedades neurológicas"},
        {"codigo": "G80.9", "descripcion": "Parálisis cerebral, no especificada", "categoria": "Enfermedades neurológicas"},
        {"codigo": "Q02", "descripcion": "Microcefalia", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q75.3", "descripcion": "Macrocefalia", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q05.9", "descripcion": "Espina bífida, no especificada", "categoria": "Malformaciones congénitas"},
        
        # Infecciones respiratorias agudas (expandido)
        {"codigo": "J00", "descripcion": "Rinofaringitis aguda (resfriado común)", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J01.9", "descripcion": "Sinusitis aguda, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J02.9", "descripcion": "Faringitis aguda, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J03.9", "descripcion": "Amigdalitis aguda, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J04.0", "descripcion": "Laringitis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J04.1", "descripcion": "Traqueítis aguda", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J05.0", "descripcion": "Laringitis obstructiva aguda (crup)", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J06.9", "descripcion": "Infección aguda de vías respiratorias superiores", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J11.1", "descripcion": "Influenza con otras manifestaciones respiratorias", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J12.9", "descripcion": "Neumonía viral, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J13", "descripcion": "Neumonía por Streptococcus pneumoniae", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J18.9", "descripcion": "Neumonía, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J20.9", "descripcion": "Bronquitis aguda, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J21.9", "descripcion": "Bronquiolitis aguda, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J45.9", "descripcion": "Asma, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "A37.9", "descripcion": "Tos ferina, no especificada", "categoria": "Enfermedades infecciosas"},
        
        # Enfermedades del oído (expandido)
        {"codigo": "H60.9", "descripcion": "Otitis externa, no especificada", "categoria": "Enfermedades del oído"},
        {"codigo": "H65.9", "descripcion": "Otitis media no supurativa, no especificada", "categoria": "Enfermedades del oído"},
        {"codigo": "H66.9", "descripcion": "Otitis media, no especificada", "categoria": "Enfermedades del oído"},
        {"codigo": "H92.0", "descripcion": "Otalgia", "categoria": "Enfermedades del oído"},
        
        # Enfermedades del ojo
        {"codigo": "H10.9", "descripcion": "Conjuntivitis, no especificada", "categoria": "Enfermedades del ojo"},
        {"codigo": "H00.0", "descripcion": "Orzuelo", "categoria": "Enfermedades del ojo"},
        {"codigo": "H01.9", "descripcion": "Blefaritis, no especificada", "categoria": "Enfermedades del ojo"},
        
        # Enfermedades gastrointestinales (expandido)
        {"codigo": "A09.9", "descripcion": "Diarrea y gastroenteritis de presunto origen infeccioso", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "A09.0", "descripcion": "Gastroenteritis y colitis de origen infeccioso", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "A08.0", "descripcion": "Enteritis por rotavirus", "categoria": "Enfermedades infecciosas"},
        {"codigo": "K30", "descripcion": "Dispepsia funcional", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K29.7", "descripcion": "Gastritis, no especificada", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K21.9", "descripcion": "Enfermedad de reflujo gastroesofágico", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K59.0", "descripcion": "Estreñimiento", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K37", "descripcion": "Apendicitis, no especificada", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "K56.1", "descripcion": "Intususcepción", "categoria": "Enfermedades gastrointestinales"},
        
        # Enfermedades de la piel (expandido)
        {"codigo": "L20.9", "descripcion": "Dermatitis atópica, no especificada", "categoria": "Enfermedades de la piel"},
        {"codigo": "L21.9", "descripcion": "Dermatitis seborreica, no especificada", "categoria": "Enfermedades de la piel"},
        {"codigo": "L22", "descripcion": "Dermatitis del pañal", "categoria": "Enfermedades de la piel"},
        {"codigo": "L30.9", "descripcion": "Dermatitis, no especificada", "categoria": "Enfermedades de la piel"},
        {"codigo": "L01.0", "descripcion": "Impétigo", "categoria": "Enfermedades de la piel"},
        {"codigo": "L03.9", "descripcion": "Celulitis, no especificada", "categoria": "Enfermedades de la piel"},
        {"codigo": "L50.9", "descripcion": "Urticaria, no especificada", "categoria": "Enfermedades de la piel"},
        {"codigo": "L70.9", "descripcion": "Acné, no especificado", "categoria": "Enfermedades de la piel"},
        
        # Síntomas y signos (expandido)
        {"codigo": "R50.9", "descripcion": "Fiebre, no especificada", "categoria": "Síntomas y signos"},
        {"codigo": "R05", "descripcion": "Tos", "categoria": "Síntomas y signos"},
        {"codigo": "R06.2", "descripcion": "Sibilancias", "categoria": "Síntomas y signos"},
        {"codigo": "R10.4", "descripcion": "Otros dolores abdominales y los no especificados", "categoria": "Síntomas y signos"},
        {"codigo": "R11", "descripcion": "Náusea y vómito", "categoria": "Síntomas y signos"},
        {"codigo": "R51", "descripcion": "Cefalea", "categoria": "Síntomas y signos"},
        {"codigo": "R53", "descripcion": "Malestar y fatiga", "categoria": "Síntomas y signos"},
        {"codigo": "R56.8", "descripcion": "Otras convulsiones y las no especificadas", "categoria": "Síntomas y signos"},
        {"codigo": "R17", "descripcion": "Ictericia no especificada", "categoria": "Síntomas y signos"},
        {"codigo": "R21", "descripcion": "Erupción cutánea y otras erupciones cutáneas no específicas", "categoria": "Síntomas y signos"},
        
        # Trastornos nutricionales (expandido)
        {"codigo": "E40", "descripcion": "Kwashiorkor", "categoria": "Trastornos nutricionales"},
        {"codigo": "E41", "descripcion": "Marasmo nutricional", "categoria": "Trastornos nutricionales"},
        {"codigo": "E44.1", "descripcion": "Desnutrición proteico-calórica leve", "categoria": "Trastornos nutricionales"},
        {"codigo": "E66.9", "descripcion": "Obesidad, no especificada", "categoria": "Trastornos nutricionales"},
        {"codigo": "E55.0", "descripcion": "Raquitismo activo", "categoria": "Trastornos nutricionales"},
        {"codigo": "D50.9", "descripcion": "Anemia por deficiencia de hierro", "categoria": "Enfermedades de la sangre"},
        {"codigo": "D64.9", "descripcion": "Anemia, no especificada", "categoria": "Enfermedades de la sangre"},
        
        # Enfermedades infecciosas (expandido)
        {"codigo": "A00.9", "descripcion": "Cólera, no especificado", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A01.0", "descripcion": "Fiebre tifoidea", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A02.9", "descripcion": "Infección por Salmonella, no especificada", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A03.9", "descripcion": "Shigelosis, no especificada", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B00.9", "descripcion": "Infección por virus del herpes simple", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B01.9", "descripcion": "Varicela sin complicación", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B02.9", "descripcion": "Herpes zóster sin complicación", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B05.9", "descripcion": "Sarampión sin complicación", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B06.9", "descripcion": "Rubéola sin complicación", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B15.9", "descripcion": "Hepatitis A sin coma hepático", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B25.9", "descripcion": "Enfermedad por citomegalovirus, no especificada", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B26.9", "descripcion": "Parotiditis, no especificada", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B37.9", "descripcion": "Candidiasis, no especificada", "categoria": "Enfermedades infecciosas"},
        
        # Malformaciones congénitas
        {"codigo": "Q24.9", "descripcion": "Malformación congénita del corazón", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q36.9", "descripcion": "Labio leporino, no especificado", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q35.9", "descripcion": "Fisura del paladar, no especificada", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q65.9", "descripcion": "Luxación congénita de cadera", "categoria": "Malformaciones congénitas"},
        
        # Trastornos mentales
        {"codigo": "F84.0", "descripcion": "Autismo infantil", "categoria": "Trastornos mentales"},
        {"codigo": "F90.9", "descripcion": "Trastorno hipercinético, no especificado", "categoria": "Trastornos mentales"},
        {"codigo": "F32.9", "descripcion": "Episodio depresivo, no especificado", "categoria": "Trastornos mentales"},
        {"codigo": "F41.9", "descripcion": "Trastorno de ansiedad, no especificado", "categoria": "Trastornos mentales"}
    ]
    
    existing_count = await db.cie10_codes.count_documents({})
    if existing_count < 50:  # Solo actualizar si no hay muchos códigos
        # Limpiar códigos existentes
        await db.cie10_codes.delete_many({})
        
        # Insertar códigos expandidos
        for code in cie10_codes:
            code['capitulo'] = obtener_capitulo_cie10(code['codigo'])
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

@api_router.post("/cie10/clasificar")
async def clasificar_diagnostico_inteligente(diagnostico: str, token: str = Depends(verify_token)):
    """Clasificación inteligente y expandida de diagnósticos según CIE-10"""
    codigo_sugerido = clasificar_cie10_inteligente(diagnostico)
    
    if codigo_sugerido:
        cie10_code = await db.cie10_codes.find_one({"codigo": codigo_sugerido})
        if cie10_code:
            return {
                "codigo": codigo_sugerido,
                "descripcion": cie10_code["descripcion"],
                "capitulo": obtener_capitulo_cie10(codigo_sugerido),
                "sugerencia": True,
                "confianza": "alta"  # Nivel de confianza en la sugerencia
            }
    
    # Si no encuentra coincidencia exacta, buscar similares
    palabras = diagnostico.lower().split()
    for palabra in palabras:
        if len(palabra) > 4:
            codes = await db.cie10_codes.find({
                "descripcion": {"$regex": palabra, "$options": "i"}
            }).to_list(5)
            
            if codes:
                return {
                    "codigo": codes[0]["codigo"],
                    "descripcion": codes[0]["descripcion"],
                    "capitulo": obtener_capitulo_cie10(codes[0]["codigo"]),
                    "sugerencia": True,
                    "confianza": "media",
                    "alternativas": [{"codigo": c["codigo"], "descripcion": c["descripcion"]} for c in codes[1:4]]
                }
    
    return {
        "codigo": None,
        "descripcion": None,
        "capitulo": None,
        "sugerencia": False,
        "confianza": "baja",
        "mensaje": "No se encontró clasificación automática. Busque manualmente en la base CIE-10."
    }

@api_router.post("/pacientes", response_model=Paciente)
async def crear_paciente(paciente_data: PacienteCreate, token: str = Depends(verify_token)):
    paciente_dict = paciente_data.dict()
    
    # Calcular edad automáticamente
    paciente_dict['edad'] = calcular_edad(paciente_data.fecha_nacimiento)
    
    # Clasificación automática CIE-10 inteligente
    if paciente_data.diagnostico_clinico and not paciente_data.codigo_cie10:
        codigo_automatico = clasificar_cie10_inteligente(paciente_data.diagnostico_clinico)
        if codigo_automatico:
            paciente_dict['codigo_cie10'] = codigo_automatico
    
    # Obtener descripción del CIE-10 si se proporcionó código
    if paciente_dict.get('codigo_cie10'):
        cie10_code = await db.cie10_codes.find_one({"codigo": paciente_dict['codigo_cie10']})
        if cie10_code:
            paciente_dict['descripcion_cie10'] = cie10_code['descripcion']
            paciente_dict['capitulo_cie10'] = obtener_capitulo_cie10(paciente_dict['codigo_cie10'])
    
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
    
    # Clasificación automática CIE-10 inteligente si se actualiza el diagnóstico
    if 'diagnostico_clinico' in update_data and not update_data.get('codigo_cie10'):
        codigo_automatico = clasificar_cie10_inteligente(update_data['diagnostico_clinico'])
        if codigo_automatico:
            update_data['codigo_cie10'] = codigo_automatico
    
    # Obtener descripción del CIE-10 si se actualiza código
    if 'codigo_cie10' in update_data:
        cie10_code = await db.cie10_codes.find_one({"codigo": update_data['codigo_cie10']})
        if cie10_code:
            update_data['descripcion_cie10'] = cie10_code['descripcion']
            update_data['capitulo_cie10'] = obtener_capitulo_cie10(update_data['codigo_cie10'])
    
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

@api_router.post("/pacientes/{paciente_id}/cita-rapida")
async def crear_cita_rapida(paciente_id: str, cita_rapida: CitaRapida, token: str = Depends(verify_token)):
    """Crear cita rápida para un paciente"""
    paciente = await db.pacientes.find_one({"id": paciente_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Calcular fecha y hora de la cita (días adelante + hora por defecto 9:00 AM)
    from datetime import timedelta
    fecha_cita = datetime.now(timezone.utc) + timedelta(days=cita_rapida.dias_adelante)
    fecha_cita = fecha_cita.replace(hour=9, minute=0, second=0, microsecond=0)  # 9:00 AM
    
    cita_data = CitaMedicaCreate(
        paciente_id=paciente_id,
        fecha_hora=fecha_cita,
        motivo=cita_rapida.motivo,
        doctor=cita_rapida.doctor
    )
    
    cita_dict = cita_data.dict()
    cita_dict['paciente_nombre'] = paciente['nombre_completo']
    
    cita_obj = CitaMedica(**cita_dict)
    await db.citas.insert_one(prepare_for_mongo(cita_obj.dict()))
    
    return {
        "mensaje": f"Cita rápida creada para {paciente['nombre_completo']}",
        "fecha_hora": fecha_cita.isoformat(),
        "cita_id": cita_obj.id
    }

# Medicamentos con filtro inteligente para el tratamiento
@api_router.get("/medicamentos/disponibles")
async def get_medicamentos_disponibles(buscar: str = "", token: str = Depends(verify_token)):
    """Obtener medicamentos disponibles (con stock) para tratamiento"""
    query = {"stock": {"$gt": 0}}  # Solo medicamentos con stock
    
    if buscar:
        query["$or"] = [
            {"nombre": {"$regex": buscar, "$options": "i"}},
            {"categoria": {"$regex": buscar, "$options": "i"}},
            {"indicaciones": {"$regex": buscar, "$options": "i"}}
        ]
    
    medicamentos = await db.medicamentos.find(query).to_list(20)
    
    return [{
        "id": med["id"],
        "nombre": med["nombre"],
        "categoria": med["categoria"],
        "stock": med["stock"],
        "dosis_pediatrica": med.get("dosis_pediatrica", ""),
        "indicaciones": med.get("indicaciones", "")[:100] + "..." if len(med.get("indicaciones", "")) > 100 else med.get("indicaciones", "")
    } for med in medicamentos]

# Endpoints de medicamentos con sistema de precios detallado
@api_router.post("/medicamentos/calcular-precios-detallado")
async def calcular_precios_detallado(
    costo_unitario: float,
    impuesto: float = 15,
    escala_compra: str = "sin_escala",
    descuento: float = 0,
    token: str = Depends(verify_token)
):
    """Calculadora detallada de precios con margen garantizado del 25%"""
    resultado = calcular_precios_farmacia_detallado(costo_unitario, impuesto, escala_compra, descuento)
    return resultado

@api_router.post("/medicamentos", response_model=Medicamento)
async def crear_medicamento(medicamento: MedicamentoCreate, token: str = Depends(verify_token)):
    medicamento_dict = medicamento.dict()
    
    # Calcular precios automáticamente con el sistema detallado
    precios = calcular_precios_farmacia_detallado(
        medicamento.costo_unitario,
        medicamento.impuesto,
        medicamento.escala_compra,
        medicamento.descuento_aplicable
    )
    
    # Actualizar con los precios calculados
    medicamento_dict.update({
        'costo_real': precios['costo_real'],
        'precio_base': precios['precio_base'],
        'precio_publico': precios['precio_publico'],
        'margen_utilidad': precios['margen_utilidad_final']
    })
    
    medicamento_obj = Medicamento(**medicamento_dict)
    await db.medicamentos.insert_one(prepare_for_mongo(medicamento_obj.dict()))
    return medicamento_obj

@api_router.get("/medicamentos", response_model=List[Medicamento])
async def get_medicamentos(token: str = Depends(verify_token)):
    medicamentos = await db.medicamentos.find().to_list(1000)
    return [Medicamento(**parse_from_mongo(medicamento)) for medicamento in medicamentos]

@api_router.get("/medicamentos/alertas")
async def get_alertas_farmacia(token: str = Depends(verify_token)):
    """Obtener todas las alertas de farmacia"""
    medicamentos = await db.medicamentos.find().to_list(1000)
    medicamentos_parsed = [parse_from_mongo(med) for med in medicamentos]
    
    alertas = generar_alertas_farmacia([med.dict() if hasattr(med, 'dict') else med for med in medicamentos_parsed])
    
    return {
        "total_alertas": len(alertas),
        "alertas_por_tipo": {
            "stock_bajo": len([a for a in alertas if a['tipo'] == AlertaTipo.STOCK_BAJO]),
            "vencimiento_cercano": len([a for a in alertas if a['tipo'] == AlertaTipo.VENCIMIENTO_CERCANO])
        },
        "alertas": alertas[:20]  # Limitar a 20 alertas
    }

@api_router.get("/medicamentos/vencer")
async def medicamentos_por_vencer(dias: int = 30, token: str = Depends(verify_token)):
    """Medicamentos que vencen en X días"""
    from datetime import timedelta
    fecha_limite = date.today() + timedelta(days=dias)
    
    medicamentos = await db.medicamentos.find({
        "fecha_vencimiento": {"$lte": fecha_limite.isoformat()}
    }).to_list(100)
    
    return [Medicamento(**parse_from_mongo(med)) for med in medicamentos]

@api_router.get("/medicamentos/stock-bajo")
async def medicamentos_stock_bajo(token: str = Depends(verify_token)):
    """Medicamentos con stock por debajo del mínimo"""
    medicamentos = await db.medicamentos.find({
        "$expr": {"$lte": ["$stock", "$stock_minimo"]}
    }).to_list(100)
    
    return [Medicamento(**parse_from_mongo(med)) for med in medicamentos]

@api_router.get("/medicamentos/search")
async def search_medicamentos(query: str, token: str = Depends(verify_token)):
    medicamentos = await db.medicamentos.find({
        "$or": [
            {"nombre": {"$regex": query, "$options": "i"}},
            {"categoria": {"$regex": query, "$options": "i"}},
            {"codigo_barras": query}
        ]
    }).to_list(50)
    return [Medicamento(**parse_from_mongo(medicamento)) for medicamento in medicamentos]

@api_router.put("/medicamentos/{medicamento_id}/stock")
async def actualizar_stock(medicamento_id: str, nuevo_stock: int, token: str = Depends(verify_token)):
    result = await db.medicamentos.update_one(
        {"id": medicamento_id},
        {"$set": {"stock": nuevo_stock}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    return {"mensaje": "Stock actualizado exitosamente"}

# Endpoints de citas médicas
@api_router.post("/citas", response_model=CitaMedica)
async def crear_cita(cita: CitaMedicaCreate, token: str = Depends(verify_token)):
    # Verificar que el paciente existe
    paciente = await db.pacientes.find_one({"id": cita.paciente_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    cita_dict = cita.dict()
    cita_dict['paciente_nombre'] = paciente['nombre_completo']
    
    cita_obj = CitaMedica(**cita_dict)
    await db.citas.insert_one(prepare_for_mongo(cita_obj.dict()))
    return cita_obj

@api_router.get("/citas", response_model=List[CitaMedica])
async def get_citas(fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None, token: str = Depends(verify_token)):
    query = {}
    if fecha_inicio and fecha_fin:
        query["fecha_hora"] = {
            "$gte": datetime.combine(fecha_inicio, datetime.min.time()).isoformat(),
            "$lte": datetime.combine(fecha_fin, datetime.max.time()).isoformat()
        }
    
    citas = await db.citas.find(query).to_list(1000)
    return [CitaMedica(**parse_from_mongo(cita)) for cita in citas]

@api_router.get("/citas/semana")
async def get_citas_semana(token: str = Depends(verify_token)):
    """Obtiene las citas de la semana actual"""
    from datetime import timedelta
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    query = {
        "fecha_hora": {
            "$gte": datetime.combine(inicio_semana, datetime.min.time()).isoformat(),
            "$lte": datetime.combine(fin_semana, datetime.max.time()).isoformat()
        }
    }
    
    citas = await db.citas.find(query).to_list(1000)
    return [CitaMedica(**parse_from_mongo(cita)) for cita in citas]

@api_router.get("/citas/dos-semanas")
async def get_citas_dos_semanas(fecha_inicio: Optional[date] = None, token: str = Depends(verify_token)):
    """Obtiene las citas de dos semanas consecutivas a partir de una fecha"""
    from datetime import timedelta
    
    if not fecha_inicio:
        hoy = date.today()
        inicio_periodo = hoy - timedelta(days=hoy.weekday())  # Inicio de semana actual
    else:
        inicio_periodo = fecha_inicio
    
    fin_periodo = inicio_periodo + timedelta(days=13)  # 14 días = 2 semanas
    
    query = {
        "fecha_hora": {
            "$gte": datetime.combine(inicio_periodo, datetime.min.time()).isoformat(),
            "$lte": datetime.combine(fin_periodo, datetime.max.time()).isoformat()
        }
    }
    
    citas = await db.citas.find(query).to_list(1000)
    return [CitaMedica(**parse_from_mongo(cita)) for cita in citas]

@api_router.put("/citas/{cita_id}/estado")
async def actualizar_estado_cita(cita_id: str, estado: EstadoCita, token: str = Depends(verify_token)):
    result = await db.citas.update_one(
        {"id": cita_id},
        {"$set": {"estado": estado}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"mensaje": "Estado de cita actualizado exitosamente"}

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
    await initialize_cie10_codes_expandido()
    logger.info("Aplicación iniciada con códigos CIE-10 expandidos y sistema inteligente")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()