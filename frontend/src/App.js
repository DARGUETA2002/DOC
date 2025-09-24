import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { Search, Plus, Edit, Trash2, Calendar, FileText, Pill, Users, Home, LogOut, Eye, EyeOff } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Utility functions
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('es-ES');
};

const calcularEdad = (fechaNacimiento) => {
  const today = new Date();
  const birthDate = new Date(fechaNacimiento);
  let age = today.getFullYear() - birthDate.getFullYear();
  const m = today.getMonth() - birthDate.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age;
};

// Login Component
const Login = ({ onLogin }) => {
  const [codigo, setCodigo] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await axios.post(`${API}/login`, { codigo });
      if (response.data.success) {
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('role', response.data.role);
        onLogin(response.data.token, response.data.role);
      }
    } catch (error) {
      alert('Código de acceso incorrecto');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-indigo-600 rounded-full flex items-center justify-center">
            <Users className="h-8 w-8 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Sistema de Clínica Pediátrica
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Ingrese su código de acceso
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleLogin}>
          <div>
            <label htmlFor="codigo" className="sr-only">
              Código de acceso
            </label>
            <div className="relative">
              <input
                id="codigo"
                name="codigo"
                type={showPassword ? "text" : "password"}
                required
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                className="appearance-none rounded-lg relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Código de acceso"
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-400" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>
          </div>
          
          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = ({ token, role, onLogout }) => {
  const [activeView, setActiveView] = useState('patients');
  const [pacientes, setPacientes] = useState([]);
  const [medicamentos, setMedicamentos] = useState([]);
  const [codigosCIE10, setCodigosCIE10] = useState([]);
  const [loading, setLoading] = useState(false);

  // Headers for authenticated requests
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [pacientesRes, medicamentosRes, cie10Res] = await Promise.all([
        axios.get(`${API}/pacientes`, { headers }),
        axios.get(`${API}/medicamentos`, { headers }),
        axios.get(`${API}/cie10`, { headers })
      ]);
      
      setPacientes(pacientesRes.data);
      setMedicamentos(medicamentosRes.data);
      setCodigosCIE10(cie10Res.data);
    } catch (error) {
      console.error('Error loading initial data:', error);
    }
    setLoading(false);
  };

  const MenuItem = ({ icon: Icon, label, view, active, onClick }) => (
    <button
      onClick={() => onClick(view)}
      className={`w-full flex items-center px-4 py-3 text-left hover:bg-indigo-50 transition-colors ${
        active ? 'bg-indigo-100 text-indigo-700 border-r-2 border-indigo-500' : 'text-gray-700'
      }`}
    >
      <Icon className="h-5 w-5 mr-3" />
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow-lg">
        <div className="p-4 bg-indigo-600 text-white">
          <h1 className="text-lg font-semibold">Clínica Pediátrica</h1>
          <p className="text-sm text-indigo-200">Dr. {role}</p>
        </div>
        
        <nav className="mt-4">
          <MenuItem
            icon={Home}
            label="Dashboard"
            view="dashboard"
            active={activeView === 'dashboard'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={Users}
            label="Pacientes"
            view="patients"
            active={activeView === 'patients'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={Pill}
            label="Farmacia"
            view="pharmacy"
            active={activeView === 'pharmacy'}
            onClick={setActiveView}
          />
          <MenuItem
            icon={FileText}
            label="Códigos CIE-10"
            view="cie10"
            active={activeView === 'cie10'}
            onClick={setActiveView}
          />
        </nav>
        
        <div className="absolute bottom-4 left-4 right-4">
          <button
            onClick={onLogout}
            className="w-full flex items-center px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="h-5 w-5 mr-3" />
            Cerrar Sesión
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {activeView === 'dashboard' && <DashboardView pacientes={pacientes} medicamentos={medicamentos} />}
        {activeView === 'patients' && (
          <PatientsView 
            pacientes={pacientes} 
            setPacientes={setPacientes}
            codigosCIE10={codigosCIE10}
            headers={headers}
          />
        )}
        {activeView === 'pharmacy' && (
          <PharmacyView 
            medicamentos={medicamentos} 
            setMedicamentos={setMedicamentos}
            headers={headers}
          />
        )}
        {activeView === 'cie10' && <CIE10View codigosCIE10={codigosCIE10} />}
      </div>
    </div>
  );
};

// Dashboard View Component
const DashboardView = ({ pacientes, medicamentos }) => {
  const totalPacientes = pacientes.length;
  const pacientesEsteAno = pacientes.filter(p => 
    new Date(p.created_at).getFullYear() === new Date().getFullYear()
  ).length;
  
  const medicamentosBajoStock = medicamentos.filter(m => m.stock < 10).length;
  
  const pacientesRecientes = pacientes
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Users className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Pacientes</p>
              <p className="text-2xl font-bold text-gray-900">{totalPacientes}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Calendar className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Pacientes Este Año</p>
              <p className="text-2xl font-bold text-gray-900">{pacientesEsteAno}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-2 bg-red-100 rounded-lg">
              <Pill className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Medicamentos Bajo Stock</p>
              <p className="text-2xl font-bold text-gray-900">{medicamentosBajoStock}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Patients */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Pacientes Recientes</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Paciente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Edad
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fecha Registro
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado Nutricional
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {pacientesRecientes.map((paciente) => (
                <tr key={paciente.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{paciente.nombre_completo}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{paciente.edad} años</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formatDate(paciente.created_at)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      paciente.estado_nutricional === 'normal' ? 'bg-green-100 text-green-800' :
                      paciente.estado_nutricional === 'desnutrido' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {paciente.estado_nutricional || 'No evaluado'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Patients View Component
const PatientsView = ({ pacientes, setPacientes, codigosCIE10, headers }) => {
  const [showModal, setShowModal] = useState(false);
  const [editingPatient, setEditingPatient] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);

  const filteredPacientes = pacientes.filter(p => 
    p.nombre_completo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.numero_celular.includes(searchTerm)
  );

  const openPatientModal = (patient = null) => {
    setEditingPatient(patient);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingPatient(null);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Gestión de Pacientes</h1>
        <button
          onClick={() => openPatientModal()}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Paciente
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar paciente por nombre o teléfono..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Patients List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPacientes.map((paciente) => (
          <PatientCard
            key={paciente.id}
            paciente={paciente}
            onEdit={() => openPatientModal(paciente)}
            onView={() => setSelectedPatient(paciente)}
            headers={headers}
            setPacientes={setPacientes}
          />
        ))}
      </div>

      {/* Modals */}
      {showModal && (
        <PatientModal
          patient={editingPatient}
          codigosCIE10={codigosCIE10}
          onClose={closeModal}
          headers={headers}
          setPacientes={setPacientes}
        />
      )}

      {selectedPatient && (
        <PatientDetailModal
          patient={selectedPatient}
          onClose={() => setSelectedPatient(null)}
          headers={headers}
        />
      )}
    </div>
  );
};

// Patient Card Component
const PatientCard = ({ paciente, onEdit, onView, headers, setPacientes }) => {
  const handleDelete = async () => {
    if (window.confirm('¿Está seguro de eliminar este paciente?')) {
      try {
        await axios.delete(`${API}/pacientes/${paciente.id}`, { headers });
        setPacientes(prev => prev.filter(p => p.id !== paciente.id));
      } catch (error) {
        alert('Error al eliminar paciente');
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{paciente.nombre_completo}</h3>
        <div className="flex space-x-2">
          <button
            onClick={onView}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={onEdit}
            className="p-1 text-gray-600 hover:bg-gray-50 rounded"
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            onClick={handleDelete}
            className="p-1 text-red-600 hover:bg-red-50 rounded"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      <div className="space-y-2 text-sm text-gray-600">
        <p><span className="font-medium">Edad:</span> {paciente.edad} años</p>
        <p><span className="font-medium">Teléfono:</span> {paciente.numero_celular}</p>
        <p><span className="font-medium">Padres:</span> {paciente.nombre_padre} / {paciente.nombre_madre}</p>
        {paciente.diagnostico_clinico && (
          <p><span className="font-medium">Diagnóstico:</span> {paciente.diagnostico_clinico}</p>
        )}
        {paciente.estado_nutricional && (
          <div className="flex items-center">
            <span className="font-medium">Estado Nutricional:</span>
            <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
              paciente.estado_nutricional === 'normal' ? 'bg-green-100 text-green-800' :
              paciente.estado_nutricional === 'desnutrido' ? 'bg-red-100 text-red-800' :
              'bg-yellow-100 text-yellow-800'
            }`}>
              {paciente.estado_nutricional}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

// Patient Modal Component (Create/Edit)
const PatientModal = ({ patient, codigosCIE10, onClose, headers, setPacientes }) => {
  const [formData, setFormData] = useState({
    nombre_completo: patient?.nombre_completo || '',
    fecha_nacimiento: patient?.fecha_nacimiento || '',
    nombre_padre: patient?.nombre_padre || '',
    nombre_madre: patient?.nombre_madre || '',
    direccion: patient?.direccion || '',
    numero_celular: patient?.numero_celular || '',
    sintomas_signos: patient?.sintomas_signos || '',
    diagnostico_clinico: patient?.diagnostico_clinico || '',
    codigo_cie10: patient?.codigo_cie10 || '',
    gravedad_diagnostico: patient?.gravedad_diagnostico || '',
    peso: patient?.peso || '',
    altura: patient?.altura || '',
    contacto_recordatorios: patient?.contacto_recordatorios || ''
  });

  const [filteredCIE10, setFilteredCIE10] = useState([]);
  const [showCIE10List, setShowCIE10List] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({...prev, [name]: value}));

    // Filter CIE-10 codes when typing
    if (name === 'codigo_cie10' && value.length > 0) {
      const filtered = codigosCIE10.filter(code =>
        code.codigo.toLowerCase().includes(value.toLowerCase()) ||
        code.descripcion.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredCIE10(filtered.slice(0, 10));
      setShowCIE10List(true);
    } else if (name === 'codigo_cie10') {
      setShowCIE10List(false);
    }
  };

  const selectCIE10Code = (code) => {
    setFormData(prev => ({...prev, codigo_cie10: code.codigo}));
    setShowCIE10List(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const dataToSubmit = {
        ...formData,
        fecha_nacimiento: formData.fecha_nacimiento,
        peso: formData.peso ? parseFloat(formData.peso) : null,
        altura: formData.altura ? parseFloat(formData.altura) : null
      };

      let response;
      if (patient) {
        response = await axios.put(`${API}/pacientes/${patient.id}`, dataToSubmit, { headers });
        setPacientes(prev => prev.map(p => p.id === patient.id ? response.data : p));
      } else {
        response = await axios.post(`${API}/pacientes`, dataToSubmit, { headers });
        setPacientes(prev => [...prev, response.data]);
      }
      
      onClose();
    } catch (error) {
      alert('Error al guardar paciente: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">
            {patient ? 'Editar Paciente' : 'Nuevo Paciente'}
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre Completo *
                </label>
                <input
                  type="text"
                  name="nombre_completo"
                  required
                  value={formData.nombre_completo}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha de Nacimiento *
                </label>
                <input
                  type="date"
                  name="fecha_nacimiento"
                  required
                  value={formData.fecha_nacimiento}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Padre *
                </label>
                <input
                  type="text"
                  name="nombre_padre"
                  required
                  value={formData.nombre_padre}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre de la Madre *
                </label>
                <input
                  type="text"
                  name="nombre_madre"
                  required
                  value={formData.nombre_madre}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Número de Celular *
                </label>
                <input
                  type="tel"
                  name="numero_celular"
                  required
                  value={formData.numero_celular}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contacto para Recordatorios
                </label>
                <input
                  type="text"
                  name="contacto_recordatorios"
                  value={formData.contacto_recordatorios}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dirección *
              </label>
              <textarea
                name="direccion"
                required
                value={formData.direccion}
                onChange={handleInputChange}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Peso (kg)
                </label>
                <input
                  type="number"
                  step="0.1"
                  name="peso"
                  value={formData.peso}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Altura (m)
                </label>
                <input
                  type="number"
                  step="0.01"
                  name="altura"
                  value={formData.altura}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Síntomas y Signos Clínicos
              </label>
              <textarea
                name="sintomas_signos"
                value={formData.sintomas_signos}
                onChange={handleInputChange}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Diagnóstico Clínico
              </label>
              <textarea
                name="diagnostico_clinico"
                value={formData.diagnostico_clinico}
                onChange={handleInputChange}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div className="relative">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Código CIE-10
              </label>
              <input
                type="text"
                name="codigo_cie10"
                value={formData.codigo_cie10}
                onChange={handleInputChange}
                placeholder="Escriba para buscar código CIE-10..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              
              {showCIE10List && filteredCIE10.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                  {filteredCIE10.map((code) => (
                    <button
                      key={code.id}
                      type="button"
                      onClick={() => selectCIE10Code(code)}
                      className="w-full text-left px-3 py-2 hover:bg-gray-100 border-b border-gray-100"
                    >
                      <div className="font-medium text-sm">{code.codigo}</div>
                      <div className="text-xs text-gray-600">{code.descripcion}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Gravedad del Diagnóstico
              </label>
              <select
                name="gravedad_diagnostico"
                value={formData.gravedad_diagnostico}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Seleccionar gravedad</option>
                <option value="leve">Leve</option>
                <option value="moderada">Moderada</option>
                <option value="grave">Grave</option>
              </select>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                {patient ? 'Actualizar' : 'Crear'} Paciente
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Patient Detail Modal Component
const PatientDetailModal = ({ patient, onClose, headers }) => {
  const [showAddCita, setShowAddCita] = useState(false);
  const [showAddAnalisis, setShowAddAnalisis] = useState(false);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{patient.nombre_completo}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          
          {/* Patient Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-3">Información Personal</h3>
              <div className="space-y-2 text-sm">
                <p><span className="font-medium">Edad:</span> {patient.edad} años</p>
                <p><span className="font-medium">Fecha de Nacimiento:</span> {formatDate(patient.fecha_nacimiento)}</p>
                <p><span className="font-medium">Padre:</span> {patient.nombre_padre}</p>
                <p><span className="font-medium">Madre:</span> {patient.nombre_madre}</p>
                <p><span className="font-medium">Teléfono:</span> {patient.numero_celular}</p>
                <p><span className="font-medium">Dirección:</span> {patient.direccion}</p>
                {patient.contacto_recordatorios && (
                  <p><span className="font-medium">Contacto Recordatorios:</span> {patient.contacto_recordatorios}</p>
                )}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-3">Estado Nutricional</h3>
              <div className="space-y-2 text-sm">
                {patient.peso && <p><span className="font-medium">Peso:</span> {patient.peso} kg</p>}
                {patient.altura && <p><span className="font-medium">Altura:</span> {patient.altura} m</p>}
                {patient.imc && <p><span className="font-medium">IMC:</span> {patient.imc}</p>}
                {patient.estado_nutricional && (
                  <p>
                    <span className="font-medium">Estado:</span> 
                    <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                      patient.estado_nutricional === 'normal' ? 'bg-green-100 text-green-800' :
                      patient.estado_nutricional === 'desnutrido' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {patient.estado_nutricional}
                    </span>
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Clinical Info */}
          {(patient.sintomas_signos || patient.diagnostico_clinico || patient.codigo_cie10) && (
            <div className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-3">Información Clínica</h3>
              <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                {patient.sintomas_signos && (
                  <div>
                    <span className="font-medium text-sm">Síntomas y Signos:</span>
                    <p className="text-sm text-gray-700 mt-1">{patient.sintomas_signos}</p>
                  </div>
                )}
                {patient.diagnostico_clinico && (
                  <div>
                    <span className="font-medium text-sm">Diagnóstico Clínico:</span>
                    <p className="text-sm text-gray-700 mt-1">{patient.diagnostico_clinico}</p>
                  </div>
                )}
                {patient.codigo_cie10 && (
                  <div>
                    <span className="font-medium text-sm">Código CIE-10:</span>
                    <p className="text-sm text-gray-700 mt-1">
                      {patient.codigo_cie10} - {patient.descripcion_cie10}
                    </p>
                  </div>
                )}
                {patient.gravedad_diagnostico && (
                  <div>
                    <span className="font-medium text-sm">Gravedad:</span>
                    <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                      patient.gravedad_diagnostico === 'leve' ? 'bg-green-100 text-green-800' :
                      patient.gravedad_diagnostico === 'moderada' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {patient.gravedad_diagnostico}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Medical History Tabs would go here */}
          <div className="space-y-4">
            <div className="flex space-x-4">
              <button
                onClick={() => setShowAddCita(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                <Plus className="h-4 w-4 inline mr-1" />
                Agregar Cita
              </button>
              <button
                onClick={() => setShowAddAnalisis(true)}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                <Plus className="h-4 w-4 inline mr-1" />
                Agregar Análisis
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Pharmacy View Component
const PharmacyView = ({ medicamentos, setMedicamentos, headers }) => {
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredMedicamentos = medicamentos.filter(m =>
    m.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.categoria.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Gestión de Farmacia</h1>
        <button
          onClick={() => setShowModal(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg flex items-center"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Medicamento
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar medicamento..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Medications Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMedicamentos.map((medicamento) => (
          <div key={medicamento.id} className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{medicamento.nombre}</h3>
            <div className="space-y-1 text-sm text-gray-600">
              <p><span className="font-medium">Categoría:</span> {medicamento.categoria}</p>
              <p><span className="font-medium">Stock:</span> {medicamento.stock} unidades</p>
              <p><span className="font-medium">Precio:</span> L. {medicamento.precio}</p>
              {medicamento.dosis_pediatrica && (
                <p><span className="font-medium">Dosis Pediátrica:</span> {medicamento.dosis_pediatrica}</p>
              )}
            </div>
            {medicamento.stock < 10 && (
              <div className="mt-3 px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full inline-block">
                Stock Bajo
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Medication Modal */}
      {showModal && (
        <MedicationModal
          onClose={() => setShowModal(false)}
          headers={headers}
          setMedicamentos={setMedicamentos}
        />
      )}
    </div>
  );
};

// Medication Modal Component
const MedicationModal = ({ onClose, headers, setMedicamentos }) => {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    stock: '',
    precio: '',
    categoria: '',
    indicaciones: '',
    contraindicaciones: '',
    dosis_pediatrica: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({...prev, [name]: value}));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const dataToSubmit = {
        ...formData,
        stock: parseInt(formData.stock),
        precio: parseFloat(formData.precio)
      };

      const response = await axios.post(`${API}/medicamentos`, dataToSubmit, { headers });
      setMedicamentos(prev => [...prev, response.data]);
      onClose();
    } catch (error) {
      alert('Error al crear medicamento: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Nuevo Medicamento</h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Medicamento *
                </label>
                <input
                  type="text"
                  name="nombre"
                  required
                  value={formData.nombre}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Categoría *
                </label>
                <select
                  name="categoria"
                  required
                  value={formData.categoria}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Seleccionar categoría</option>
                  <option value="Antibióticos">Antibióticos</option>
                  <option value="Analgésicos">Analgésicos</option>
                  <option value="Antiinflamatorios">Antiinflamatorios</option>
                  <option value="Vitaminas">Vitaminas</option>
                  <option value="Jarabe para la tos">Jarabe para la tos</option>
                  <option value="Antialérgicos">Antialérgicos</option>
                  <option value="Probióticos">Probióticos</option>
                  <option value="Cremas y ungüentos">Cremas y ungüentos</option>
                  <option value="Otros">Otros</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Stock Inicial *
                </label>
                <input
                  type="number"
                  name="stock"
                  required
                  min="0"
                  value={formData.stock}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Precio (Lempiras) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  name="precio"
                  required
                  min="0"
                  value={formData.precio}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Descripción *
              </label>
              <textarea
                name="descripcion"
                required
                value={formData.descripcion}
                onChange={handleInputChange}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dosis Pediátrica
              </label>
              <textarea
                name="dosis_pediatrica"
                value={formData.dosis_pediatrica}
                onChange={handleInputChange}
                rows="2"
                placeholder="Ej: 5ml cada 8 horas por 7 días"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Indicaciones
              </label>
              <textarea
                name="indicaciones"
                value={formData.indicaciones}
                onChange={handleInputChange}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraindicaciones
              </label>
              <textarea
                name="contraindicaciones"
                value={formData.contraindicaciones}
                onChange={handleInputChange}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                Crear Medicamento
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// CIE-10 View Component
const CIE10View = ({ codigosCIE10 }) => {
  const [searchTerm, setSearchTerm] = useState('');
  
  const filteredCodes = codigosCIE10.filter(code =>
    code.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    code.descripcion.toLowerCase().includes(searchTerm.toLowerCase()) ||
    code.categoria.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const categorias = [...new Set(codigosCIE10.map(code => code.categoria))];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Códigos CIE-10</h1>
      
      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar código o descripción..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Categories */}
      <div className="space-y-6">
        {categorias.map(categoria => {
          const codesInCategory = filteredCodes.filter(code => code.categoria === categoria);
          
          if (codesInCategory.length === 0) return null;
          
          return (
            <div key={categoria} className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 bg-gray-50 border-b">
                <h2 className="text-lg font-semibold text-gray-900">{categoria}</h2>
                <p className="text-sm text-gray-600">{codesInCategory.length} códigos</p>
              </div>
              <div className="p-6">
                <div className="grid gap-3">
                  {codesInCategory.map(code => (
                    <div key={code.id} className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                      <div className="flex-shrink-0 w-16">
                        <span className="font-mono font-semibold text-indigo-600">{code.codigo}</span>
                      </div>
                      <div className="flex-1 ml-4">
                        <p className="text-sm text-gray-900">{code.descripcion}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [role, setRole] = useState(localStorage.getItem('role'));

  useEffect(() => {
    if (token) {
      setIsAuthenticated(true);
    }
  }, [token]);

  const handleLogin = (newToken, newRole) => {
    localStorage.setItem('token', newToken);
    localStorage.setItem('role', newRole);
    setToken(newToken);
    setRole(newRole);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    setToken(null);
    setRole(null);
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return <Dashboard token={token} role={role} onLogout={handleLogout} />;
}

export default App;