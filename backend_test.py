#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Pediatric Clinic Management System
Tests all endpoints with proper authentication and data validation
"""

import requests
import sys
import json
from datetime import datetime, date
from typing import Dict, Any

class PediatricClinicAPITester:
    def __init__(self, base_url="https://pedimed-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None, expected_status: int = 200) -> tuple[bool, Dict[Any, Any]]:
        """Make HTTP request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_authentication(self):
        """Test login functionality"""
        print("\n🔐 Testing Authentication...")
        
        # Test invalid code
        success, response = self.make_request(
            'POST', 'login', 
            {"codigo": "wrong_code"}, 
            expected_status=401
        )
        self.log_test("Login with invalid code (should fail)", success, 
                     "Should return 401" if success else f"Got: {response}")

        # Test valid code
        success, response = self.make_request(
            'POST', 'login', 
            {"codigo": "1970"}, 
            expected_status=200
        )
        
        if success and response.get('success') and response.get('token'):
            self.token = response['token']
            self.log_test("Login with valid code 1970", True)
            self.log_test("Token received", response.get('token') == 'valid_token_1970')
            self.log_test("Role is doctor", response.get('role') == 'doctor')
        else:
            self.log_test("Login with valid code 1970", False, f"Response: {response}")
            return False
        
        return True

    def test_cie10_endpoints(self):
        """Test CIE-10 code endpoints"""
        print("\n📋 Testing CIE-10 Endpoints...")
        
        # Get all CIE-10 codes
        success, response = self.make_request('GET', 'cie10')
        if success and isinstance(response, list) and len(response) > 0:
            self.log_test("Get all CIE-10 codes", True, f"Found {len(response)} codes")
            
            # Test search functionality
            success, search_response = self.make_request('GET', 'cie10/search?query=J00')
            if success and isinstance(search_response, list):
                self.log_test("Search CIE-10 codes", True, f"Found {len(search_response)} results for 'J00'")
            else:
                self.log_test("Search CIE-10 codes", False, f"Response: {search_response}")
        else:
            self.log_test("Get all CIE-10 codes", False, f"Response: {response}")

    def test_patient_crud_operations(self):
        """Test patient CRUD operations"""
        print("\n👶 Testing Patient Management...")
        
        # Create test patient
        patient_data = {
            "nombre_completo": "Juan Pérez López",
            "fecha_nacimiento": "2018-05-15",
            "nombre_padre": "Carlos Pérez",
            "nombre_madre": "María López",
            "direccion": "Colonia Kennedy, Tegucigalpa",
            "numero_celular": "9876-5432",
            "sintomas_signos": "Fiebre y tos",
            "diagnostico_clinico": "Infección respiratoria",
            "codigo_cie10": "J00",
            "gravedad_diagnostico": "leve",
            "peso": 25.5,
            "altura": 1.10,
            "contacto_recordatorios": "9876-5432"
        }
        
        success, response = self.make_request('POST', 'pacientes', patient_data, expected_status=200)
        
        if success and response.get('id'):
            patient_id = response['id']
            self.log_test("Create patient", True, f"Patient ID: {patient_id}")
            
            # Verify automatic calculations
            if response.get('edad') and response.get('imc'):
                expected_age = datetime.now().year - 2018
                self.log_test("Automatic age calculation", 
                            abs(response['edad'] - expected_age) <= 1,
                            f"Age: {response['edad']}, Expected: ~{expected_age}")
                
                self.log_test("Automatic BMI calculation", 
                            response.get('imc') is not None,
                            f"BMI: {response.get('imc')}")
                
                self.log_test("Nutritional status calculation", 
                            response.get('estado_nutricional') is not None,
                            f"Status: {response.get('estado_nutricional')}")
            
            # Test get all patients
            success, patients = self.make_request('GET', 'pacientes')
            if success and isinstance(patients, list):
                self.log_test("Get all patients", True, f"Found {len(patients)} patients")
            else:
                self.log_test("Get all patients", False, f"Response: {patients}")
            
            # Test get specific patient
            success, patient = self.make_request('GET', f'pacientes/{patient_id}')
            if success and patient.get('id') == patient_id:
                self.log_test("Get specific patient", True)
            else:
                self.log_test("Get specific patient", False, f"Response: {patient}")
            
            # Test update patient
            update_data = {
                "peso": 26.0,
                "altura": 1.12
            }
            success, updated_patient = self.make_request('PUT', f'pacientes/{patient_id}', update_data)
            if success and updated_patient.get('peso') == 26.0:
                self.log_test("Update patient", True)
                
                # Verify BMI recalculation
                if updated_patient.get('imc') != response.get('imc'):
                    self.log_test("BMI recalculation on update", True)
                else:
                    self.log_test("BMI recalculation on update", False, "BMI should have changed")
            else:
                self.log_test("Update patient", False, f"Response: {updated_patient}")
            
            # Test add medical appointment
            cita_data = {
                "fecha_cita": "2024-01-15",
                "motivo": "Control rutinario",
                "tratamiento": "Vitaminas",
                "cobro": 500.0,
                "doctor_atencion": "Dr. García"
            }
            success, cita_response = self.make_request('POST', f'pacientes/{patient_id}/citas', cita_data)
            self.log_test("Add medical appointment", success, 
                         f"Response: {cita_response}" if not success else "")
            
            # Test add lab analysis
            analisis_data = {
                "nombre_analisis": "Hemograma completo",
                "resultado": "Normal",
                "fecha_analisis": "2024-01-10",
                "doctor_solicita": "Dr. García"
            }
            success, analisis_response = self.make_request('POST', f'pacientes/{patient_id}/analisis', analisis_data)
            self.log_test("Add lab analysis", success,
                         f"Response: {analisis_response}" if not success else "")
            
            # Test delete patient
            success, delete_response = self.make_request('DELETE', f'pacientes/{patient_id}')
            self.log_test("Delete patient", success,
                         f"Response: {delete_response}" if not success else "")
            
        else:
            self.log_test("Create patient", False, f"Response: {response}")

    def test_medication_management(self):
        """Test medication/pharmacy endpoints with enhanced features"""
        print("\n💊 Testing Medication Management...")
        
        # Create test medication with correct field names
        medication_data = {
            "nombre": "Paracetamol Pediátrico",
            "descripcion": "Analgésico y antipirético para niños",
            "codigo_barras": "7501234567890",
            "stock": 50,
            "stock_minimo": 10,
            "costo_unitario": 15.00,  # Correct field name
            "escala_compra": "10+2",
            "descuento_aplicable": 5.0,
            "impuesto": 15.0,
            "categoria": "Analgésicos",
            "lote": "LOT2024001",
            "fecha_vencimiento": "2025-12-31",
            "proveedor": "Farmacéutica Nacional",
            "indicaciones": "Fiebre y dolor leve a moderado",
            "contraindicaciones": "Hipersensibilidad al paracetamol",
            "dosis_pediatrica": "10-15 mg/kg cada 6-8 horas"
        }
        
        success, response = self.make_request('POST', 'medicamentos', medication_data, expected_status=200)
        
        if success and response.get('id'):
            medication_id = response['id']
            self.log_test("Create medication", True, f"Medication ID: {medication_id}")
            
            # Verify automatic price calculations were applied
            if response.get('precio_publico') and response.get('margen_utilidad'):
                self.log_test("Automatic price calculation on creation", True, 
                            f"Public price: {response['precio_publico']}, Margin: {response['margen_utilidad']}%")
            else:
                self.log_test("Automatic price calculation on creation", False, "Prices not calculated")
            
            # Test get all medications
            success, medications = self.make_request('GET', 'medicamentos')
            if success and isinstance(medications, list):
                self.log_test("Get all medications", True, f"Found {len(medications)} medications")
            else:
                self.log_test("Get all medications", False, f"Response: {medications}")
            
            # Test NEW available medications endpoint (for treatment planning)
            success, available_meds = self.make_request('GET', 'medicamentos/disponibles')
            if success and isinstance(available_meds, list):
                self.log_test("Get available medications", True, f"Found {len(available_meds)} available medications")
                
                # Verify response format includes required fields
                if available_meds and all(key in available_meds[0] for key in ['id', 'nombre', 'categoria', 'stock', 'dosis_pediatrica']):
                    self.log_test("Available medications format", True, "All required fields present")
                else:
                    self.log_test("Available medications format", False, "Missing required fields")
            else:
                self.log_test("Get available medications", False, f"Response: {available_meds}")
            
            # Test available medications with search
            success, search_available = self.make_request('GET', 'medicamentos/disponibles?buscar=Paracetamol')
            if success and isinstance(search_available, list):
                found_paracetamol = any(med['nombre'].lower().find('paracetamol') >= 0 for med in search_available)
                self.log_test("Search available medications", found_paracetamol, 
                            f"Found {len(search_available)} results for 'Paracetamol'")
            else:
                self.log_test("Search available medications", False, f"Response: {search_available}")
            
            # Test search by category
            success, category_search = self.make_request('GET', 'medicamentos/disponibles?buscar=Analgésicos')
            if success and isinstance(category_search, list):
                self.log_test("Search by category", True, f"Found {len(category_search)} analgesics")
            else:
                self.log_test("Search by category", False, f"Response: {category_search}")
            
            # Test search medications (general search)
            success, search_results = self.make_request('GET', 'medicamentos/search?query=Paracetamol')
            if success and isinstance(search_results, list):
                self.log_test("General medication search", True, f"Found {len(search_results)} results")
            else:
                self.log_test("General medication search", False, f"Response: {search_results}")
            
            # Test update stock
            success, stock_response = self.make_request('PUT', f'medicamentos/{medication_id}/stock', {"nuevo_stock": 45})
            self.log_test("Update medication stock", success,
                         f"Response: {stock_response}" if not success else "")
            
        else:
            self.log_test("Create medication", False, f"Response: {response}")

    def test_unauthorized_access(self):
        """Test endpoints without authentication"""
        print("\n🔒 Testing Unauthorized Access...")
        
        # Note: Based on current implementation, token validation might not be fully implemented
        # This is a security concern that should be addressed
        
        # Temporarily remove token
        original_token = self.token
        self.token = "invalid_token"
        
        # Test accessing protected endpoints with invalid token
        success, response = self.make_request('GET', 'pacientes', expected_status=401)
        if success:
            self.log_test("Reject invalid token (security)", True)
        else:
            self.log_test("Reject invalid token (security)", False, 
                         "SECURITY ISSUE: Invalid tokens are being accepted")
        
        # Restore token
        self.token = original_token

    def test_automatic_cie10_classification(self):
        """Test automatic CIE-10 classification feature"""
        print("\n🤖 Testing Automatic CIE-10 Classification...")
        
        # Test classification endpoint
        test_cases = [
            ("fiebre", "R50"),
            ("diarrea", "A09"),
            ("asma", "J45"),
            ("otitis", "H66"),
            ("bronquitis", "J20")
        ]
        
        for diagnostico, expected_code in test_cases:
            success, response = self.make_request('POST', f'cie10/clasificar?diagnostico={diagnostico}')
            if success and response.get('codigo') == expected_code:
                self.log_test(f"Auto-classify '{diagnostico}' -> {expected_code}", True)
                
                # Check if chapter is included
                if response.get('capitulo'):
                    self.log_test(f"Chapter classification for {expected_code}", True, 
                                f"Chapter: {response['capitulo']}")
                else:
                    self.log_test(f"Chapter classification for {expected_code}", False, "No chapter returned")
            else:
                self.log_test(f"Auto-classify '{diagnostico}' -> {expected_code}", False, 
                            f"Expected {expected_code}, got {response.get('codigo')}")

    def test_price_calculation_system(self):
        """Test enhanced pricing system with 25% margin guarantee"""
        print("\n💰 Testing Enhanced Pricing System...")
        
        # Test the new detailed price calculator endpoint
        price_data = {
            "costo_unitario": 20.00,
            "impuesto": 15.0,
            "escala_compra": "10+3",
            "descuento": 10.0
        }
        
        success, response = self.make_request('POST', 'medicamentos/calcular-precios-detallado', price_data)
        if success:
            self.log_test("Enhanced price calculation endpoint", True)
            
            # Verify 25% margin is guaranteed
            if response.get('margen_garantizado'):
                self.log_test("25% margin guarantee flag", response['margen_garantizado'], 
                            f"Margin guaranteed: {response['margen_garantizado']}")
            
            if response.get('margen_utilidad_final'):
                margin = response['margen_utilidad_final']
                # Should be at least 24.5% (with 0.5% tolerance)
                margin_ok = margin >= 24.5
                self.log_test("25% margin verification", margin_ok, 
                            f"Final margin: {margin}%, Expected: >=24.5%")
            else:
                self.log_test("25% margin verification", False, "No final margin returned")
                
            # Check all required price fields are present
            required_fields = [
                'costo_unitario_original', 'costo_con_impuesto', 'costo_real', 
                'precio_base', 'precio_publico', 'precio_final_cliente', 
                'margen_utilidad_final', 'escala_aplicada', 'unidades_recibidas'
            ]
            for field in required_fields:
                if field in response:
                    self.log_test(f"Price field '{field}' present", True, f"Value: {response[field]}")
                else:
                    self.log_test(f"Price field '{field}' present", False)
                    
            # Test scale calculation (10+3 should give 13 units received)
            if response.get('unidades_recibidas') == 13:
                self.log_test("Scale calculation (10+3)", True, "Correctly calculated 13 units received")
            else:
                self.log_test("Scale calculation (10+3)", False, 
                            f"Expected 13 units, got {response.get('unidades_recibidas')}")
        else:
            self.log_test("Enhanced price calculation endpoint", False, f"Response: {response}")
            
        # Test different scale scenarios
        test_scales = [
            {"escala": "sin_escala", "expected_units": 1},
            {"escala": "5+1", "expected_units": 6},
            {"escala": "20+5", "expected_units": 25}
        ]
        
        for scale_test in test_scales:
            scale_data = {
                "costo_unitario": 15.00,
                "escala_compra": scale_test["escala"]
            }
            success, scale_response = self.make_request('POST', 'medicamentos/calcular-precios-detallado', scale_data)
            if success and scale_response.get('unidades_recibidas') == scale_test["expected_units"]:
                self.log_test(f"Scale calculation ({scale_test['escala']})", True)
            else:
                self.log_test(f"Scale calculation ({scale_test['escala']})", False, 
                            f"Expected {scale_test['expected_units']}, got {scale_response.get('unidades_recibidas') if success else 'error'}")

    def test_appointments_system(self):
        """Test appointment management system including two-week calendar and quick appointments"""
        print("\n📅 Testing Appointments System...")
        
        # First create a test patient for appointments
        patient_data = {
            "nombre_completo": "Ana García Rodríguez",
            "fecha_nacimiento": "2020-03-10",
            "nombre_padre": "Luis García",
            "nombre_madre": "Carmen Rodríguez",
            "direccion": "Colonia Palmira, San Pedro Sula",
            "numero_celular": "9988-7766",
            "tratamiento_medico": "Control de crecimiento y desarrollo"
        }
        
        success, patient_response = self.make_request('POST', 'pacientes', patient_data)
        if success and patient_response.get('id'):
            patient_id = patient_response['id']
            
            # Create appointment
            appointment_data = {
                "paciente_id": patient_id,
                "fecha_hora": "2024-02-15T10:30:00",
                "motivo": "Control rutinario",
                "doctor": "Dr. Martínez",
                "notas": "Primera consulta del año"
            }
            
            success, appointment_response = self.make_request('POST', 'citas', appointment_data)
            if success and appointment_response.get('id'):
                appointment_id = appointment_response['id']
                self.log_test("Create appointment", True, f"Appointment ID: {appointment_id}")
                
                # Test get all appointments
                success, appointments = self.make_request('GET', 'citas')
                if success and isinstance(appointments, list):
                    self.log_test("Get all appointments", True, f"Found {len(appointments)} appointments")
                else:
                    self.log_test("Get all appointments", False, f"Response: {appointments}")
                
                # Test weekly appointments
                success, weekly_appointments = self.make_request('GET', 'citas/semana')
                if success and isinstance(weekly_appointments, list):
                    self.log_test("Get weekly appointments", True, f"Found {len(weekly_appointments)} weekly appointments")
                else:
                    self.log_test("Get weekly appointments", False, f"Response: {weekly_appointments}")
                
                # Test NEW two-week calendar endpoint
                success, two_week_appointments = self.make_request('GET', 'citas/dos-semanas')
                if success and isinstance(two_week_appointments, list):
                    self.log_test("Get two-week appointments", True, f"Found {len(two_week_appointments)} appointments in 2-week period")
                else:
                    self.log_test("Get two-week appointments", False, f"Response: {two_week_appointments}")
                
                # Test two-week calendar with specific start date
                success, two_week_specific = self.make_request('GET', 'citas/dos-semanas?fecha_inicio=2024-02-12')
                if success and isinstance(two_week_specific, list):
                    self.log_test("Get two-week appointments with specific date", True, 
                                f"Found {len(two_week_specific)} appointments from 2024-02-12")
                else:
                    self.log_test("Get two-week appointments with specific date", False, f"Response: {two_week_specific}")
                
                # Test update appointment status
                success, status_response = self.make_request('PUT', f'citas/{appointment_id}/estado', {"estado": "confirmada"})
                self.log_test("Update appointment status", success, 
                            f"Response: {status_response}" if not success else "")
                
            else:
                self.log_test("Create appointment", False, f"Response: {appointment_response}")
            
            # Test QUICK APPOINTMENT CREATION with different day ranges
            quick_appointment_tests = [
                {"dias_adelante": 1, "motivo": "Urgente - fiebre alta"},
                {"dias_adelante": 3, "motivo": "Control post-tratamiento"},
                {"dias_adelante": 7, "motivo": "Seguimiento semanal"},
                {"dias_adelante": 14, "motivo": "Control quincenal"},
                {"dias_adelante": 30, "motivo": "Control mensual"}
            ]
            
            for quick_test in quick_appointment_tests:
                quick_data = {
                    "motivo": quick_test["motivo"],
                    "doctor": "Dr. Sistema",
                    "dias_adelante": quick_test["dias_adelante"]
                }
                
                success, quick_response = self.make_request('POST', f'pacientes/{patient_id}/cita-rapida', quick_data)
                if success and quick_response.get('cita_id'):
                    self.log_test(f"Quick appointment ({quick_test['dias_adelante']} days)", True, 
                                f"Created for {quick_test['dias_adelante']} days ahead")
                else:
                    self.log_test(f"Quick appointment ({quick_test['dias_adelante']} days)", False, 
                                f"Response: {quick_response}")
            
            # Clean up - delete test patient
            self.make_request('DELETE', f'pacientes/{patient_id}')
        else:
            self.log_test("Create test patient for appointments", False, f"Response: {patient_response}")

    def test_pharmacy_alerts_system(self):
        """Test enhanced pharmacy alerts system"""
        print("\n⚠️ Testing Enhanced Pharmacy Alerts System...")
        
        # Create medication with low stock
        low_stock_med = {
            "nombre": "Ibuprofeno Infantil",
            "descripcion": "Antiinflamatorio pediátrico",
            "codigo_barras": "7501234567891",
            "stock": 3,
            "stock_minimo": 10,
            "costo_unitario": 18.00,  # Correct field name
            "categoria": "Antiinflamatorios",
            "lote": "LOT2024002",
            "fecha_vencimiento": "2024-03-15",  # Soon to expire
            "proveedor": "Laboratorios Unidos"
        }
        
        success, med_response = self.make_request('POST', 'medicamentos', low_stock_med)
        if success and med_response.get('id'):
            med_id = med_response['id']
            
            # Test comprehensive alerts endpoint
            success, alerts_response = self.make_request('GET', 'medicamentos/alertas')
            if success and alerts_response.get('alertas'):
                self.log_test("Comprehensive alerts endpoint", True, 
                            f"Total alerts: {alerts_response.get('total_alertas', 0)}")
                
                # Check alert structure
                if alerts_response.get('alertas_por_tipo'):
                    stock_alerts = alerts_response['alertas_por_tipo'].get('stock_bajo', 0)
                    expiry_alerts = alerts_response['alertas_por_tipo'].get('vencimiento_cercano', 0)
                    self.log_test("Alert categorization", True, 
                                f"Stock alerts: {stock_alerts}, Expiry alerts: {expiry_alerts}")
                else:
                    self.log_test("Alert categorization", False, "No alert categorization found")
                
                # Verify alert details
                alerts = alerts_response.get('alertas', [])
                if alerts:
                    first_alert = alerts[0]
                    required_alert_fields = ['tipo', 'medicamento_id', 'medicamento_nombre', 'mensaje', 'prioridad']
                    has_all_fields = all(field in first_alert for field in required_alert_fields)
                    self.log_test("Alert structure completeness", has_all_fields, 
                                f"Alert fields: {list(first_alert.keys())}")
                else:
                    self.log_test("Alert structure completeness", False, "No alerts generated")
            else:
                self.log_test("Comprehensive alerts endpoint", False, f"Response: {alerts_response}")
            
            # Test low stock alert
            success, low_stock_response = self.make_request('GET', 'medicamentos/stock-bajo')
            if success and isinstance(low_stock_response, list):
                found_low_stock = any(med['id'] == med_id for med in low_stock_response)
                self.log_test("Low stock alert detection", found_low_stock, 
                            f"Found {len(low_stock_response)} low stock medications")
            else:
                self.log_test("Low stock alert detection", False, f"Response: {low_stock_response}")
            
            # Test expiration alert
            success, expiring_response = self.make_request('GET', 'medicamentos/vencer?dias=60')
            if success and isinstance(expiring_response, list):
                found_expiring = any(med['id'] == med_id for med in expiring_response)
                self.log_test("Expiration alert detection", found_expiring,
                            f"Found {len(expiring_response)} medications expiring in 60 days")
            else:
                self.log_test("Expiration alert detection", False, f"Response: {expiring_response}")
                
        else:
            self.log_test("Create test medication for alerts", False, f"Response: {med_response}")

    def test_cosmetics_category(self):
        """Test cosmetics category in pharmacy"""
        print("\n💄 Testing Cosmetics Category...")
        
        # Create cosmetic product
        cosmetic_data = {
            "nombre": "Crema Hidratante Bebé",
            "descripcion": "Crema hidratante para piel sensible de bebés",
            "codigo_barras": "7501234567892",
            "stock": 25,
            "stock_minimo": 5,
            "costo_base": 12.00,
            "categoria": "Cosméticos",
            "lote": "COSM2024001",
            "fecha_vencimiento": "2026-01-31",
            "proveedor": "Cosméticos Naturales"
        }
        
        success, cosmetic_response = self.make_request('POST', 'medicamentos', cosmetic_data)
        if success and cosmetic_response.get('id'):
            self.log_test("Create cosmetic product", True, f"Product ID: {cosmetic_response['id']}")
            
            # Verify category is correctly set
            if cosmetic_response.get('categoria') == 'Cosméticos':
                self.log_test("Cosmetics category assignment", True)
            else:
                self.log_test("Cosmetics category assignment", False, 
                            f"Expected 'Cosméticos', got '{cosmetic_response.get('categoria')}'")
                
            # Test search by cosmetics category
            success, search_response = self.make_request('GET', 'medicamentos/search?query=Cosméticos')
            if success and isinstance(search_response, list):
                found_cosmetic = any(prod['id'] == cosmetic_response['id'] for prod in search_response)
                self.log_test("Search cosmetics by category", found_cosmetic,
                            f"Found {len(search_response)} cosmetic products")
            else:
                self.log_test("Search cosmetics by category", False, f"Response: {search_response}")
        else:
            self.log_test("Create cosmetic product", False, f"Response: {cosmetic_response}")

    def test_treatment_field_integration(self):
        """Test medical treatment field integration"""
        print("\n🩺 Testing Medical Treatment Field...")
        
        # Create patient with treatment field
        patient_with_treatment = {
            "nombre_completo": "Pedro Martínez Silva",
            "fecha_nacimiento": "2019-07-20",
            "nombre_padre": "Roberto Martínez",
            "nombre_madre": "Elena Silva",
            "direccion": "Barrio La Granja, Tegucigalpa",
            "numero_celular": "9955-4433",
            "diagnostico_clinico": "Bronquitis aguda",
            "tratamiento_medico": "Amoxicilina 250mg cada 8 horas por 7 días, abundantes líquidos y reposo"
        }
        
        success, patient_response = self.make_request('POST', 'pacientes', patient_with_treatment)
        if success and patient_response.get('id'):
            # Verify treatment field is saved
            if patient_response.get('tratamiento_medico'):
                self.log_test("Treatment field creation", True, 
                            f"Treatment: {patient_response['tratamiento_medico'][:50]}...")
            else:
                self.log_test("Treatment field creation", False, "Treatment field not saved")
            
            # Verify automatic CIE-10 classification worked
            if patient_response.get('codigo_cie10'):
                self.log_test("Auto CIE-10 from diagnosis", True, 
                            f"Code: {patient_response['codigo_cie10']}")
                
                # Check if chapter was assigned
                if patient_response.get('capitulo_cie10'):
                    self.log_test("CIE-10 chapter assignment", True,
                                f"Chapter: {patient_response['capitulo_cie10'][:50]}...")
                else:
                    self.log_test("CIE-10 chapter assignment", False, "No chapter assigned")
            else:
                self.log_test("Auto CIE-10 from diagnosis", False, "No automatic classification")
            
            # Clean up
            self.make_request('DELETE', f'pacientes/{patient_response["id"]}')
        else:
            self.log_test("Create patient with treatment", False, f"Response: {patient_response}")

    def run_all_tests(self):
        """Run all test suites"""
        print("🏥 Starting Pediatric Clinic Management System API Tests")
        print("=" * 60)
        
        # Test authentication first
        if not self.test_authentication():
            print("❌ Authentication failed - stopping tests")
            return False
        
        # Run all test suites
        self.test_cie10_endpoints()
        self.test_automatic_cie10_classification()
        self.test_patient_crud_operations()
        self.test_treatment_field_integration()
        self.test_medication_management()
        self.test_price_calculation_system()
        self.test_pharmacy_alerts_system()
        self.test_cosmetics_category()
        self.test_appointments_system()
        self.test_unauthorized_access()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

    def save_results(self, filename="/app/test_reports/backend_test_results.json"):
        """Save test results to file"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "test_details": self.test_results
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"📄 Test results saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

def main():
    """Main test execution"""
    tester = PediatricClinicAPITester()
    
    try:
        success = tester.run_all_tests()
        tester.save_results()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())