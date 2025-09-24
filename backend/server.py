from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date, timezone
from enum import Enum
import re
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage

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

async def clasificar_cie10_inteligente_con_ai(diagnostico: str) -> Dict[str, Any]:
    """Clasificación inteligente con IA de diagnósticos según CIE-10"""
    if not diagnostico:
        return {"codigo": None, "confianza": "baja", "descripcion": None}
    
    try:
        # Usar IA para clasificación más precisa
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if emergent_key:
            chat = LlmChat(
                api_key=emergent_key,
                session_id=f"cie10-{datetime.now().timestamp()}",
                system_message="""Eres un experto en clasificación médica CIE-10. 
                Tu tarea es analizar diagnósticos médicos en español y devolver ÚNICAMENTE el código CIE-10 más apropiado.
                
                Responde SOLO con el formato: CODIGO|DESCRIPCION
                
                Ejemplos:
                - Para "Diarrea y gastroenteritis de presunto origen infeccioso" responde: A09.9|Diarrea y gastroenteritis de presunto origen infeccioso
                - Para "Fiebre" responde: R50.9|Fiebre, no especificada
                - Para "Otitis media aguda" responde: H66.9|Otitis media, no especificada
                
                Si no puedes determinar un código CIE-10 apropiado, responde: NONE|No clasificable"""
            ).with_model("openai", "gpt-4o")
            
            user_message = UserMessage(
                text=f"Clasifica este diagnóstico médico pediátrico según CIE-10: {diagnostico}"
            )
            
            try:
                response = await chat.send_message(user_message)
                
                if response and "|" in response:
                    parts = response.strip().split("|", 1)
                    if len(parts) == 2 and parts[0] != "NONE":
                        codigo = parts[0].strip()
                        descripcion = parts[1].strip()
                        
                        # Validar que el código tiene formato CIE-10 básico
                        if re.match(r'^[A-Z]\d{2}(\.\d)?$', codigo):
                            return {
                                "codigo": codigo,
                                "descripcion": descripcion,
                                "confianza": "alta",
                                "metodo": "ai"
                            }
                
            except Exception as ai_error:
                print(f"Error en clasificación con IA: {ai_error}")
                # Fall back to rule-based classification
                pass
    
    except Exception as e:
        print(f"Error configurando IA: {e}")
    
    # Fallback al método de reglas existente
    codigo_regla = clasificar_cie10_inteligente(diagnostico)
    if codigo_regla:
        return {
            "codigo": codigo_regla,
            "descripcion": None,
            "confianza": "media",
            "metodo": "reglas"
        }
    
    return {"codigo": None, "confianza": "baja", "descripcion": None, "metodo": "ninguno"}

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
    """💰 Sistema completo de cálculo de precios con margen garantizado del 25%"""
    
    # 1. Aplicar impuesto al costo unitario
    costo_con_impuesto = costo_unitario * (1 + impuesto / 100)
    
    # 2. Calcular costo real considerando escala de compra
    costo_real = costo_con_impuesto
    unidades_pagadas = 1
    unidades_recibidas = 1
    descripcion_escala = "Sin escala de compra"
    
    if escala_compra and escala_compra != "sin_escala" and '+' in escala_compra:
        try:
            partes = escala_compra.split('+')
            if len(partes) == 2:
                compra = float(partes[0])
                bonus = float(partes[1])
                recibe = compra + bonus
                
                # Costo real = (total pagado) / (total recibido)
                costo_real = (costo_con_impuesto * compra) / recibe
                unidades_pagadas = compra
                unidades_recibidas = recibe
                descripcion_escala = f"Compro {int(compra)} y recibo {int(recibe)} unidades"
        except Exception:
            # Si hay error en parsing, mantener sin escala
            pass
    
    # 3. Calcular precio base (mínimo sin descuento) con margen del 25%
    # Fórmula exacta solicitada: Precio Base = Costo Real / (1 - 0.25)
    precio_base = costo_real / (1 - 0.25)
    
    # 4. Calcular precio público manteniendo 25% después del descuento
    # Fórmula exacta solicitada: Precio Público = Costo Real / ((1 - 0.25)(1 - Descuento))
    if descuento > 0:
        precio_publico = costo_real / ((1 - 0.25) * (1 - descuento / 100))
    else:
        precio_publico = precio_base
    
    # 5. Verificar margen final después del descuento
    precio_final_cliente = precio_publico * (1 - descuento / 100)
    margen_final = ((precio_final_cliente - costo_real) / precio_final_cliente) * 100
    
    # 6. Cálculos adicionales para mostrar al usuario
    utilidad_por_unidad = precio_final_cliente - costo_real
    porcentaje_markup = ((precio_final_cliente - costo_real) / costo_real) * 100
    
    return {
        'costo_unitario_original': round(costo_unitario, 2),
        'impuesto_aplicado': impuesto,
        'costo_con_impuesto': round(costo_con_impuesto, 2),
        'escala_aplicada': escala_compra,
        'descripcion_escala': descripcion_escala,
        'unidades_pagadas': unidades_pagadas,
        'unidades_recibidas': unidades_recibidas,
        'costo_real': round(costo_real, 2),
        'precio_base': round(precio_base, 2),
        'precio_publico': round(precio_publico, 2),
        'descuento_aplicado': descuento,
        'precio_final_cliente': round(precio_final_cliente, 2),
        'margen_utilidad_final': round(margen_final, 2),
        'utilidad_por_unidad': round(utilidad_por_unidad, 2),
        'porcentaje_markup': round(porcentaje_markup, 2),
        'margen_garantizado': margen_final >= 24.5,  # Tolerancia del 0.5%
        'mensaje_verificacion': f"✅ Margen del {round(margen_final, 1)}% - {'GARANTIZADO' if margen_final >= 24.5 else 'INSUFICIENTE'}"
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
        
        # Alerta de vencimiento cercano (4 semanas = 28 días)
        if med.get('fecha_vencimiento'):
            try:
                if isinstance(med['fecha_vencimiento'], str):
                    fecha_venc = datetime.fromisoformat(med['fecha_vencimiento']).date()
                else:
                    fecha_venc = med['fecha_vencimiento']
                
                dias_hasta_vencimiento = (fecha_venc - date.today()).days
                
                if 0 <= dias_hasta_vencimiento <= 28:  # 4 semanas
                    if dias_hasta_vencimiento <= 7:
                        prioridad = 'alta'
                        mensaje = f"⚠️ URGENTE: Vence en {dias_hasta_vencimiento} días ({fecha_venc.strftime('%d/%m/%Y')})"
                    elif dias_hasta_vencimiento <= 14:
                        prioridad = 'alta'
                        mensaje = f"🚨 Vence en {dias_hasta_vencimiento} días ({fecha_venc.strftime('%d/%m/%Y')})"
                    else:
                        prioridad = 'media'
                        mensaje = f"⏰ Vence en {dias_hasta_vencimiento} días ({fecha_venc.strftime('%d/%m/%Y')})"
                    
                    alertas.append({
                        'tipo': AlertaTipo.VENCIMIENTO_CERCANO,
                        'medicamento_id': med.get('id'),
                        'medicamento_nombre': med.get('nombre'),
                        'mensaje': mensaje,
                        'prioridad': prioridad,
                        'fecha_alerta': datetime.now(timezone.utc),
                        'dias_restantes': dias_hasta_vencimiento
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

class VentaItem(BaseModel):
    medicamento_id: str
    medicamento_nombre: str
    cantidad: int
    precio_unitario: float
    costo_unitario: float
    descuento_aplicado: float = 0
    subtotal: float
    costo_total: float

class Venta(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    paciente_id: Optional[str] = None
    paciente_nombre: Optional[str] = None
    items: List[VentaItem]
    subtotal: float
    descuento_total: float = 0
    total_venta: float
    total_costo: float
    utilidad_bruta: float
    fecha_venta: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vendedor: str = "Sistema"
    notas: str = ""

class VentaCreate(BaseModel):
    paciente_id: Optional[str] = None
    items: List[Dict]  # Lista de {medicamento_id, cantidad, descuento_aplicado}
    descuento_total: float = 0
    vendedor: str = "Sistema"
    notas: str = ""

class VentaRapida(BaseModel):
    medicamento_id: str
    cliente_nombre: str
    precio_venta: float
    descuento_aplicado: float = 0
    cantidad: int = 1
    vendedor: str = "Farmacia"

class RestockDetection(BaseModel):
    nombre_producto: str
    nuevo_lote: str
    fecha_vencimiento: date
    stock_inicial: int
    costo_unitario: float
    impuesto: float = 0
    escala_compra: str = "sin_escala"

class BalanceDiario(BaseModel):
    fecha: date
    total_ventas: float
    total_costos: float
    utilidad_bruta: float
    numero_ventas: int
    productos_vendidos: int
    medicamentos_mas_vendidos: List[Dict]

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
        {"codigo": "F41.9", "descripcion": "Trastorno de ansiedad, no especificado", "categoria": "Trastornos mentales"},
        
        # Códigos CIE-10-ES 2024 actualizados según documento del usuario
        {"codigo": "A00", "descripcion": "Cólera", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A01.0", "descripcion": "Fiebre tifoidea", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A02.0", "descripcion": "Enteritis debida a Salmonella", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A04.9", "descripcion": "Otras infecciones intestinales bacterianas", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A08.4", "descripcion": "Gastroenteritis debida a virus (no especificada)", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A09", "descripcion": "Diarrea y gastroenteritis de presunto origen infeccioso", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "A17.81", "descripcion": "Tuberculosis del sistema nervioso con absceso cerebral o medular", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A33", "descripcion": "Tétanos neonatal", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A37", "descripcion": "Tos ferina", "categoria": "Enfermedades respiratorias"},
        {"codigo": "A38", "descripcion": "Escarlatina", "categoria": "Enfermedades infecciosas"},
        {"codigo": "A50", "descripcion": "Sífilis congénita", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B01", "descripcion": "Varicela", "categoria": "Enfermedades infecciosas"},
        {"codigo": "B08.4", "descripcion": "Enfermedad de boca, mano y pie", "categoria": "Enfermedades infecciosas"},
        {"codigo": "D64.9", "descripcion": "Anemia, no especificada", "categoria": "Enfermedades de la sangre"},
        {"codigo": "D61.01", "descripcion": "Anemia aplásica congénita", "categoria": "Enfermedades de la sangre"},
        {"codigo": "E66.811", "descripcion": "Obesidad clase 1", "categoria": "Trastornos nutricionales"},
        {"codigo": "E66.812", "descripcion": "Obesidad clase 2", "categoria": "Trastornos nutricionales"},
        {"codigo": "E66.813", "descripcion": "Obesidad clase 3", "categoria": "Trastornos nutricionales"},
        {"codigo": "E70.0", "descripcion": "Fenilcetonuria clásica", "categoria": "Trastornos metabólicos"},
        {"codigo": "E71.0", "descripcion": "Enfermedad del jarabe de arce (leucinosis)", "categoria": "Trastornos metabólicos"},
        {"codigo": "E72.2", "descripcion": "Trastornos del ciclo de la urea (no especificado)", "categoria": "Trastornos metabólicos"},
        {"codigo": "E75.2", "descripcion": "Enfermedad de Gaucher y Niemann-Pick", "categoria": "Trastornos metabólicos"},
        {"codigo": "E83.0", "descripcion": "Enfermedad de Wilson", "categoria": "Trastornos metabólicos"},
        {"codigo": "E88.0", "descripcion": "Trimetilaminuria", "categoria": "Trastornos metabólicos"},
        {"codigo": "F41.0", "descripcion": "Trastorno de pánico", "categoria": "Trastornos mentales"},
        {"codigo": "F42", "descripcion": "Trastorno obsesivo-compulsivo", "categoria": "Trastornos mentales"},
        {"codigo": "F50.0", "descripcion": "Anorexia nerviosa", "categoria": "Trastornos mentales"},
        {"codigo": "F50.2", "descripcion": "Bulimia nerviosa", "categoria": "Trastornos mentales"},
        {"codigo": "F64.2", "descripcion": "Trastorno de identidad de género en niños", "categoria": "Trastornos mentales"},
        {"codigo": "F80.3", "descripcion": "Síndrome de Landau-Kleffner o afasia epiléptica adquirida", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F81.0", "descripcion": "Trastorno específico de la lectura (dislexia)", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F81.2", "descripcion": "Trastornos específicos de las habilidades aritméticas (acalculia)", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F84.2", "descripcion": "Síndrome de Rett", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F84.5", "descripcion": "Síndrome de Asperger", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F90.0", "descripcion": "Trastorno por déficit de atención con hiperactividad, tipo desatento", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F90.1", "descripcion": "Trastorno por déficit de atención con hiperactividad, tipo hiperactivo-impulsivo", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F90.2", "descripcion": "Trastorno por déficit de atención con hiperactividad (TDAH), tipo combinado", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F91.0", "descripcion": "Trastorno de conducta limitado al contexto familiar", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F91.3", "descripcion": "Trastorno negativista desafiante", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F93.0", "descripcion": "Trastorno de ansiedad por separación en la infancia", "categoria": "Trastornos mentales"},
        {"codigo": "F93.8", "descripcion": "Trastorno de ansiedad y miedo de la infancia NCOC", "categoria": "Trastornos mentales"},
        {"codigo": "F94.0", "descripcion": "Mutismo selectivo", "categoria": "Trastornos del desarrollo"},
        {"codigo": "F95.0", "descripcion": "Trastorno de tics transitorio", "categoria": "Trastornos del desarrollo"},
        {"codigo": "G71.0", "descripcion": "Distrofia muscular (Duchenne, Becker)", "categoria": "Enfermedades neurológicas"},
        {"codigo": "G71.3", "descripcion": "Miopatía mitocondrial", "categoria": "Enfermedades neurológicas"},
        {"codigo": "H10.9", "descripcion": "Conjuntivitis, no especificada", "categoria": "Enfermedades del ojo"},
        {"codigo": "H66.012", "descripcion": "Otitis media supurativa aguda con rotura espontánea de tímpano", "categoria": "Enfermedades del oído"},
        {"codigo": "J05.0", "descripcion": "Crup", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J21.0", "descripcion": "Bronquiolitis aguda, debida a virus sincitial respiratorio (VSR)", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J21.9", "descripcion": "Bronquiolitis aguda, no especificada", "categoria": "Enfermedades respiratorias"},
        {"codigo": "J38.5", "descripcion": "Laringismo estriduloso (crup espasmódico)", "categoria": "Enfermedades respiratorias"},
        {"codigo": "K90.0", "descripcion": "Enfermedad celíaca", "categoria": "Enfermedades gastrointestinales"},
        {"codigo": "P05.0", "descripcion": "Pequeño para la edad gestacional (PEG) asimétrico", "categoria": "Afecciones perinatales"},
        {"codigo": "P22.0", "descripcion": "Síndrome de dificultad respiratoria del recién nacido", "categoria": "Afecciones perinatales"},
        {"codigo": "P80.0", "descripcion": "Hipotermia severa del recién nacido", "categoria": "Afecciones perinatales"},
        {"codigo": "P96.1", "descripcion": "Síndrome de deprivación por drogas ilícitas", "categoria": "Afecciones perinatales"},
        {"codigo": "Q00.0", "descripcion": "Anencefalia", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q24.0", "descripcion": "Dextrocardia", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q65.0", "descripcion": "Luxación congénita de la cadera, unilateral", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q66.0", "descripcion": "Pie equinovaro", "categoria": "Malformaciones congénitas"},
        {"codigo": "Q90.0", "descripcion": "Síndrome de Down, cariotipo regular", "categoria": "Alteraciones cromosómicas"},
        {"codigo": "Z05.0", "descripcion": "Observación por sospecha de afección cardiaca en recién nacido", "categoria": "Factores que influyen en el estado de salud"},
        {"codigo": "Z38.00", "descripcion": "Recién nacido vivo único, parto vaginal", "categoria": "Factores que influyen en el estado de salud"},
        {"codigo": "Z68.54", "descripcion": "IMC pediátrico en percentil 95 o superior para obesidad clase 1", "categoria": "Factores que influyen en el estado de salud"}
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
    """🧠 Clasificación inteligente con IA de diagnósticos según CIE-10"""
    
    # Usar nueva clasificación con IA
    resultado_ai = await clasificar_cie10_inteligente_con_ai(diagnostico)
    
    if resultado_ai["codigo"]:
        # Buscar información completa en la base de datos
        cie10_code = await db.cie10_codes.find_one({"codigo": resultado_ai["codigo"]})
        
        descripcion_final = resultado_ai.get("descripcion", "")
        if cie10_code and not descripcion_final:
            descripcion_final = cie10_code["descripcion"]
        
        return {
            "codigo": resultado_ai["codigo"],
            "descripcion": descripcion_final,
            "capitulo": obtener_capitulo_cie10(resultado_ai["codigo"]),
            "sugerencia": True,
            "confianza": resultado_ai["confianza"],
            "metodo": resultado_ai.get("metodo", "ai"),
            "mensaje": f"✅ Clasificación automática {'con IA' if resultado_ai.get('metodo') == 'ai' else 'por reglas'}"
        }
    
    # Si no encuentra con IA, buscar similares en base de datos
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
                    "metodo": "busqueda_similar",
                    "alternativas": [{"codigo": c["codigo"], "descripcion": c["descripcion"]} for c in codes[1:4]],
                    "mensaje": "📚 Encontrado por búsqueda similar en base de datos"
                }
    
    return {
        "codigo": None,
        "descripcion": None,
        "capitulo": None,
        "sugerencia": False,
        "confianza": "baja",
        "metodo": "ninguno",
        "mensaje": "❌ No se encontró clasificación automática. Busque manualmente en la base CIE-10."
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
    impuesto: float = 0,
    escala_compra: str = "sin_escala",
    descuento: float = 0,
    token: str = Depends(verify_token)
):
    """💰 Calculadora detallada de precios con margen garantizado del 25%"""
    
    # Validar entradas
    if costo_unitario <= 0:
        raise HTTPException(status_code=400, detail="El costo unitario debe ser mayor a 0")
    
    if descuento < 0 or descuento > 100:
        raise HTTPException(status_code=400, detail="El descuento debe estar entre 0 y 100%")
    
    if impuesto < 0 or impuesto > 100:
        raise HTTPException(status_code=400, detail="El impuesto debe estar entre 0 y 100%")
    
    resultado = calcular_precios_farmacia_detallado(costo_unitario, impuesto, escala_compra, descuento)
    
    return {
        **resultado,
        "mensaje": "✅ Cálculo completado con margen garantizado del 25%",
        "formulas_aplicadas": {
            "costo_real": "Costo unitario × (1 + impuesto/100) ÷ unidades_recibidas_con_escala",
            "precio_base": "Costo real ÷ (1 - 0.25)",
            "precio_publico": "Costo real ÷ ((1 - 0.25) × (1 - descuento/100))"
        }
    }

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

@api_router.put("/medicamentos/{medicamento_id}", response_model=Medicamento)
async def actualizar_medicamento(medicamento_id: str, medicamento: MedicamentoCreate, token: str = Depends(verify_token)):
    """✏️ Actualizar información de un medicamento existente"""
    
    # Verificar que el medicamento existe
    existing = await db.medicamentos.find_one({"id": medicamento_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    
    # Calcular precios actualizados
    precios = calcular_precios_farmacia_detallado(
        medicamento.costo_unitario,
        medicamento.impuesto,
        medicamento.escala_compra,
        medicamento.descuento_aplicable
    )
    
    medicamento_actualizado = Medicamento(
        id=medicamento_id,
        **medicamento.dict(),
        costo_real=precios['costo_real'],
        precio_base=precios['precio_base'],
        precio_publico=precios['precio_publico'],
        margen_utilidad=precios['margen_utilidad_final']
    )
    
    # Actualizar en base de datos
    await db.medicamentos.update_one(
        {"id": medicamento_id},
        {"$set": prepare_for_mongo(medicamento_actualizado.dict())}
    )
    
    return medicamento_actualizado

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

# NEW: Sales Management Endpoints
@api_router.post("/ventas", response_model=Venta)
async def crear_venta(venta_data: VentaCreate, token: str = Depends(verify_token)):
    """💰 Crear nueva venta con cálculo automático de costos y utilidades"""
    
    if not venta_data.items:
        raise HTTPException(status_code=400, detail="La venta debe incluir al menos un producto")
    
    # Obtener información de medicamentos
    medicamento_ids = [item["medicamento_id"] for item in venta_data.items]
    medicamentos = await db.medicamentos.find({"id": {"$in": medicamento_ids}}).to_list(100)
    medicamentos_map = {med["id"]: med for med in medicamentos}
    
    # Calcular items de venta
    items_venta = []
    subtotal = 0
    total_costo = 0
    
    for item_data in venta_data.items:
        med_id = item_data["medicamento_id"]
        cantidad = item_data["cantidad"]
        descuento_item = item_data.get("descuento_aplicado", 0)
        
        if med_id not in medicamentos_map:
            raise HTTPException(status_code=404, detail=f"Medicamento {med_id} no encontrado")
        
        medicamento = medicamentos_map[med_id]
        
        # Verificar stock suficiente
        if medicamento["stock"] < cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para {medicamento['nombre']}")
        
        # Calcular precios
        precio_unitario = medicamento["precio_publico"]
        costo_unitario = medicamento["costo_real"]
        
        precio_con_descuento = precio_unitario * (1 - descuento_item / 100)
        subtotal_item = precio_con_descuento * cantidad
        costo_total_item = costo_unitario * cantidad
        
        items_venta.append(VentaItem(
            medicamento_id=med_id,
            medicamento_nombre=medicamento["nombre"],
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            costo_unitario=costo_unitario,
            descuento_aplicado=descuento_item,
            subtotal=subtotal_item,
            costo_total=costo_total_item
        ))
        
        subtotal += subtotal_item
        total_costo += costo_total_item
        
        # Actualizar stock
        await db.medicamentos.update_one(
            {"id": med_id},
            {"$inc": {"stock": -cantidad, "ventas_mes": cantidad}}
        )
    
    # Calcular totales de venta
    descuento_total = venta_data.descuento_total
    total_venta = subtotal * (1 - descuento_total / 100)
    utilidad_bruta = total_venta - total_costo
    
    # Obtener nombre del paciente si se especifica
    paciente_nombre = None
    if venta_data.paciente_id:
        paciente = await db.pacientes.find_one({"id": venta_data.paciente_id})
        if paciente:
            paciente_nombre = paciente["nombre_completo"]
    
    # Crear venta
    venta = Venta(
        paciente_id=venta_data.paciente_id,
        paciente_nombre=paciente_nombre,
        items=items_venta,
        subtotal=subtotal,
        descuento_total=descuento_total,
        total_venta=total_venta,
        total_costo=total_costo,
        utilidad_bruta=utilidad_bruta,
        vendedor=venta_data.vendedor,
        notas=venta_data.notas
    )
    
    await db.ventas.insert_one(prepare_for_mongo(venta.dict()))
    return venta

@api_router.get("/ventas/balance-diario")
async def get_balance_diario(fecha: Optional[date] = None, token: str = Depends(verify_token)):
    """📊 Obtener balance diario de ventas"""
    
    if not fecha:
        fecha = date.today()
    
    # Obtener ventas del día
    inicio_dia = datetime.combine(fecha, datetime.min.time()).isoformat()
    fin_dia = datetime.combine(fecha, datetime.max.time()).isoformat()
    
    ventas_dia = await db.ventas.find({
        "fecha_venta": {
            "$gte": inicio_dia,
            "$lte": fin_dia
        }
    }).to_list(1000)
    
    # Calcular totales
    total_ventas = sum(venta.get("total_venta", 0) for venta in ventas_dia)
    total_costos = sum(venta.get("total_costo", 0) for venta in ventas_dia)
    utilidad_bruta = total_ventas - total_costos
    numero_ventas = len(ventas_dia)
    
    # Contar productos vendidos
    productos_vendidos = 0
    medicamentos_vendidos = {}
    
    for venta in ventas_dia:
        for item in venta.get("items", []):
            productos_vendidos += item.get("cantidad", 0)
            med_nombre = item.get("medicamento_nombre", "Desconocido")
            if med_nombre in medicamentos_vendidos:
                medicamentos_vendidos[med_nombre] += item.get("cantidad", 0)
            else:
                medicamentos_vendidos[med_nombre] = item.get("cantidad", 0)
    
    # Top 5 medicamentos más vendidos
    medicamentos_mas_vendidos = [
        {"nombre": nombre, "cantidad": cantidad}
        for nombre, cantidad in sorted(medicamentos_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return BalanceDiario(
        fecha=fecha,
        total_ventas=total_ventas,
        total_costos=total_costos,
        utilidad_bruta=utilidad_bruta,
        numero_ventas=numero_ventas,
        productos_vendidos=productos_vendidos,
        medicamentos_mas_vendidos=medicamentos_mas_vendidos
    )

@api_router.get("/ventas/hoy")
async def get_ventas_hoy(token: str = Depends(verify_token)):
    """🕐 Obtener resumen de ventas de hoy"""
    balance = await get_balance_diario(date.today(), token)
    
    return {
        "productos_vendidos_hoy": balance.productos_vendidos,
        "numero_ventas": balance.numero_ventas,
        "total_ingresos": balance.total_ventas,
        "utilidad": balance.utilidad_bruta,
        "top_productos": balance.medicamentos_mas_vendidos[:3]
    }

@api_router.post("/ventas/venta-rapida")
async def crear_venta_rapida(venta: VentaRapida, token: str = Depends(verify_token)):
    """⚡ Crear venta rápida desde farmacia"""
    
    # Obtener información del medicamento
    medicamento = await db.medicamentos.find_one({"id": venta.medicamento_id})
    if not medicamento:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    
    # Verificar stock suficiente
    if medicamento["stock"] < venta.cantidad:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {medicamento['stock']}")
    
    # Calcular totales
    subtotal = venta.precio_venta * venta.cantidad
    descuento_total = subtotal * (venta.descuento_aplicado / 100)
    total_venta = subtotal - descuento_total
    costo_total = medicamento["costo_real"] * venta.cantidad
    utilidad = total_venta - costo_total
    
    # Crear item de venta
    item_venta = VentaItem(
        medicamento_id=venta.medicamento_id,
        medicamento_nombre=medicamento["nombre"],
        cantidad=venta.cantidad,
        precio_unitario=venta.precio_venta,
        costo_unitario=medicamento["costo_real"],
        descuento_aplicado=venta.descuento_aplicado,
        subtotal=subtotal,
        costo_total=costo_total
    )
    
    # Crear venta completa
    nueva_venta = Venta(
        paciente_nombre=venta.cliente_nombre,
        items=[item_venta],
        subtotal=subtotal,
        descuento_total=venta.descuento_aplicado,
        total_venta=total_venta,
        total_costo=costo_total,
        utilidad_bruta=utilidad,
        vendedor=venta.vendedor,
        notas=f"Venta rápida - Cliente: {venta.cliente_nombre}"
    )
    
    # Guardar venta
    await db.ventas.insert_one(prepare_for_mongo(nueva_venta.dict()))
    
    # Actualizar stock
    new_stock = medicamento["stock"] - venta.cantidad
    await db.medicamentos.update_one(
        {"id": venta.medicamento_id},
        {
            "$inc": {"stock": -venta.cantidad, "ventas_mes": venta.cantidad},
            "$set": {"ultima_venta": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Verificar si el stock llegó a 0 para notificar
    if new_stock == 0:
        # Crear alerta de stock agotado
        alerta = {
            "tipo": "STOCK_AGOTADO",
            "medicamento_id": venta.medicamento_id,
            "medicamento_nombre": medicamento["nombre"],
            "mensaje": f"🚨 STOCK AGOTADO: {medicamento['nombre']} - Se necesita restock urgente",
            "prioridad": "alta",
            "fecha_alerta": datetime.now(timezone.utc),
            "leida": False
        }
        await db.alertas_farmacia.insert_one(prepare_for_mongo(alerta))
    
    return {
        "success": True,
        "venta_id": nueva_venta.id,
        "total": total_venta,
        "utilidad": utilidad,
        "stock_restante": new_stock,
        "mensaje": f"✅ Venta rápida registrada: {medicamento['nombre']} - {venta.cliente_nombre}"
    }

@api_router.post("/medicamentos/detectar-restock")
async def detectar_restock_inteligente(restock_data: RestockDetection, token: str = Depends(verify_token)):
    """🧠 Detectar restock inteligente con IA"""
    
    try:
        # Buscar productos similares en la base de datos
        productos_similares = await db.medicamentos.find({
            "nombre": {"$regex": restock_data.nombre_producto, "$options": "i"}
        }).to_list(10)
        
        if productos_similares:
            # Usar IA para determinar si es el mismo producto
            emergent_key = os.environ.get('EMERGENT_LLM_KEY')
            if emergent_key:
                chat = LlmChat(
                    api_key=emergent_key,
                    session_id=f"restock-{datetime.now().timestamp()}",
                    system_message="""Eres un experto en farmacia. Tu tarea es determinar si un producto nuevo es un restock (reabastecimiento) de un producto existente.

Responde ÚNICAMENTE con el formato: RESTOCK|ID_PRODUCTO|CONFIANZA
- RESTOCK: SI o NO
- ID_PRODUCTO: el ID del producto existente si es restock
- CONFIANZA: ALTA, MEDIA, BAJA

Ejemplos:
- Para "Acetaminofén 500mg" vs productos existentes ["Acetaminofén 500mg", "Ibuprofeno"] responde: SI|id123|ALTA
- Para "Vitamina C 1000mg" vs productos existentes ["Acetaminofén 500mg"] responde: NO||BAJA"""
                ).with_model("openai", "gpt-4o")
                
                productos_texto = ", ".join([f"{p['nombre']} (ID: {p['id']})" for p in productos_similares[:5]])
                
                user_message = UserMessage(
                    text=f"¿El producto '{restock_data.nombre_producto}' es un restock de alguno de estos productos existentes?: {productos_texto}"
                )
                
                try:
                    response = await chat.send_message(user_message)
                    
                    if response and "|" in response:
                        parts = response.strip().split("|")
                        if len(parts) >= 3 and parts[0] == "SI":
                            # Es un restock - obtener datos del producto existente
                            producto_id = parts[1]
                            confianza = parts[2]
                            
                            producto_existente = await db.medicamentos.find_one({"id": producto_id})
                            if producto_existente:
                                return {
                                    "es_restock": True,
                                    "producto_existente": producto_existente,
                                    "confianza": confianza.lower(),
                                    "sugerencia": {
                                        "mantener": {
                                            "nombre": producto_existente["nombre"],
                                            "categoria": producto_existente["categoria"],
                                            "descripcion": producto_existente["descripcion"],
                                            "dosis_pediatrica": producto_existente.get("dosis_pediatrica", ""),
                                            "stock_minimo": producto_existente["stock_minimo"]
                                        },
                                        "actualizar": {
                                            "lote": restock_data.nuevo_lote,
                                            "fecha_vencimiento": restock_data.fecha_vencimiento.isoformat(),
                                            "stock": restock_data.stock_inicial,
                                            "costo_unitario": restock_data.costo_unitario,
                                            "impuesto": restock_data.impuesto,
                                            "escala_compra": restock_data.escala_compra
                                        }
                                    },
                                    "mensaje": f"🔄 Restock detectado con {confianza.lower()} confianza. Datos del producto existente pre-cargados."
                                }
                
                except Exception as ai_error:
                    print(f"Error en AI restock detection: {ai_error}")
        
        # No es restock - producto completamente nuevo
        return {
            "es_restock": False,
            "producto_existente": None,
            "confianza": "alta",
            "sugerencia": {
                "crear_nuevo": True,
                "datos": {
                    "nombre": restock_data.nombre_producto,
                    "lote": restock_data.nuevo_lote,
                    "fecha_vencimiento": restock_data.fecha_vencimiento.isoformat(),
                    "stock": restock_data.stock_inicial,
                    "costo_unitario": restock_data.costo_unitario,
                    "impuesto": restock_data.impuesto,
                    "escala_compra": restock_data.escala_compra
                }
            },
            "mensaje": "✨ Producto nuevo detectado. Proceda a crear como nuevo producto."
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en detección de restock: {str(e)}")

@api_router.put("/medicamentos/{medicamento_id}/restock")
async def aplicar_restock(medicamento_id: str, restock_data: RestockDetection, token: str = Depends(verify_token)):
    """🔄 Aplicar restock a producto existente"""
    
    # Verificar que el medicamento existe
    existing = await db.medicamentos.find_one({"id": medicamento_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    
    # Calcular nuevos precios
    precios = calcular_precios_farmacia_detallado(
        restock_data.costo_unitario,
        restock_data.impuesto,
        restock_data.escala_compra,
        existing.get("descuento_maximo", 0)
    )
    
    # Actualizar solo los campos de restock
    await db.medicamentos.update_one(
        {"id": medicamento_id},
        {"$set": {
            "lote": restock_data.nuevo_lote,
            "fecha_vencimiento": restock_data.fecha_vencimiento.isoformat(),
            "stock": existing["stock"] + restock_data.stock_inicial,  # Sumar al stock existente
            "costo_unitario": restock_data.costo_unitario,
            "impuesto": restock_data.impuesto,
            "escala_compra": restock_data.escala_compra,
            "costo_real": precios['costo_real'],
            "precio_base": precios['precio_base'],
            "precio_publico": precios['precio_publico'],
            "margen_utilidad": precios['margen_utilidad_final'],
            "fecha_actualizacion": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Eliminar alertas de stock agotado para este producto
    await db.alertas_farmacia.delete_many({
        "medicamento_id": medicamento_id,
        "tipo": "STOCK_AGOTADO"
    })
    
    return {
        "success": True,
        "mensaje": f"✅ Restock aplicado exitosamente a {existing['nombre']}",
        "nuevo_stock": existing["stock"] + restock_data.stock_inicial,
        "nuevos_precios": precios
    }

# REPORTES AVANZADOS DE VENTAS
@api_router.get("/reportes/ventas-mensual")
async def get_reporte_ventas_mensual(mes: int, ano: int, token: str = Depends(verify_token)):
    """📊 Reporte completo de ventas mensuales para exportar a Excel"""
    
    from datetime import datetime, timedelta
    
    # Calcular rango de fechas del mes
    primer_dia = datetime(ano, mes, 1)
    if mes == 12:
        ultimo_dia = datetime(ano + 1, 1, 1) - timedelta(seconds=1)
    else:
        ultimo_dia = datetime(ano, mes + 1, 1) - timedelta(seconds=1)
    
    # Obtener todas las ventas del mes
    ventas_mes = await db.ventas.find({
        "fecha_venta": {
            "$gte": primer_dia.isoformat(),
            "$lte": ultimo_dia.isoformat()
        }
    }).to_list(10000)
    
    # Análisis por productos
    productos_analysis = {}
    clientes_analysis = {}
    
    total_ventas = 0
    total_costos = 0
    
    for venta in ventas_mes:
        total_ventas += venta.get("total_venta", 0)
        total_costos += venta.get("total_costo", 0)
        
        cliente = venta.get("paciente_nombre", "Cliente Anónimo")
        if cliente not in clientes_analysis:
            clientes_analysis[cliente] = {
                "nombre": cliente,
                "numero_compras": 0,
                "total_gastado": 0,
                "productos_comprados": 0
            }
        
        clientes_analysis[cliente]["numero_compras"] += 1
        clientes_analysis[cliente]["total_gastado"] += venta.get("total_venta", 0)
        
        for item in venta.get("items", []):
            med_id = item.get("medicamento_id")
            med_nombre = item.get("medicamento_nombre", "Desconocido")
            cantidad = item.get("cantidad", 0)
            subtotal = item.get("subtotal", 0)
            costo_total = item.get("costo_total", 0)
            utilidad = subtotal - costo_total
            
            if med_id not in productos_analysis:
                productos_analysis[med_id] = {
                    "nombre": med_nombre,
                    "cantidad_vendida": 0,
                    "ingresos_generados": 0,
                    "costos_totales": 0,
                    "utilidad_generada": 0,
                    "numero_ventas": 0
                }
            
            productos_analysis[med_id]["cantidad_vendida"] += cantidad
            productos_analysis[med_id]["ingresos_generados"] += subtotal
            productos_analysis[med_id]["costos_totales"] += costo_total
            productos_analysis[med_id]["utilidad_generada"] += utilidad
            productos_analysis[med_id]["numero_ventas"] += 1
            
            clientes_analysis[cliente]["productos_comprados"] += cantidad
    
    # Obtener todos los productos para identificar no vendidos
    todos_productos = await db.medicamentos.find({}).to_list(1000)
    productos_no_vendidos = []
    
    for producto in todos_productos:
        if producto["id"] not in productos_analysis:
            productos_no_vendidos.append({
                "id": producto["id"],
                "nombre": producto["nombre"],
                "categoria": producto["categoria"],
                "stock_actual": producto["stock"],
                "precio_publico": producto.get("precio_publico", 0)
            })
    
    # Rankings
    productos_vendidos = list(productos_analysis.values())
    productos_mas_vendidos = sorted(productos_vendidos, key=lambda x: x["cantidad_vendida"], reverse=True)[:10]
    productos_menos_vendidos = sorted(productos_vendidos, key=lambda x: x["cantidad_vendida"])[:10]
    productos_mas_rentables = sorted(productos_vendidos, key=lambda x: x["utilidad_generada"], reverse=True)[:10]
    productos_menos_rentables = sorted(productos_vendidos, key=lambda x: x["utilidad_generada"])[:10]
    
    clientes_list = list(clientes_analysis.values())
    mejores_clientes_frecuencia = sorted(clientes_list, key=lambda x: x["numero_compras"], reverse=True)[:10]
    mejores_clientes_cantidad = sorted(clientes_list, key=lambda x: x["total_gastado"], reverse=True)[:10]
    
    utilidad_total = total_ventas - total_costos
    
    return {
        "periodo": f"{mes:02d}/{ano}",
        "resumen": {
            "total_ventas": total_ventas,
            "total_costos": total_costos,
            "utilidad_bruta": utilidad_total,
            "margen_promedio": (utilidad_total / total_ventas * 100) if total_ventas > 0 else 0,
            "numero_transacciones": len(ventas_mes),
            "productos_diferentes_vendidos": len(productos_analysis),
            "productos_no_vendidos": len(productos_no_vendidos)
        },
        "productos_mas_vendidos": productos_mas_vendidos,
        "productos_menos_vendidos": productos_menos_vendidos,
        "productos_mas_rentables": productos_mas_rentables,
        "productos_menos_rentables": productos_menos_rentables,
        "productos_no_vendidos": productos_no_vendidos,
        "mejores_clientes_frecuencia": mejores_clientes_frecuencia,
        "mejores_clientes_monto": mejores_clientes_cantidad,
        "datos_completos": {
            "productos": productos_vendidos,
            "clientes": clientes_list,
            "ventas_detalle": ventas_mes
        }
    }

@api_router.get("/reportes/recomendaciones-ia")
async def get_recomendaciones_financieras_ia(mes: int, ano: int, token: str = Depends(verify_token)):
    """🧠 Recomendaciones financieras mensuales con IA"""
    
    try:
        # Obtener datos del reporte mensual
        reporte = await get_reporte_ventas_mensual(mes, ano, token)
        
        # Usar IA para generar recomendaciones
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if emergent_key:
            chat = LlmChat(
                api_key=emergent_key,
                session_id=f"financial-advice-{mes}-{ano}-{datetime.now().timestamp()}",
                system_message="""Eres un consultor financiero especializado en farmacias pediátricas. 
                
Analiza los datos de ventas mensuales y proporciona recomendaciones específicas en español siguiendo esta estructura:

FORMATO DE RESPUESTA:
```json
{
  "recomendaciones_inventario": [
    {"accion": "COMPRAR_MAS", "producto": "nombre", "razon": "justificación"},
    {"accion": "REDUCIR_STOCK", "producto": "nombre", "razon": "justificación"}
  ],
  "recomendaciones_precios": [
    {"accion": "AJUSTAR_PRECIO", "producto": "nombre", "sugerencia": "específica"}
  ],
  "alertas_financieras": ["alerta 1", "alerta 2"],
  "oportunidades_mejora": ["oportunidad 1", "oportunidad 2"],
  "resumen_ejecutivo": "resumen en 2-3 oraciones"
}
```

Considera:
- Productos con alta demanda vs stock
- Productos no vendidos que ocupan capital
- Margen de utilidad por producto
- Frecuencia de compra de clientes
- Estacionalidad pediátrica"""
            ).with_model("openai", "gpt-4o")
            
            datos_resumen = {
                "resumen_financiero": reporte["resumen"],
                "top_5_vendidos": reporte["productos_mas_vendidos"][:5],
                "top_5_rentables": reporte["productos_mas_rentables"][:5],
                "productos_no_vendidos": len(reporte["productos_no_vendidos"]),
                "mejor_cliente": reporte["mejores_clientes_monto"][0] if reporte["mejores_clientes_monto"] else None
            }
            
            user_message = UserMessage(
                text=f"Analiza estos datos de farmacia pediátrica del {mes}/{ano} y proporciona recomendaciones financieras: {json.dumps(datos_resumen, default=str)}"
            )
            
            try:
                response = await chat.send_message(user_message)
                
                # Intentar parsear JSON de la respuesta
                import json
                if "```json" in response:
                    json_part = response.split("```json")[1].split("```")[0]
                    recomendaciones = json.loads(json_part)
                else:
                    # Crear estructura básica si falla el parsing
                    recomendaciones = {
                        "recomendaciones_inventario": [],
                        "recomendaciones_precios": [],
                        "alertas_financieras": [],
                        "oportunidades_mejora": [],
                        "resumen_ejecutivo": response[:200] + "..." if len(response) > 200 else response
                    }
                
                return {
                    "periodo": f"{mes:02d}/{ano}",
                    "fecha_generacion": datetime.now().isoformat(),
                    "recomendaciones": recomendaciones,
                    "datos_base": datos_resumen,
                    "metodo": "ia_gpt4"
                }
                
            except Exception as ai_error:
                print(f"Error en IA recommendations: {ai_error}")
                # Fallback a recomendaciones básicas
                pass
    
    except Exception as e:
        print(f"Error en recomendaciones: {e}")
    
    # Recomendaciones básicas si falla la IA
    return {
        "periodo": f"{mes:02d}/{ano}",
        "fecha_generacion": datetime.now().isoformat(),
        "recomendaciones": {
            "recomendaciones_inventario": [
                {"accion": "REVISAR_MANUALMENTE", "producto": "Todos", "razon": "Sistema de IA no disponible temporalmente"}
            ],
            "alertas_financieras": ["Revisar manualmente los datos de ventas"],
            "resumen_ejecutivo": "Recomendaciones básicas generadas. Revisar datos manualmente."
        },
        "metodo": "fallback_basico"
    }

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