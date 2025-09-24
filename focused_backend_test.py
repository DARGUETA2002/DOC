#!/usr/bin/env python3
"""
Focused Backend API Testing for Review Request Features
Tests the specific features mentioned in the review request
"""

import requests
import sys
import json
from datetime import datetime, date
from typing import Dict, Any

class FocusedAPITester:
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

    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None, params: Dict[str, Any] = None, expected_status: int = 200) -> tuple[bool, Dict[Any, Any]]:
        """Make HTTP request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, params=params, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, params=params, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=30)
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
        """Test authentication with code 1970"""
        print("\n🔐 Testing Authentication...")
        
        success, response = self.make_request('POST', 'login', {"codigo": "1970"}, expected_status=200)
        
        if success and response.get('success') and response.get('token'):
            self.token = response['token']
            self.log_test("Login with code 1970", True)
            return True
        else:
            self.log_test("Login with code 1970", False, f"Response: {response}")
            return False

    def test_two_week_calendar(self):
        """Test two-week calendar endpoint"""
        print("\n📅 Testing Two-Week Calendar Endpoint...")
        
        # Create test patient and appointment first
        patient_data = {
            "nombre_completo": "Test Patient Calendar",
            "fecha_nacimiento": "2020-01-15",
            "nombre_padre": "Test Father",
            "nombre_madre": "Test Mother",
            "direccion": "Test Address",
            "numero_celular": "9999-9999"
        }
        
        success, patient_response = self.make_request('POST', 'pacientes', patient_data)
        if success and patient_response.get('id'):
            patient_id = patient_response['id']
            
            # Create appointment for testing
            appointment_data = {
                "paciente_id": patient_id,
                "fecha_hora": "2024-02-15T10:30:00",
                "motivo": "Test appointment",
                "doctor": "Dr. Test"
            }
            
            success, appointment_response = self.make_request('POST', 'citas', appointment_data)
            if success:
                # Test two-week calendar endpoint
                success, two_week_response = self.make_request('GET', 'citas/dos-semanas')
                if success and isinstance(two_week_response, list):
                    self.log_test("Two-week calendar endpoint", True, f"Found {len(two_week_response)} appointments")
                    
                    # Test with specific date
                    success, specific_date_response = self.make_request('GET', 'citas/dos-semanas?fecha_inicio=2024-02-12')
                    if success and isinstance(specific_date_response, list):
                        self.log_test("Two-week calendar with specific date", True, f"Found {len(specific_date_response)} appointments")
                    else:
                        self.log_test("Two-week calendar with specific date", False, f"Response: {specific_date_response}")
                else:
                    self.log_test("Two-week calendar endpoint", False, f"Response: {two_week_response}")
            
            # Cleanup
            self.make_request('DELETE', f'pacientes/{patient_id}')
        else:
            self.log_test("Create test patient for calendar", False, f"Response: {patient_response}")

    def test_pharmacy_integration(self):
        """Test pharmacy integration with search functionality"""
        print("\n💊 Testing Pharmacy Integration...")
        
        # Create test medications
        medications = [
            {
                "nombre": "Paracetamol Pediátrico",
                "descripcion": "Analgésico y antipirético",
                "stock": 50,
                "costo_unitario": 15.00,
                "categoria": "Analgésicos",
                "indicaciones": "Fiebre y dolor",
                "dosis_pediatrica": "10-15 mg/kg cada 6-8 horas"
            },
            {
                "nombre": "Amoxicilina Suspensión",
                "descripcion": "Antibiótico pediátrico",
                "stock": 30,
                "costo_unitario": 25.00,
                "categoria": "Antibióticos",
                "indicaciones": "Infecciones bacterianas",
                "dosis_pediatrica": "20-40 mg/kg/día"
            }
        ]
        
        created_meds = []
        for med_data in medications:
            success, med_response = self.make_request('POST', 'medicamentos', med_data)
            if success and med_response.get('id'):
                created_meds.append(med_response['id'])
        
        if len(created_meds) >= 2:
            self.log_test("Create test medications", True, f"Created {len(created_meds)} medications")
            
            # Test available medications endpoint
            success, available_response = self.make_request('GET', 'medicamentos/disponibles')
            if success and isinstance(available_response, list):
                self.log_test("Get available medications", True, f"Found {len(available_response)} available medications")
                
                # Test search functionality
                success, search_response = self.make_request('GET', 'medicamentos/disponibles?buscar=Paracetamol')
                if success and isinstance(search_response, list):
                    found_paracetamol = any('paracetamol' in med['nombre'].lower() for med in search_response)
                    self.log_test("Search medications by name", found_paracetamol, f"Found {len(search_response)} results")
                else:
                    self.log_test("Search medications by name", False, f"Response: {search_response}")
                
                # Test search by category
                success, category_response = self.make_request('GET', 'medicamentos/disponibles?buscar=Analgésicos')
                if success and isinstance(category_response, list):
                    self.log_test("Search medications by category", True, f"Found {len(category_response)} analgesics")
                else:
                    self.log_test("Search medications by category", False, f"Response: {category_response}")
            else:
                self.log_test("Get available medications", False, f"Response: {available_response}")
        else:
            self.log_test("Create test medications", False, "Failed to create required medications")

    def test_quick_appointment_creation(self):
        """Test quick appointment creation with different day ranges"""
        print("\n⚡ Testing Quick Appointment Creation...")
        
        # Create test patient
        patient_data = {
            "nombre_completo": "Quick Appointment Patient",
            "fecha_nacimiento": "2019-06-10",
            "nombre_padre": "Quick Father",
            "nombre_madre": "Quick Mother",
            "direccion": "Quick Address",
            "numero_celular": "8888-8888"
        }
        
        success, patient_response = self.make_request('POST', 'pacientes', patient_data)
        if success and patient_response.get('id'):
            patient_id = patient_response['id']
            
            # Test different day ranges
            day_ranges = [1, 3, 7, 14, 30]
            for days in day_ranges:
                # Note: CitaRapida model expects paciente_id in body even though it's in path
                quick_data = {
                    "paciente_id": patient_id,  # Required by the model
                    "motivo": f"Quick appointment for {days} days ahead",
                    "doctor": "Dr. Quick",
                    "dias_adelante": days
                }
                
                success, quick_response = self.make_request('POST', f'pacientes/{patient_id}/cita-rapida', quick_data)
                if success and quick_response.get('cita_id'):
                    self.log_test(f"Quick appointment ({days} days)", True, f"Created appointment ID: {quick_response['cita_id']}")
                else:
                    self.log_test(f"Quick appointment ({days} days)", False, f"Response: {quick_response}")
            
            # Cleanup
            self.make_request('DELETE', f'pacientes/{patient_id}')
        else:
            self.log_test("Create test patient for quick appointments", False, f"Response: {patient_response}")

    def test_enhanced_pricing_system(self):
        """Test enhanced pricing system with 25% margin guarantee"""
        print("\n💰 Testing Enhanced Pricing System...")
        
        # Test detailed price calculation endpoint (uses query parameters)
        params = "costo_unitario=20.00&impuesto=15.0&escala_compra=10+3&descuento=10.0"
        
        success, response = self.make_request('POST', f'medicamentos/calcular-precios-detallado?{params}')
        if success:
            self.log_test("Enhanced price calculation endpoint", True)
            
            # Check 25% margin guarantee
            if response.get('margen_garantizado'):
                self.log_test("25% margin guarantee flag", response['margen_garantizado'], 
                            f"Margin guaranteed: {response['margen_garantizado']}")
            
            if response.get('margen_utilidad_final'):
                margin = response['margen_utilidad_final']
                margin_ok = margin >= 24.5  # Allow 0.5% tolerance
                self.log_test("25% margin verification", margin_ok, 
                            f"Final margin: {margin}%, Expected: >=24.5%")
            
            # Test scale calculation
            if response.get('unidades_recibidas') == 13.0:  # 10+3 (float comparison)
                self.log_test("Scale calculation (10+3)", True, "Correctly calculated 13 units")
            else:
                self.log_test("Scale calculation (10+3)", False, 
                            f"Expected 13 units, got {response.get('unidades_recibidas')}")
                            
            # Test different scales
            test_scales = [
                ("sin_escala", 1.0),
                ("5+1", 6.0),
                ("20+5", 25.0)
            ]
            
            for escala, expected_units in test_scales:
                scale_params = f"costo_unitario=15.00&escala_compra={escala}"
                success, scale_response = self.make_request('POST', f'medicamentos/calcular-precios-detallado?{scale_params}')
                if success and scale_response.get('unidades_recibidas') == expected_units:
                    self.log_test(f"Scale calculation ({escala})", True, f"Got {expected_units} units")
                else:
                    self.log_test(f"Scale calculation ({escala})", False, 
                                f"Expected {expected_units}, got {scale_response.get('unidades_recibidas') if success else 'error'}")
        else:
            self.log_test("Enhanced price calculation endpoint", False, f"Response: {response}")

    def test_patient_medication_integration(self):
        """Test patient medication integration"""
        print("\n👶💊 Testing Patient Medication Integration...")
        
        # Create test medication first
        med_data = {
            "nombre": "Test Medication for Patient",
            "descripcion": "Test medication",
            "stock": 20,
            "costo_unitario": 10.00,
            "categoria": "Test Category"
        }
        
        success, med_response = self.make_request('POST', 'medicamentos', med_data)
        if success and med_response.get('id'):
            med_id = med_response['id']
            
            # Create patient with prescribed medications
            patient_data = {
                "nombre_completo": "Patient With Medications",
                "fecha_nacimiento": "2021-03-20",
                "nombre_padre": "Med Father",
                "nombre_madre": "Med Mother",
                "direccion": "Med Address",
                "numero_celular": "7777-7777",
                "medicamentos_recetados": [med_id]
            }
            
            success, patient_response = self.make_request('POST', 'pacientes', patient_data)
            if success and patient_response.get('id'):
                patient_id = patient_response['id']
                
                # Verify medicamentos_recetados field
                if patient_response.get('medicamentos_recetados'):
                    prescribed_meds = patient_response['medicamentos_recetados']
                    if med_id in prescribed_meds:
                        self.log_test("Patient medication storage", True, f"Stored {len(prescribed_meds)} medications")
                    else:
                        self.log_test("Patient medication storage", False, "Medication ID not found in patient record")
                else:
                    self.log_test("Patient medication storage", False, "medicamentos_recetados field not saved")
                
                # Test retrieval
                success, retrieved_patient = self.make_request('GET', f'pacientes/{patient_id}')
                if success and retrieved_patient.get('medicamentos_recetados'):
                    if med_id in retrieved_patient['medicamentos_recetados']:
                        self.log_test("Patient medication retrieval", True, "Medication correctly retrieved")
                    else:
                        self.log_test("Patient medication retrieval", False, "Medication not found on retrieval")
                else:
                    self.log_test("Patient medication retrieval", False, "medicamentos_recetados field not retrieved")
                
                # Cleanup
                self.make_request('DELETE', f'pacientes/{patient_id}')
        else:
            self.log_test("Create test medication for patient", False, f"Response: {med_response}")

    def test_existing_endpoints(self):
        """Test existing core endpoints"""
        print("\n🏥 Testing Existing Core Endpoints...")
        
        # Test CIE-10 endpoints
        success, cie10_response = self.make_request('GET', 'cie10')
        if success and isinstance(cie10_response, list) and len(cie10_response) > 0:
            self.log_test("CIE-10 codes endpoint", True, f"Found {len(cie10_response)} codes")
        else:
            self.log_test("CIE-10 codes endpoint", False, f"Response: {cie10_response}")
        
        # Test CIE-10 classification
        success, classify_response = self.make_request('POST', 'cie10/clasificar?diagnostico=fiebre')
        if success and classify_response.get('codigo'):
            self.log_test("CIE-10 classification", True, f"Classified 'fiebre' as {classify_response['codigo']}")
        else:
            self.log_test("CIE-10 classification", False, f"Response: {classify_response}")
        
        # Test basic patient CRUD
        patient_data = {
            "nombre_completo": "Test CRUD Patient",
            "fecha_nacimiento": "2020-05-15",
            "nombre_padre": "CRUD Father",
            "nombre_madre": "CRUD Mother",
            "direccion": "CRUD Address",
            "numero_celular": "6666-6666"
        }
        
        success, patient_response = self.make_request('POST', 'pacientes', patient_data)
        if success and patient_response.get('id'):
            self.log_test("Patient creation", True, f"Created patient ID: {patient_response['id']}")
            
            # Test get patient
            success, get_response = self.make_request('GET', f'pacientes/{patient_response["id"]}')
            if success and get_response.get('id') == patient_response['id']:
                self.log_test("Patient retrieval", True)
            else:
                self.log_test("Patient retrieval", False, f"Response: {get_response}")
            
            # Cleanup
            self.make_request('DELETE', f'pacientes/{patient_response["id"]}')
        else:
            self.log_test("Patient creation", False, f"Response: {patient_response}")

    def run_focused_tests(self):
        """Run focused tests for review request"""
        print("🏥 Starting Focused Backend API Tests for Review Request")
        print("=" * 60)
        
        # Test authentication first
        if not self.test_authentication():
            print("❌ Authentication failed - stopping tests")
            return False
        
        # Run focused test suites
        self.test_two_week_calendar()
        self.test_pharmacy_integration()
        self.test_quick_appointment_creation()
        self.test_enhanced_pricing_system()
        self.test_patient_medication_integration()
        self.test_existing_endpoints()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All focused tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test execution"""
    tester = FocusedAPITester()
    
    try:
        success = tester.run_focused_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())