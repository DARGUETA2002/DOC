#!/usr/bin/env python3
"""
Enhanced Backend API Testing for Pediatric Clinic System - Focus on New Features
Tests the completely enhanced system with all new improvements as requested
"""

import requests
import sys
import json
from datetime import datetime, date
from typing import Dict, Any

class EnhancedPediatricClinicTester:
    def __init__(self, base_url="https://pedimed-fix.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.critical_failures = []

    def log_test(self, name: str, success: bool, details: str = "", is_critical: bool = False):
        """Log test results with critical failure tracking"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            if is_critical:
                self.critical_failures.append(f"{name}: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "critical": is_critical,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None, params: Dict[str, str] = None, expected_status: int = 200) -> tuple[bool, Dict[Any, Any]]:
        """Make HTTP request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params, timeout=30)
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

    def test_authentication_with_code_1970(self):
        """Test authentication using code '1970' as specified"""
        print("\n🔐 Testing Authentication with Code 1970...")
        
        # Test valid code 1970
        success, response = self.make_request(
            'POST', 'login', 
            {"codigo": "1970"}, 
            expected_status=200
        )
        
        if success and response.get('success') and response.get('token'):
            self.token = response['token']
            self.log_test("Login with code '1970'", True, is_critical=True)
            self.log_test("Token received", response.get('token') == 'valid_token_1970')
            self.log_test("Role is doctor", response.get('role') == 'doctor')
            return True
        else:
            self.log_test("Login with code '1970'", False, f"Response: {response}", is_critical=True)
            return False

    def test_enhanced_cie10_ai_classification(self):
        """Test Enhanced CIE-10 with AI Classification"""
        print("\n🧠 Testing Enhanced CIE-10 with AI Classification...")
        
        # Test the specific example from the review request
        test_diagnosis = "Diarrea y gastroenteritis de presunto origen infeccioso"
        
        success, response = self.make_request(
            'POST', 'cie10/clasificar', 
            params={"diagnostico": test_diagnosis}
        )
        
        if success:
            self.log_test("AI Classification endpoint accessible", True, is_critical=True)
            
            # Check if AI classification is working
            if response.get('metodo') == 'ai':
                self.log_test("AI-powered classification working", True, 
                            f"Method: {response.get('metodo')}, Confidence: {response.get('confianza')}")
                
                # Verify expected code for the test case
                if response.get('codigo') == 'A09.9':
                    self.log_test("Correct AI classification for test case", True, 
                                f"Got A09.9 for '{test_diagnosis}'")
                else:
                    self.log_test("Correct AI classification for test case", False, 
                                f"Expected A09.9, got {response.get('codigo')}")
            
            elif response.get('metodo') == 'reglas':
                self.log_test("Fallback to rule-based system", True, 
                            "AI failed, using rule-based classification")
                
                # Still should get correct classification
                if response.get('codigo'):
                    self.log_test("Rule-based classification working", True, 
                                f"Code: {response.get('codigo')}")
                else:
                    self.log_test("Rule-based classification working", False, "No code returned")
            
            else:
                self.log_test("AI or fallback classification", False, 
                            f"Unknown method: {response.get('metodo')}", is_critical=True)
            
            # Test confidence levels
            if response.get('confianza') in ['alta', 'media', 'baja']:
                self.log_test("Confidence level provided", True, f"Confidence: {response.get('confianza')}")
            else:
                self.log_test("Confidence level provided", False, f"Invalid confidence: {response.get('confianza')}")
                
            # Test chapter classification
            if response.get('capitulo'):
                self.log_test("Chapter classification included", True, f"Chapter: {response.get('capitulo')[:50]}...")
            else:
                self.log_test("Chapter classification included", False, "No chapter provided")
                
        else:
            self.log_test("AI Classification endpoint accessible", False, f"Response: {response}", is_critical=True)
        
        # Test additional Spanish medical terms
        spanish_terms = [
            "Fiebre alta en niño",
            "Otitis media aguda",
            "Bronquitis aguda",
            "Dolor abdominal"
        ]
        
        for term in spanish_terms:
            success, response = self.make_request('POST', 'cie10/clasificar', params={"diagnostico": term})
            if success and response.get('codigo'):
                self.log_test(f"Spanish term classification: '{term}'", True, 
                            f"Code: {response.get('codigo')}")
            else:
                self.log_test(f"Spanish term classification: '{term}'", False, 
                            f"No classification for '{term}'")

    def test_fixed_pricing_calculator(self):
        """Test Fixed Pricing Calculator with 25% margin guarantee"""
        print("\n💰 Testing Fixed Pricing Calculator...")
        
        # Test the specific scenario from review request
        test_scenario = {
            "costo_unitario": 100.0,
            "impuesto": 15.0,
            "escala_compra": "10+3",
            "descuento": 10.0
        }
        
        success, response = self.make_request(
            'POST', 'medicamentos/calcular-precios-detallado', 
            params=test_scenario
        )
        
        if success:
            self.log_test("Pricing calculator endpoint accessible", True, is_critical=True)
            
            # Verify 25% margin guarantee
            if response.get('margen_garantizado'):
                self.log_test("25% margin guarantee flag", True, 
                            f"Margin guaranteed: {response['margen_garantizado']}")
            else:
                self.log_test("25% margin guarantee flag", False, 
                            "Margin guarantee flag missing or false", is_critical=True)
            
            # Check final margin is at least 25%
            final_margin = response.get('margen_utilidad_final')
            if final_margin and final_margin >= 24.5:  # 0.5% tolerance
                self.log_test("25% margin verification", True, 
                            f"Final margin: {final_margin}%")
            else:
                self.log_test("25% margin verification", False, 
                            f"Final margin: {final_margin}% (should be ≥25%)", is_critical=True)
            
            # Test scale calculation (10+3 = 13 units)
            if response.get('unidades_recibidas') == 13:
                self.log_test("Scale calculation (10+3)", True, "Correctly calculated 13 units")
            else:
                self.log_test("Scale calculation (10+3)", False, 
                            f"Expected 13 units, got {response.get('unidades_recibidas')}")
            
            # Verify all required pricing fields
            required_fields = [
                'costo_unitario_original', 'costo_con_impuesto', 'costo_real',
                'precio_base', 'precio_publico', 'precio_final_cliente',
                'margen_utilidad_final', 'utilidad_por_unidad'
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if not missing_fields:
                self.log_test("All pricing fields present", True)
            else:
                self.log_test("All pricing fields present", False, 
                            f"Missing fields: {missing_fields}")
            
            # Test formula accuracy
            if response.get('formulas_aplicadas'):
                self.log_test("Pricing formulas documentation", True, "Formulas provided")
            else:
                self.log_test("Pricing formulas documentation", False, "No formulas documented")
                
        else:
            self.log_test("Pricing calculator endpoint accessible", False, 
                        f"Response: {response}", is_critical=True)
        
        # Test additional scenarios
        additional_scenarios = [
            {"costo_unitario": 50.0, "escala_compra": "5+1", "expected_units": 6},
            {"costo_unitario": 200.0, "escala_compra": "20+5", "expected_units": 25},
            {"costo_unitario": 30.0, "escala_compra": "sin_escala", "expected_units": 1}
        ]
        
        for scenario in additional_scenarios:
            success, response = self.make_request(
                'POST', 'medicamentos/calcular-precios-detallado',
                params={"costo_unitario": scenario["costo_unitario"], "escala_compra": scenario["escala_compra"]}
            )
            if success and response.get('unidades_recibidas') == scenario["expected_units"]:
                self.log_test(f"Scale calculation ({scenario['escala_compra']})", True)
            else:
                self.log_test(f"Scale calculation ({scenario['escala_compra']})", False,
                            f"Expected {scenario['expected_units']}, got {response.get('unidades_recibidas') if success else 'error'}")

    def test_sales_system(self):
        """Test Sales System endpoints"""
        print("\n💳 Testing Sales System...")
        
        # First create test medications for sales
        test_medications = [
            {
                "nombre": "Paracetamol Infantil 120mg",
                "descripcion": "Antipirético pediátrico",
                "stock": 100,
                "costo_unitario": 15.0,
                "categoria": "Analgésicos",
                "precio_publico": 25.0
            },
            {
                "nombre": "Amoxicilina Suspensión",
                "descripcion": "Antibiótico pediátrico",
                "stock": 50,
                "costo_unitario": 30.0,
                "categoria": "Antibióticos",
                "precio_publico": 50.0
            }
        ]
        
        medication_ids = []
        for med_data in test_medications:
            success, response = self.make_request('POST', 'medicamentos', med_data)
            if success and response.get('id'):
                medication_ids.append(response['id'])
        
        if len(medication_ids) >= 2:
            self.log_test("Create test medications for sales", True, f"Created {len(medication_ids)} medications")
            
            # Test POST /api/ventas to create new sales
            sale_data = {
                "items": [
                    {
                        "medicamento_id": medication_ids[0],
                        "cantidad": 2,
                        "descuento_aplicado": 0
                    },
                    {
                        "medicamento_id": medication_ids[1],
                        "cantidad": 1,
                        "descuento_aplicado": 5.0
                    }
                ],
                "descuento_total": 0,
                "vendedor": "Dr. Test",
                "notas": "Venta de prueba"
            }
            
            success, sale_response = self.make_request('POST', 'ventas', sale_data)
            if success and sale_response.get('id'):
                sale_id = sale_response['id']
                self.log_test("Create new sale", True, f"Sale ID: {sale_id}", is_critical=True)
                
                # Verify sale calculations
                if sale_response.get('total_venta') and sale_response.get('utilidad_bruta'):
                    self.log_test("Sale calculations", True, 
                                f"Total: {sale_response['total_venta']}, Profit: {sale_response['utilidad_bruta']}")
                else:
                    self.log_test("Sale calculations", False, "Missing total or profit calculations")
                
                # Verify items structure
                if sale_response.get('items') and len(sale_response['items']) == 2:
                    self.log_test("Sale items structure", True, f"Contains {len(sale_response['items'])} items")
                else:
                    self.log_test("Sale items structure", False, "Incorrect items structure")
                    
            else:
                self.log_test("Create new sale", False, f"Response: {sale_response}", is_critical=True)
            
            # Test /api/ventas/hoy for today's sales summary
            success, today_sales = self.make_request('GET', 'ventas/hoy')
            if success:
                self.log_test("Today's sales summary endpoint", True, is_critical=True)
                
                # Check if our sale appears in today's summary
                if isinstance(today_sales, dict) and today_sales.get('numero_ventas') is not None:
                    self.log_test("Today's sales data structure", True, 
                                f"Sales today: {today_sales.get('numero_ventas', 0)}")
                else:
                    self.log_test("Today's sales data structure", False, f"Invalid data structure: {today_sales}")
            else:
                self.log_test("Today's sales summary endpoint", False, f"Response: {today_sales}", is_critical=True)
            
            # Test /api/ventas/balance-diario for daily balance
            success, daily_balance = self.make_request('GET', 'ventas/balance-diario')
            if success:
                self.log_test("Daily balance endpoint", True, is_critical=True)
                
                # Verify balance structure
                required_balance_fields = ['total_ventas', 'total_costos', 'utilidad_bruta', 'numero_ventas']
                if all(field in daily_balance for field in required_balance_fields):
                    self.log_test("Daily balance structure", True, 
                                f"Balance: {daily_balance.get('total_ventas', 0)} sales, {daily_balance.get('utilidad_bruta', 0)} profit")
                else:
                    self.log_test("Daily balance structure", False, "Missing required balance fields")
            else:
                self.log_test("Daily balance endpoint", False, f"Response: {daily_balance}", is_critical=True)
                
        else:
            self.log_test("Create test medications for sales", False, "Failed to create required medications", is_critical=True)

    def test_enhanced_pharmacy_alerts(self):
        """Test Enhanced Pharmacy Alerts with 4-week expiration warnings"""
        print("\n⚠️ Testing Enhanced Pharmacy Alerts...")
        
        # Create medication with near expiration (within 4 weeks)
        from datetime import timedelta
        near_expiry_date = (date.today() + timedelta(days=20)).isoformat()  # 20 days from now
        
        alert_test_med = {
            "nombre": "Ibuprofeno Test Alert",
            "descripcion": "Medication for alert testing",
            "stock": 3,
            "stock_minimo": 10,
            "costo_unitario": 20.0,
            "categoria": "Test",
            "fecha_vencimiento": near_expiry_date
        }
        
        success, med_response = self.make_request('POST', 'medicamentos', alert_test_med)
        if success and med_response.get('id'):
            med_id = med_response['id']
            
            # Test /api/medicamentos/alertas endpoint
            success, alerts_response = self.make_request('GET', 'medicamentos/alertas')
            if success:
                self.log_test("Pharmacy alerts endpoint", True, is_critical=True)
                
                # Check 4-week expiration warnings
                if alerts_response.get('alertas'):
                    alerts = alerts_response['alertas']
                    expiry_alerts = [a for a in alerts if a.get('tipo') == 'vencimiento_cercano']
                    
                    if expiry_alerts:
                        self.log_test("4-week expiration warnings", True, 
                                    f"Found {len(expiry_alerts)} expiration alerts")
                        
                        # Check if our test medication appears in alerts
                        our_alert = next((a for a in expiry_alerts if a.get('medicamento_id') == med_id), None)
                        if our_alert:
                            self.log_test("Test medication in expiration alerts", True, 
                                        f"Alert: {our_alert.get('mensaje', '')}")
                        else:
                            self.log_test("Test medication in expiration alerts", False, 
                                        "Test medication not found in alerts")
                    else:
                        self.log_test("4-week expiration warnings", False, "No expiration alerts found")
                
                # Check stock alerts
                if alerts_response.get('alertas_por_tipo'):
                    stock_alerts = alerts_response['alertas_por_tipo'].get('stock_bajo', 0)
                    expiry_alerts = alerts_response['alertas_por_tipo'].get('vencimiento_cercano', 0)
                    
                    self.log_test("Alert categorization", True, 
                                f"Stock alerts: {stock_alerts}, Expiry alerts: {expiry_alerts}")
                else:
                    self.log_test("Alert categorization", False, "No alert categorization")
                
                # Check priority levels (alta, media, baja)
                if alerts_response.get('alertas'):
                    priorities = set(alert.get('prioridad') for alert in alerts_response['alertas'])
                    valid_priorities = priorities.intersection({'alta', 'media', 'baja'})
                    
                    if valid_priorities:
                        self.log_test("Priority levels (alta, media, baja)", True, 
                                    f"Found priorities: {list(valid_priorities)}")
                    else:
                        self.log_test("Priority levels (alta, media, baja)", False, 
                                    f"Invalid priorities: {list(priorities)}")
                        
            else:
                self.log_test("Pharmacy alerts endpoint", False, f"Response: {alerts_response}", is_critical=True)
                
        else:
            self.log_test("Create test medication for alerts", False, f"Response: {med_response}")

    def test_two_week_calendar(self):
        """Test Two-Week Calendar endpoint"""
        print("\n📅 Testing Two-Week Calendar...")
        
        # Test /api/citas/dos-semanas endpoint
        success, two_week_response = self.make_request('GET', 'citas/dos-semanas')
        if success:
            self.log_test("Two-week calendar endpoint", True, is_critical=True)
            
            if isinstance(two_week_response, list):
                self.log_test("Two-week calendar data format", True, 
                            f"Found {len(two_week_response)} appointments in 2-week period")
            else:
                self.log_test("Two-week calendar data format", False, "Invalid data format")
                
        else:
            self.log_test("Two-week calendar endpoint", False, f"Response: {two_week_response}", is_critical=True)
        
        # Test with date ranges
        test_date = "2024-02-01"
        success, date_range_response = self.make_request('GET', 'citas/dos-semanas', 
                                                       params={"fecha_inicio": test_date})
        if success:
            self.log_test("Two-week calendar with date range", True, 
                        f"Found {len(date_range_response) if isinstance(date_range_response, list) else 0} appointments from {test_date}")
        else:
            self.log_test("Two-week calendar with date range", False, f"Response: {date_range_response}")

    def test_medication_updates(self):
        """Test Medication Updates (PUT /api/medicamentos/{id})"""
        print("\n💊 Testing Medication Updates...")
        
        # Create test medication first
        original_med = {
            "nombre": "Test Update Medication",
            "descripcion": "Original description",
            "stock": 20,
            "costo_unitario": 25.0,
            "categoria": "Test Category",
            "impuesto": 15.0
        }
        
        success, create_response = self.make_request('POST', 'medicamentos', original_med)
        if success and create_response.get('id'):
            med_id = create_response['id']
            
            # Test PUT update
            updated_data = {
                "nombre": "Updated Test Medication",
                "descripcion": "Updated description",
                "stock": 30,
                "costo_unitario": 35.0,
                "categoria": "Updated Category",
                "impuesto": 18.0
            }
            
            success, update_response = self.make_request('PUT', f'medicamentos/{med_id}', updated_data)
            if success:
                self.log_test("Medication update endpoint", True, is_critical=True)
                
                # Verify updates were applied
                if update_response.get('nombre') == "Updated Test Medication":
                    self.log_test("Medication name update", True)
                else:
                    self.log_test("Medication name update", False, 
                                f"Expected 'Updated Test Medication', got '{update_response.get('nombre')}'")
                
                if update_response.get('stock') == 30:
                    self.log_test("Medication stock update", True)
                else:
                    self.log_test("Medication stock update", False, 
                                f"Expected 30, got {update_response.get('stock')}")
                
                # Verify price recalculation after update
                if update_response.get('precio_publico') != create_response.get('precio_publico'):
                    self.log_test("Price recalculation on update", True, 
                                f"Price changed from {create_response.get('precio_publico')} to {update_response.get('precio_publico')}")
                else:
                    self.log_test("Price recalculation on update", False, "Price should have changed")
                    
            else:
                self.log_test("Medication update endpoint", False, f"Response: {update_response}", is_critical=True)
                
        else:
            self.log_test("Create test medication for update", False, f"Response: {create_response}")

    def test_all_endpoints_with_authentication(self):
        """Test all endpoints with proper authentication headers"""
        print("\n🔐 Testing All Endpoints with Authentication...")
        
        # List of critical endpoints that should require authentication
        protected_endpoints = [
            ('GET', 'cie10'),
            ('GET', 'pacientes'),
            ('GET', 'medicamentos'),
            ('GET', 'citas'),
            ('GET', 'medicamentos/alertas'),
            ('GET', 'ventas/balance-diario'),
            ('POST', 'cie10/clasificar', {"diagnostico": "test"})
        ]
        
        for endpoint_info in protected_endpoints:
            if len(endpoint_info) == 3:
                method, endpoint, params = endpoint_info
                success, response = self.make_request(method, endpoint, params=params)
            else:
                method, endpoint = endpoint_info
                success, response = self.make_request(method, endpoint)
            if success:
                self.log_test(f"Authentication for {method} {endpoint}", True)
            else:
                # Check if it's an authentication error
                if isinstance(response, dict) and response.get('status_code') == 401:
                    self.log_test(f"Authentication for {method} {endpoint}", False, 
                                "Authentication required but token may be invalid", is_critical=True)
                else:
                    self.log_test(f"Authentication for {method} {endpoint}", False, 
                                f"Unexpected error: {response}")

    def run_enhanced_tests(self):
        """Run all enhanced tests focusing on new features"""
        print("🏥 Starting Enhanced Pediatric Clinic System Tests")
        print("🎯 Focus: New Features and Improvements")
        print("=" * 70)
        
        # Test authentication first
        if not self.test_authentication_with_code_1970():
            print("❌ Authentication failed - stopping tests")
            return False
        
        # Run enhanced test suites focusing on new features
        self.test_enhanced_cie10_ai_classification()
        self.test_fixed_pricing_calculator()
        self.test_sales_system()
        self.test_enhanced_pharmacy_alerts()
        self.test_two_week_calendar()
        self.test_medication_updates()
        self.test_all_endpoints_with_authentication()
        
        # Print summary
        print("\n" + "=" * 70)
        print(f"📊 Enhanced Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.critical_failures:
            print(f"🚨 Critical Failures ({len(self.critical_failures)}):")
            for failure in self.critical_failures:
                print(f"   • {failure}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All enhanced tests passed!")
            return True
        else:
            failed_tests = self.tests_run - self.tests_passed
            print(f"⚠️  {failed_tests} tests failed")
            return False

    def save_results(self, filename="/app/enhanced_test_results.json"):
        """Save enhanced test results"""
        results = {
            "test_type": "enhanced_features",
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "critical_failures": len(self.critical_failures),
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "critical_failure_details": self.critical_failures,
            "test_details": self.test_results
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"📄 Enhanced test results saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

def main():
    """Main enhanced test execution"""
    tester = EnhancedPediatricClinicTester()
    
    try:
        success = tester.run_enhanced_tests()
        tester.save_results()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Enhanced test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())