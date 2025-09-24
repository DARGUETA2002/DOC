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
    def __init__(self, base_url="https://pedisalud-1.preview.emergentagent.com"):
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
        """Test medication/pharmacy endpoints with new pricing system"""
        print("\n💊 Testing Medication Management...")
        
        # Create test medication with new fields
        medication_data = {
            "nombre": "Paracetamol Pediátrico",
            "descripcion": "Analgésico y antipirético para niños",
            "codigo_barras": "7501234567890",
            "stock": 50,
            "stock_minimo": 10,
            "costo_base": 15.00,
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
            
            # Test get all medications
            success, medications = self.make_request('GET', 'medicamentos')
            if success and isinstance(medications, list):
                self.log_test("Get all medications", True, f"Found {len(medications)} medications")
            else:
                self.log_test("Get all medications", False, f"Response: {medications}")
            
            # Test search medications
            success, search_results = self.make_request('GET', 'medicamentos/search?query=Paracetamol')
            if success and isinstance(search_results, list):
                self.log_test("Search medications", True, f"Found {len(search_results)} results")
            else:
                self.log_test("Search medications", False, f"Response: {search_results}")
            
            # Test update stock
            success, stock_response = self.make_request('PUT', f'medicamentos/{medication_id}/stock?nuevo_stock=45')
            self.log_test("Update medication stock", success,
                         f"Response: {stock_response}" if not success else "")
            
        else:
            self.log_test("Create medication", False, f"Response: {response}")

    def test_unauthorized_access(self):
        """Test endpoints without authentication"""
        print("\n🔒 Testing Unauthorized Access...")
        
        # Temporarily remove token
        original_token = self.token
        self.token = None
        
        # Test accessing protected endpoints without token
        success, response = self.make_request('GET', 'pacientes', expected_status=401)
        self.log_test("Access patients without token (should fail)", success)
        
        success, response = self.make_request('GET', 'medicamentos', expected_status=401)
        self.log_test("Access medications without token (should fail)", success)
        
        success, response = self.make_request('GET', 'cie10', expected_status=401)
        self.log_test("Access CIE-10 without token (should fail)", success)
        
        # Restore token
        self.token = original_token

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
        self.test_patient_crud_operations()
        self.test_medication_management()
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